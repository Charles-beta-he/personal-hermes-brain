#!/usr/bin/env python3
"""Hermes-native Replay receipt/proof verifier and generator.

Clean-room extraction of the replay receipt evidence loop from hermes-hudui
(commit b7b76d5, MIT). Generates redacted proof artifacts, receipt hashes,
and optional Ed25519 signature verification — all without requiring the HUD
runtime.

This script works directly against ~/.hermes/ session data and produces
self-contained JSON proof artifacts that can be stored, shared, and verified.

Usage:
    # Generate a receipt for a session
    python3 replay_receipts.py generate --session <id>

    # Verify a receipt against a replay artifact
    python3 replay_receipts.py verify --receipt path/to/receipt.json --replay path/to/replay.json

    # Scan session data for sensitive content (dry-run redaction)
    python3 replay_receipts.py scan --session <id>

    # List recent sessions eligible for receipt generation
    python3 replay_receipts.py list [--limit N]
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Sequence

VERSION = 1
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()
STATE_DB = HERMES_HOME / "state.db"
KEYS_DIR = HERMES_HOME / "auth" / "replay_keys"

# ---------------------------------------------------------------------------
# Redaction patterns (inspired by hermes-hudui replay_redactor.py)
# ---------------------------------------------------------------------------

REDACTION_PATTERNS: list[tuple[str, str, str, re.Pattern[str]]] = [
    ("api_key", "critical", "[REDACTED_API_KEY]",
     re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|sk-ant-[A-Za-z0-9_-]{20,})\b")),
    ("bearer_token", "critical", "[REDACTED_BEARER]",
     re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.IGNORECASE)),
    ("github_token", "critical", "[REDACTED_GITHUB]",
     re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")),
    ("aws_key", "critical", "[REDACTED_AWS]",
     re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("ssh_key", "critical", "[REDACTED_SSH]",
     re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL)),
    ("email", "medium", "[REDACTED_EMAIL]",
     re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("env_var", "high", "[REDACTED_ENV]",
     re.compile(r"""\b[A-Z][A-Z0-9_]{2,}\s*=\s*[^\s'"]{8,}""")),
    ("basic_auth_url", "high", "[REDACTED_URL]",
     re.compile(r"https?://[^\s:@]+:[^\s:@]+@[^\s]+")),
    ("tokenized_url", "high", "[REDACTED_URL]",
     re.compile(r"https?://[^\s]+[?&](?:token|key|secret|auth|signature)=[^\s&]+", re.IGNORECASE)),
    ("local_path", "medium", "[REDACTED_PATH]",
     re.compile(r"(?:/Users|/home|/var/folders|/tmp)/[A-Za-z0-9._/-]+")),
]

RAW_FIELD_NAMES = {"raw_content", "reasoning"}
RAW_METADATA_KEYS = {"arguments", "args", "command", "output", "stderr", "stdout"}


# ---------------------------------------------------------------------------
# Core data models
# ---------------------------------------------------------------------------

@dataclass
class RedactionFinding:
    finding_id: str
    severity: str  # critical / high / medium
    type: str
    field_path: str
    preview: str
    replacement: str


@dataclass
class ReceiptHashes:
    source_hash: str | None = None
    redacted_replay_hash: str | None = None
    receipt_hash: str | None = None


@dataclass
class ReplayReceipt:
    schema_version: str = "0.1"
    receipt_id: str = ""
    replay_id: str = ""
    source_session_id: str = ""
    title: str = ""
    status: str = "unknown"
    started_at: str | None = None
    ended_at: str | None = None
    duration_ms: int | None = None
    model: str | None = None
    total_cost_usd: float | None = None
    files_changed: int | None = None
    tests: dict[str, Any] | None = None
    tool_call_count: int = 0
    skills_used: list[dict[str, Any]] = field(default_factory=list)
    hashes: ReceiptHashes = field(default_factory=ReceiptHashes)
    redaction: dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""
    generator: dict[str, str] = field(default_factory=lambda: {"name": "hermes-replay-receipts", "version": str(VERSION)})
    # Signature fields (populated if signing is requested)
    signature_algorithm: str | None = None
    signature: str | None = None
    public_key: str | None = None
    signed_at: str | None = None


@dataclass
class ReplayEvent:
    event_id: str
    type: str
    title: str
    summary: str
    timestamp: str | None = None
    status: str = "info"
    raw_content: str | None = None
    redacted_content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    receipt_hash: str | None = None
    redacted_replay_hash: str | None = None
    redaction_mode: str | None = None
    signature_valid: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "receipt_hash": self.receipt_hash,
            "redacted_replay_hash": self.redacted_replay_hash,
            "redaction_mode": self.redaction_mode,
            "signature_valid": self.signature_valid,
        }


# ---------------------------------------------------------------------------
# Hashing utilities
# ---------------------------------------------------------------------------

def hash_payload(payload: Any) -> str:
    """Deterministic SHA-256 hash of any JSON-serializable payload."""
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Redaction engine
# ---------------------------------------------------------------------------

def _finding_id(field_path: str, kind: str, index: int) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", field_path).strip("_")[:48]
    return f"{safe}_{kind}_{index}"


def _scan_text(value: str, field_path: str) -> tuple[str, list[RedactionFinding]]:
    redacted = value
    findings: list[RedactionFinding] = []
    counters: dict[str, int] = {}
    for kind, severity, base_replacement, pattern in REDACTION_PATTERNS:
        for match in pattern.finditer(redacted):
            counters[kind] = counters.get(kind, 0) + 1
            replacement = f"{base_replacement[:-1]}_{counters[kind]}]"
            preview = match.group(0)
            findings.append(RedactionFinding(
                finding_id=_finding_id(field_path, kind, len(findings) + 1),
                severity=severity, type=kind, field_path=field_path,
                preview=preview[:80], replacement=replacement,
            ))
            redacted = redacted.replace(preview, replacement)
    return redacted, findings


def _redact_value(value: Any, field_path: str) -> tuple[Any, list[RedactionFinding]]:
    if isinstance(value, str):
        return _scan_text(value, field_path)
    if isinstance(value, list):
        items, findings = [], []
        for i, item in enumerate(value):
            r, f = _redact_value(item, f"{field_path}[{i}]")
            items.append(r)
            findings.extend(f)
        return items, findings
    if isinstance(value, dict):
        result, findings = {}, []
        for key, item in value.items():
            child = f"{field_path}.{key}"
            if str(key) in RAW_METADATA_KEYS and isinstance(item, str):
                result[key] = "[REDACTED_RAW_FIELD]"
                findings.append(RedactionFinding(
                    finding_id=_finding_id(child, "raw_field", 1),
                    severity="high", type="raw_field", field_path=child,
                    preview=item[:80], replacement="[REDACTED_RAW_FIELD]",
                ))
                continue
            r, f = _redact_value(item, child)
            result[key] = r
            findings.extend(f)
        return result, findings
    return value, []


def redact_events(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[RedactionFinding]]:
    """Redact a list of event dicts, returning (redacted_events, findings)."""
    all_findings: list[RedactionFinding] = []
    redacted_events = []
    for i, event in enumerate(events):
        r, f = _redact_value(copy.deepcopy(event), f"events[{i}]")
        redacted_events.append(r)
        all_findings.extend(f)
    return redacted_events, all_findings


# ---------------------------------------------------------------------------
# Ed25519 signing (optional)
# ---------------------------------------------------------------------------

def _load_or_create_signing_key() -> Any | None:
    """Load or create Ed25519 keypair. Returns None if cryptography is unavailable."""
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError:
        return None
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    key_path = KEYS_DIR / "ed25519_private.pem"
    if key_path.exists():
        return serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    key = Ed25519PrivateKey.generate()
    key_path.write_bytes(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    key_path.chmod(0o600)
    return key


def sign_receipt(receipt_hash: str, replay_hash: str) -> dict[str, str] | None:
    """Sign receipt+replay hashes with Ed25519. Returns None if unavailable."""
    key = _load_or_create_signing_key()
    if key is None:
        return None
    from cryptography.hazmat.primitives import serialization
    message = f"{receipt_hash}\n{replay_hash}".encode("utf-8")
    signature = key.sign(message)
    pub_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {
        "signature_algorithm": "ed25519",
        "signature": base64.b64encode(signature).decode("ascii"),
        "public_key": base64.b64encode(pub_bytes).decode("ascii"),
        "signed_at": datetime.now(timezone.utc).isoformat(),
    }


def verify_signature(receipt_hash: str, replay_hash: str, signature_b64: str, pubkey_b64: str) -> bool:
    """Verify Ed25519 signature over receipt+replay hashes."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(pubkey_b64))
        message = f"{receipt_hash}\n{replay_hash}".encode("utf-8")
        pub.verify(base64.b64decode(signature_b64), message)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Session data access
# ---------------------------------------------------------------------------

def _get_db() -> sqlite3.Connection | None:
    if not STATE_DB.exists():
        return None
    conn = sqlite3.connect(str(STATE_DB))
    conn.row_factory = sqlite3.Row
    return conn


def list_sessions(limit: int = 20) -> list[dict[str, Any]]:
    """List recent Hermes sessions from state.db."""
    conn = _get_db()
    if conn is None:
        return []
    try:
        rows = conn.execute(
            "SELECT id, title, model, started_at, ended_at, message_count, tool_call_count, estimated_cost_usd "
            "FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def get_session_messages(session_id: str) -> list[dict[str, Any]]:
    """Fetch messages for a session from state.db."""
    conn = _get_db()
    if conn is None:
        return []
    try:
        rows = conn.execute(
            "SELECT role, content, timestamp, tool_calls FROM messages WHERE session_id = ? ORDER BY rowid",
            (session_id,)
        ).fetchall()
        messages = []
        for r in rows:
            msg = dict(r)
            if msg.get("tool_calls"):
                try:
                    msg["tool_calls"] = json.loads(msg["tool_calls"])
                except (json.JSONDecodeError, TypeError):
                    pass
            messages.append(msg)
        return messages
    except Exception:
        return []
    finally:
        conn.close()


def get_session_info(session_id: str) -> dict[str, Any] | None:
    """Fetch session metadata."""
    conn = _get_db()
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Receipt generation
# ---------------------------------------------------------------------------

def _replay_id(session_id: str) -> str:
    return f"replay_{hashlib.sha256(session_id.encode()).hexdigest()[:12]}"


def _extract_skill_names(messages: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for msg in messages:
        content = str(msg.get("content") or "")
        for pattern in [
            r"\bskill(?:\s+used)?\s*[:=]\s*([A-Za-z0-9_.:/-]+)",
            r"\busing\s+skill\s+([A-Za-z0-9_.:/-]+)",
            r"\bloaded\s+skill\s+([A-Za-z0-9_.:/-]+)",
        ]:
            for m in re.finditer(pattern, content, re.IGNORECASE):
                name = m.group(1).strip(".,;")
                if name and name not in names:
                    names.append(name)
    return names


def _extract_test_counts(messages: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    passed = failed = None
    for msg in messages:
        text = str(msg.get("content") or "").lower()
        m = re.search(r"(\d+)\s+passed", text)
        if m:
            passed = (passed or 0) + int(m.group(1))
        m = re.search(r"(\d+)\s+failed", text)
        if m:
            failed = (failed or 0) + int(m.group(1))
    return passed, failed


def generate_receipt(session_id: str, sign: bool = True) -> dict[str, Any]:
    """Generate a replay receipt for a Hermes session.

    Returns a dict with keys: receipt, events, redaction_findings, replay_hash.
    """
    session = get_session_info(session_id)
    if session is None:
        return {"error": f"Session not found: {session_id}"}

    messages = get_session_messages(session_id)
    rid = _replay_id(session_id)
    skill_names = _extract_skill_names(messages)
    test_passed, test_failed = _extract_test_counts(messages)

    # Build events
    events: list[dict[str, Any]] = []
    tool_count = 0
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = str(msg.get("content") or "")
        ts = msg.get("timestamp") or session.get("started_at")
        if role == "user":
            etype = "prompt"
        elif role == "assistant":
            etype = "assistant_message"
        elif role == "tool":
            etype = "tool_result"
        else:
            etype = "error"

        event_id = hashlib.sha256(f"{rid}:{i}:{etype}".encode()).hexdigest()[:16]
        events.append({
            "event_id": event_id, "type": etype,
            "title": f"{'User prompt' if etype == 'prompt' else 'Assistant message' if etype == 'assistant_message' else 'Tool result'}",
            "summary": (content[:157] + "...") if len(content) > 160 else content,
            "timestamp": ts, "status": "info",
            "raw_content": content,
        })

        # Parse tool calls
        tc = msg.get("tool_calls")
        if isinstance(tc, list):
            for j, call in enumerate(tc):
                tool_count += 1
                name = "tool"
                if isinstance(call, dict):
                    fn = call.get("function")
                    if isinstance(fn, dict) and fn.get("name"):
                        name = fn["name"]
                    elif call.get("name"):
                        name = call["name"]
                eid = hashlib.sha256(f"{rid}:{i}:tool_call:{j}".encode()).hexdigest()[:16]
                events.append({
                    "event_id": eid, "type": "tool_call",
                    "title": f"Tool call: {name}",
                    "summary": f"Called {name}",
                    "timestamp": ts, "status": "info",
                    "raw_content": json.dumps(call, sort_keys=True, default=str),
                    "metadata": {"tool_name": name},
                })

    # Redact events
    redacted_events, findings = redact_events(events)

    # Build redacted replay hash (from redacted event summaries only)
    redacted_replay_hash = hash_payload({
        "replay_id": rid,
        "events": [
            {"event_id": e.get("event_id"), "type": e.get("type"),
             "title": e.get("title"), "summary": e.get("summary"),
             "timestamp": e.get("timestamp"), "status": e.get("status")}
            for e in redacted_events
        ],
    })

    # Build source hash
    source_hash = hash_payload({
        "session_id": session_id,
        "events": events,
    })

    # Build receipt
    now_iso = datetime.now(timezone.utc).isoformat()
    receipt = ReplayReceipt(
        schema_version="0.1",
        receipt_id=f"receipt_{rid}",
        replay_id=rid,
        source_session_id=session_id,
        title=session.get("title") or session_id[:8],
        status="success" if session.get("ended_at") else "unknown",
        started_at=session.get("started_at"),
        ended_at=session.get("ended_at"),
        model=session.get("model"),
        total_cost_usd=session.get("estimated_cost_usd"),
        tool_call_count=tool_count,
        skills_used=[{"name": n, "version": None, "hash": None} for n in skill_names],
        hashes=ReceiptHashes(source_hash=source_hash, redacted_replay_hash=redacted_replay_hash),
        redaction={
            "mode": "safe_share",
            "findings_count": len(findings),
            "redacted_fields_count": len(findings),
        },
        generated_at=now_iso,
    )

    if test_passed is not None or test_failed is not None:
        receipt.tests = {"passed": test_passed, "failed": test_failed}

    # Compute receipt hash (self-referential, with signature fields nulled)
    receipt_dict = _receipt_to_dict(receipt)
    for k in ["signature_algorithm", "signature", "public_key", "signed_at"]:
        receipt_dict.pop(k, None)
    hashes_copy = dict(receipt_dict.get("hashes") or {})
    hashes_copy["receipt_hash"] = None
    receipt_dict["hashes"] = hashes_copy
    rh = hash_payload(receipt_dict)
    receipt.hashes.receipt_hash = rh

    # Optional signing
    sig_info = None
    if sign:
        sig_info = sign_receipt(rh, redacted_replay_hash)
        if sig_info:
            receipt.signature_algorithm = sig_info["signature_algorithm"]
            receipt.signature = sig_info["signature"]
            receipt.public_key = sig_info["public_key"]
            receipt.signed_at = sig_info["signed_at"]

    return {
        "receipt": _receipt_to_dict(receipt),
        "events": redacted_events,
        "redaction_findings": [_finding_to_dict(f) for f in findings],
        "replay_hash": redacted_replay_hash,
        "signed": sig_info is not None,
    }


def _receipt_to_dict(r: ReplayReceipt) -> dict[str, Any]:
    d: dict[str, Any] = {}
    for f in fields(r):
        val = getattr(r, f.name)
        if is_dataclass(val) and not isinstance(val, type):
            val = {k: v for k, v in val.__dict__.items()}
        d[f.name] = val
    return d


def _finding_to_dict(f: RedactionFinding) -> dict[str, Any]:
    return {k: getattr(f, k) for k in ["finding_id", "severity", "type", "field_path", "preview", "replacement"]}


# ---------------------------------------------------------------------------
# Receipt verification
# ---------------------------------------------------------------------------

def verify_receipt(receipt_path: str, replay_path: str | None = None) -> VerificationResult:
    """Verify a receipt JSON file.

    If replay_path is provided, also cross-check hashes against the replay.
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        receipt = json.loads(Path(receipt_path).expanduser().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return VerificationResult(ok=False, errors=[f"Receipt not found: {receipt_path}"])
    except json.JSONDecodeError as e:
        return VerificationResult(ok=False, errors=[f"Invalid JSON: {e}"])

    if not isinstance(receipt, dict):
        return VerificationResult(ok=False, errors=["Receipt must be a JSON object"])

    # Required fields
    for f in ["schema_version", "receipt_id", "replay_id", "source_session_id", "hashes", "redaction"]:
        if f not in receipt:
            errors.append(f"Receipt missing required field: {f}")

    if receipt.get("schema_version") != "0.1":
        errors.append(f"Unsupported schema_version: {receipt.get('schema_version')}")

    # Verify receipt hash
    receipt_hashes = receipt.get("hashes", {})
    expected_rh = receipt_hashes.get("receipt_hash")
    actual_rh = _compute_receipt_hash(receipt)
    if expected_rh != actual_rh:
        errors.append("Receipt hash does not match receipt payload (tampered or recomputed)")

    # Verify signature if present
    sig = receipt.get("signature")
    pub = receipt.get("public_key")
    if sig and pub:
        algo = receipt.get("signature_algorithm")
        if algo != "ed25519":
            errors.append(f"Unsupported signature algorithm: {algo}")
        elif expected_rh and receipt_hashes.get("redacted_replay_hash"):
            if not verify_signature(str(expected_rh), str(receipt_hashes["redacted_replay_hash"]), str(sig), str(pub)):
                errors.append("Receipt signature is INVALID")
            else:
                pass  # valid
    else:
        warnings.append("No signature present; hash-only verification")

    # Cross-check with replay if provided
    if replay_path:
        try:
            replay = json.loads(Path(replay_path).expanduser().read_text(encoding="utf-8"))
            run = (replay.get("replay") or {}).get("run") or {}
            run_hashes = run.get("hashes") or {}
            if receipt.get("replay_id") != run.get("replay_id"):
                errors.append("Receipt replay_id does not match replay")
            if receipt_hashes.get("redacted_replay_hash") != run_hashes.get("redacted_replay_hash"):
                errors.append("Receipt redacted_replay_hash does not match replay run hash")
        except FileNotFoundError:
            warnings.append(f"Replay file not found: {replay_path} (receipt-only verification)")
        except (json.JSONDecodeError, KeyError) as e:
            errors.append(f"Could not parse replay: {e}")

    redaction = receipt.get("redaction", {})
    if not redaction.get("mode"):
        errors.append("Receipt missing redaction mode")
    if redaction.get("mode") == "raw":
        warnings.append("Receipt declares raw redaction mode")

    return VerificationResult(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        receipt_hash=expected_rh,
        redacted_replay_hash=receipt_hashes.get("redacted_replay_hash"),
        redaction_mode=redaction.get("mode"),
        signature_valid=bool(sig and pub) and not any("signature" in e.lower() for e in errors),
    )


def _compute_receipt_hash(receipt: dict[str, Any]) -> str:
    payload = dict(receipt)
    for k in ["signature_algorithm", "signature", "public_key", "signed_at"]:
        payload.pop(k, None)
    hashes = dict(payload.get("hashes") or {})
    hashes["receipt_hash"] = None
    payload["hashes"] = hashes
    return hash_payload(payload)


# ---------------------------------------------------------------------------
# Scan mode (dry-run redaction preview)
# ---------------------------------------------------------------------------

def scan_session(session_id: str) -> dict[str, Any]:
    """Scan session messages for sensitive content, returning findings without generating a receipt."""
    messages = get_session_messages(session_id)
    if not messages:
        return {"error": f"No messages found for session: {session_id}"}

    # Build raw content blobs
    blobs: list[tuple[str, str]] = []
    for i, msg in enumerate(messages):
        content = str(msg.get("content") or "")
        if content:
            blobs.append((f"messages[{i}].content", content))
        tc = msg.get("tool_calls")
        if isinstance(tc, list):
            for j, call in enumerate(tc):
                blobs.append((f"messages[{i}].tool_calls[{j}]", json.dumps(call, sort_keys=True, default=str)))

    all_findings: list[RedactionFinding] = []
    for path, text in blobs:
        _, findings = _scan_text(text, path)
        all_findings.extend(findings)

    severity_counts = {}
    for f in all_findings:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

    return {
        "session_id": session_id,
        "blobs_scanned": len(blobs),
        "total_findings": len(all_findings),
        "severity_counts": severity_counts,
        "findings": [_finding_to_dict(f) for f in all_findings[:100]],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Hermes-native Replay receipt/proof verifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # generate
    gen = sub.add_parser("generate", help="Generate a receipt for a session")
    gen.add_argument("--session", required=True, help="Session ID")
    gen.add_argument("--output", "-o", help="Output file path (default: stdout)")
    gen.add_argument("--no-sign", action="store_true", help="Skip Ed25519 signing")

    # verify
    ver = sub.add_parser("verify", help="Verify a receipt file")
    ver.add_argument("--receipt", required=True, help="Receipt JSON path")
    ver.add_argument("--replay", help="Replay JSON path (optional cross-check)")

    # scan
    scn = sub.add_parser("scan", help="Scan session for sensitive content (dry-run)")
    scn.add_argument("--session", required=True, help="Session ID")

    # list
    ls = sub.add_parser("list", help="List recent sessions")
    ls.add_argument("--limit", type=int, default=20, help="Max sessions to list")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "list":
        sessions = list_sessions(args.limit)
        if not sessions:
            print("No sessions found (state.db missing or empty)")
            return 1
        for s in sessions:
            sid = s.get("id", "?")[:16]
            title = (s.get("title") or "?")[:40]
            model = s.get("model") or "?"
            print(f"  {sid}  {title:<40}  {model}")
        return 0

    if args.command == "scan":
        result = scan_session(args.session)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if "error" not in result else 1

    if args.command == "generate":
        result = generate_receipt(args.session, sign=not args.no_sign)
        if "error" in result:
            print(f"ERROR: {result['error']}", file=sys.stderr)
            return 1
        output = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        if args.output:
            Path(args.output).expanduser().write_text(output, encoding="utf-8")
            print(f"Receipt written to {args.output}")
        else:
            print(output)
        return 0

    if args.command == "verify":
        result = verify_receipt(args.receipt, getattr(args, "replay", None))
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result.ok else 2

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
