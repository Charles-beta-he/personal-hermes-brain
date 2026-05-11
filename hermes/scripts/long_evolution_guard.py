#!/usr/bin/env python3
"""long_evolution_guard.py — Hermes-native long-term evolution control plane.

This script lands the Ruflo-inspired governance primitives without importing
Ruflo: capability inventory/witness, local claim/lease/handoff ledger, and
budget/hop circuit breakers for recursive delegation.

All state is local-first. No network, no shell execution, no destructive
commands.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import hmac
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

INVENTORY_SCHEMA = "hermes_capability_inventory_v1"
WITNESS_SCHEMA = "hermes_capability_witness_v1"
LEDGER_SCHEMA_VERSION = 1
DEFAULT_SCAN_DIRS = ["scripts", "skills"]
DEFAULT_IGNORE_PATTERNS = [
    ".git/**",
    "**/__pycache__/**",
    "**/*.pyc",
    "memory/**",
    "logs/**",
    "sessions/**",
    "*.sqlite",
    "*.db",
]
SCRIPT_SUFFIXES = {".py", ".sh", ".bash"}


def now_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def now_epoch() -> float:
    return time.time()


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(data: Any) -> str:
    return sha256_bytes(canonical_json(data).encode("utf-8"))


def resolve_root(root: str | Path | None = None) -> Path:
    if root:
        return Path(root).expanduser().resolve()
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser().resolve()


def resolve_evolution_home() -> Path:
    return Path(os.environ.get("HERMES_EVOLUTION_HOME", str(Path.home() / ".hermes" / "memory" / "evolution"))).expanduser().resolve()


def default_witness_path() -> Path:
    return resolve_evolution_home() / "capability_witness.json"


def default_key_path() -> Path:
    return resolve_evolution_home() / "witness.key"


def default_db_path() -> Path:
    return resolve_evolution_home() / "claims.sqlite"


def rel_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def ignored(rel: str, patterns: Sequence[str] = DEFAULT_IGNORE_PATTERNS) -> bool:
    rel = rel.replace(os.sep, "/")
    for pattern in patterns:
        pat = pattern.replace(os.sep, "/")
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch("/" + rel, pat):
            return True
        if pat.endswith("/**") and rel.startswith(pat[:-3].rstrip("/") + "/"):
            return True
    return False


def git_head(root: Path) -> str | None:
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, check=False)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def extract_markers(path: Path, text: str) -> list[str]:
    markers: list[str] = []
    if path.name == "SKILL.md":
        for line in text.splitlines()[:40]:
            if line.startswith("name:"):
                markers.append(line.split(":", 1)[1].strip().strip('"\''))
                break
        headings = [line.lstrip("#").strip() for line in text.splitlines() if line.startswith("#")]
        markers.extend(h for h in headings[:3] if h)
    elif path.suffix == ".py":
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("def "):
                markers.append(stripped.split("def ", 1)[1].split("(", 1)[0])
            elif stripped.startswith("class "):
                markers.append(stripped.split("class ", 1)[1].split("(", 1)[0].split(":", 1)[0])
            if len(markers) >= 12:
                break
    elif path.suffix in {".sh", ".bash"}:
        if text.startswith("#!"):
            markers.append("shebang")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.endswith(") {") or stripped.startswith("function "):
                markers.append(stripped[:80])
            if len(markers) >= 8:
                break
    return sorted(set(m for m in markers if m))[:20]


def capability_type(path: Path, rel: str) -> str:
    if path.name == "SKILL.md" and "/skills/" in f"/{rel}":
        return "skill"
    if rel.startswith("skills/") and path.name == "SKILL.md":
        return "skill"
    if rel.startswith("scripts/"):
        return "script"
    return "file"


def iter_capability_files(root: Path, scan_dirs: Sequence[str] = DEFAULT_SCAN_DIRS) -> Iterable[Path]:
    for scan_dir in scan_dirs:
        base = root / scan_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            try:
                rel = rel_posix(path, root)
            except ValueError:
                continue
            if ignored(rel):
                continue
            if rel.startswith("scripts/") and path.suffix not in SCRIPT_SUFFIXES:
                continue
            if rel.startswith("skills/") and path.name != "SKILL.md":
                continue
            yield path


def build_inventory(root: str | Path | None = None) -> dict:
    root_path = resolve_root(root)
    capabilities: list[dict] = []
    for path in iter_capability_files(root_path):
        rel = rel_posix(path, root_path)
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
        ctype = capability_type(path, rel)
        capabilities.append({
            "id": f"{ctype}:{rel}",
            "type": ctype,
            "path": rel,
            "sha256": sha256_bytes(data),
            "size_bytes": len(data),
            "markers": extract_markers(path, text),
        })
    capabilities.sort(key=lambda c: (c["type"], c["path"]))
    return {
        "schema": INVENTORY_SCHEMA,
        "root": str(root_path),
        "git_head": git_head(root_path),
        "generated_at": now_ts(),
        "capability_count": len(capabilities),
        "capabilities": capabilities,
    }


def stable_inventory_for_hash(inventory: dict) -> dict:
    stable = dict(inventory)
    stable.pop("generated_at", None)
    return stable


def ensure_key(path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_bytes()
    key = os.urandom(32)
    path.write_bytes(key)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return key


def sign_manifest(manifest_hash: str, key: bytes) -> str:
    return hmac.new(key, manifest_hash.encode("ascii"), hashlib.sha256).hexdigest()


def create_witness(root: str | Path | None = None, out: str | Path | None = None, key_path: str | Path | None = None) -> dict:
    root_path = resolve_root(root)
    out_path = Path(out).expanduser().resolve() if out else default_witness_path()
    key_file = Path(key_path).expanduser().resolve() if key_path else default_key_path()
    inv = build_inventory(root_path)
    manifest_hash = sha256_json(stable_inventory_for_hash(inv))
    key = ensure_key(key_file)
    witness = {
        "schema": WITNESS_SCHEMA,
        "created_at": now_ts(),
        "root": str(root_path),
        "git_head": inv.get("git_head"),
        "manifest_hash": manifest_hash,
        "signature_type": "hmac-sha256-local-key",
        "signature": sign_manifest(manifest_hash, key),
        "key_path": str(key_file),
        "inventory": inv,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(witness, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        out_path.chmod(0o600)
    except OSError:
        pass
    return {"ok": True, **witness, "witness_path": str(out_path)}


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def verify_witness(witness_path: str | Path, *, root: str | Path | None = None) -> dict:
    witness = load_json(witness_path)
    root_path = resolve_root(root or witness.get("root"))
    violations: list[dict] = []
    if witness.get("schema") != WITNESS_SCHEMA:
        violations.append({"type": "schema_mismatch", "expected": WITNESS_SCHEMA, "actual": witness.get("schema")})
    inv = witness.get("inventory") or {}
    witness_root = str(Path(witness.get("root", "")).expanduser().resolve()) if witness.get("root") else None
    inventory_root = str(Path(inv.get("root", "")).expanduser().resolve()) if inv.get("root") else None
    actual_root = str(root_path)
    if witness_root != inventory_root:
        violations.append({"type": "root_mismatch", "witness_root": witness_root, "inventory_root": inventory_root})
    if witness_root != actual_root:
        violations.append({"type": "root_mismatch", "witness_root": witness_root, "actual_root": actual_root})
    expected_hash = witness.get("manifest_hash")
    stored_hash = sha256_json(stable_inventory_for_hash(inv))
    if stored_hash != expected_hash:
        violations.append({"type": "manifest_hash_mismatch", "expected": expected_hash, "actual": stored_hash})
    key_path = witness.get("key_path")
    if key_path and Path(key_path).exists():
        key_file = Path(key_path)
        expected_sig = sign_manifest(str(expected_hash), key_file.read_bytes())
        if expected_sig != witness.get("signature"):
            violations.append({"type": "signature_mismatch"})
        try:
            mode = key_file.stat().st_mode & 0o777
            if mode & 0o077:
                violations.append({"type": "weak_key_permissions", "path": str(key_file), "mode": oct(mode)})
        except OSError:
            pass
    else:
        violations.append({"type": "missing_witness_key", "path": key_path})

    current_inv = build_inventory(root_path)
    current_hash = sha256_json(stable_inventory_for_hash(current_inv))
    if current_hash != expected_hash:
        violations.append({"type": "inventory_drift", "expected": expected_hash, "actual": current_hash})

    expected_caps = {cap.get("path"): cap for cap in inv.get("capabilities", []) if cap.get("path")}
    current_caps = {cap.get("path"): cap for cap in current_inv.get("capabilities", []) if cap.get("path")}
    for rel, cap in sorted(expected_caps.items()):
        current = current_caps.get(rel)
        if current is None:
            violations.append({"type": "missing_file", "path": rel})
            continue
        if current.get("sha256") != cap.get("sha256"):
            violations.append({"type": "hash_mismatch", "path": rel, "expected": cap.get("sha256"), "actual": current.get("sha256")})
    for rel, cap in sorted(current_caps.items()):
        if rel not in expected_caps:
            violations.append({"type": "added_capability", "path": rel, "sha256": cap.get("sha256")})
    passed = not violations
    return {
        "schema": "hermes_capability_verify_v1",
        "passed": passed,
        "root": str(root_path),
        "witness": str(Path(witness_path).expanduser()),
        "checked_capabilities": len(current_caps),
        "expected_capabilities": len(expected_caps),
        "violations": violations,
    }


def ensure_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path).expanduser().resolve() if db_path else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute(
        "create table if not exists claims (task_id text primary key, owner text not null, status text not null, claim_ts real not null, expires_at real not null, metadata_json text not null, lineage_json text not null)"
    )
    con.execute(
        "create table if not exists claim_events (id integer primary key autoincrement, ts real not null, event text not null, task_id text not null, owner text, details_json text not null, previous_event_hash text not null default '', event_hash text not null default '', schema_version integer not null default 1)"
    )
    for col, ddl in [
        ("previous_event_hash", "alter table claim_events add column previous_event_hash text not null default ''"),
        ("event_hash", "alter table claim_events add column event_hash text not null default ''"),
        ("schema_version", "alter table claim_events add column schema_version integer not null default 1"),
    ]:
        existing = {row[1] for row in con.execute("pragma table_info(claim_events)").fetchall()}
        if col not in existing:
            con.execute(ddl)
    con.commit()
    return con


def row_to_claim(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {
        "task_id": row["task_id"],
        "owner": row["owner"],
        "status": row["status"],
        "claim_ts": row["claim_ts"],
        "expires_at": row["expires_at"],
        "metadata": json.loads(row["metadata_json"] or "{}"),
        "lineage": json.loads(row["lineage_json"] or "[]"),
    }


def get_claim(task_id: str, con: sqlite3.Connection | None = None) -> dict | None:
    close = con is None
    con = con or ensure_db()
    try:
        row = con.execute("select * from claims where task_id = ?", (task_id,)).fetchone()
        return row_to_claim(row)
    finally:
        if close:
            con.close()


def is_active_claim(claim: dict | None, at: float | None = None) -> bool:
    if not claim:
        return False
    at = at if at is not None else now_epoch()
    return claim.get("status") == "active" and float(claim.get("expires_at", 0)) > at


def event_hash_payload(ts: float, event: str, task_id: str, owner: str | None, details_json: str, previous_event_hash: str) -> str:
    return sha256_json({
        "schema_version": LEDGER_SCHEMA_VERSION,
        "ts": ts,
        "event": event,
        "task_id": task_id,
        "owner": owner,
        "details_json": details_json,
        "previous_event_hash": previous_event_hash,
    })


def record_event(con: sqlite3.Connection, event: str, task_id: str, owner: str | None = None, details: dict | None = None) -> None:
    details_json = canonical_json(details or {})
    row = con.execute("select event_hash from claim_events order by id desc limit 1").fetchone()
    previous = row[0] if row and row[0] else ""
    ts = now_epoch()
    digest = event_hash_payload(ts, event, task_id, owner, details_json, previous)
    con.execute(
        "insert into claim_events(ts, event, task_id, owner, details_json, previous_event_hash, event_hash, schema_version) values (?, ?, ?, ?, ?, ?, ?, ?)",
        (ts, event, task_id, owner, details_json, previous, digest, LEDGER_SCHEMA_VERSION),
    )


def verify_ledger() -> dict:
    con = ensure_db()
    violations: list[dict] = []
    try:
        rows = con.execute("select * from claim_events order by id asc").fetchall()
        previous = ""
        for row in rows:
            if (row["previous_event_hash"] or "") != previous:
                violations.append({"type": "event_chain_break", "id": row["id"], "expected_previous": previous, "actual_previous": row["previous_event_hash"]})
            digest = event_hash_payload(row["ts"], row["event"], row["task_id"], row["owner"], row["details_json"], row["previous_event_hash"] or "")
            if digest != row["event_hash"]:
                violations.append({"type": "event_hash_mismatch", "id": row["id"], "expected": row["event_hash"], "actual": digest})
            previous = row["event_hash"] or ""
        return {"schema": "hermes_claim_ledger_verify_v1", "passed": not violations, "checked_events": len(rows), "violations": violations}
    finally:
        con.close()


def claim_task(task_id: str, owner: str, ttl: int = 3600, metadata: dict | None = None, *, exit_code: bool = False) -> dict:
    con = ensure_db()
    try:
        con.execute("BEGIN IMMEDIATE")
        current = get_claim(task_id, con)
        if is_active_claim(current):
            return {"ok": False, "reason": "active_claim_exists", "claim": current}
        ts = now_epoch()
        expires_at = ts + max(1, int(ttl))
        lineage = (current or {}).get("lineage", []) if current else []
        lineage.append({"event": "claim", "owner": owner, "ts": now_ts()})
        con.execute(
            "insert or replace into claims(task_id, owner, status, claim_ts, expires_at, metadata_json, lineage_json) values (?, ?, 'active', ?, ?, ?, ?)",
            (task_id, owner, ts, expires_at, canonical_json(metadata or {}), canonical_json(lineage)),
        )
        record_event(con, "claim", task_id, owner, {"ttl": ttl})
        con.commit()
        return {"ok": True, "claim": get_claim(task_id, con)}
    finally:
        con.close()


def release_task(task_id: str, owner: str) -> dict:
    if not owner:
        return {"ok": False, "reason": "owner_required"}
    con = ensure_db()
    try:
        con.execute("BEGIN IMMEDIATE")
        current = get_claim(task_id, con)
        if not current:
            return {"ok": False, "reason": "claim_not_found"}
        if owner and current.get("owner") != owner:
            return {"ok": False, "reason": "owner_mismatch", "claim": current}
        lineage = current.get("lineage", []) + [{"event": "release", "owner": current.get("owner"), "ts": now_ts()}]
        con.execute("update claims set status = 'released', lineage_json = ? where task_id = ?", (canonical_json(lineage), task_id))
        record_event(con, "release", task_id, current.get("owner"), {})
        con.commit()
        return {"ok": True, "claim": get_claim(task_id, con)}
    finally:
        con.close()


def handoff_task(task_id: str, from_owner: str, to_owner: str, ttl: int = 3600) -> dict:
    con = ensure_db()
    try:
        con.execute("BEGIN IMMEDIATE")
        current = get_claim(task_id, con)
        if not is_active_claim(current):
            return {"ok": False, "reason": "no_active_claim", "claim": current}
        if current.get("owner") != from_owner:
            return {"ok": False, "reason": "owner_mismatch", "claim": current}
        ts = now_epoch()
        lineage = current.get("lineage", []) + [{"event": "handoff", "from": from_owner, "to": to_owner, "ts": now_ts()}]
        con.execute(
            "update claims set owner = ?, claim_ts = ?, expires_at = ?, lineage_json = ? where task_id = ?",
            (to_owner, ts, ts + max(1, int(ttl)), canonical_json(lineage), task_id),
        )
        record_event(con, "handoff", task_id, to_owner, {"from": from_owner, "to": to_owner, "ttl": ttl})
        con.commit()
        return {"ok": True, "claim": get_claim(task_id, con)}
    finally:
        con.close()


def steal_task(task_id: str, owner: str, ttl: int = 3600) -> dict:
    con = ensure_db()
    try:
        con.execute("BEGIN IMMEDIATE")
        current = get_claim(task_id, con)
        if is_active_claim(current):
            return {"ok": False, "reason": "active_claim_exists", "claim": current}
        ts = now_epoch()
        previous_owner = current.get("owner") if current else None
        lineage = (current or {}).get("lineage", []) if current else []
        lineage.append({"event": "steal", "from": previous_owner, "to": owner, "ts": now_ts()})
        con.execute(
            "insert or replace into claims(task_id, owner, status, claim_ts, expires_at, metadata_json, lineage_json) values (?, ?, 'active', ?, ?, ?, ?)",
            (task_id, owner, ts, ts + max(1, int(ttl)), canonical_json((current or {}).get("metadata", {})), canonical_json(lineage)),
        )
        record_event(con, "steal", task_id, owner, {"from": previous_owner, "ttl": ttl})
        con.commit()
        return {"ok": True, "claim": get_claim(task_id, con)}
    finally:
        con.close()


def claim_status(task_id: str) -> dict:
    claim = get_claim(task_id)
    return {"ok": claim is not None, "claim": claim, "active": is_active_claim(claim)}


def as_number(value: Any) -> tuple[float | None, bool]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, False
    if number != number or number in (float("inf"), float("-inf")):
        return None, False
    return number, True


BUDGET_CHECKS = [
    ("hop_limit_exceeded", "hop_count", "max_hops"),
    ("token_budget_exceeded", "spent_tokens", "max_tokens"),
    ("cost_budget_exceeded", "spent_usd", "max_usd"),
    ("tool_call_budget_exceeded", "tool_calls", "max_tool_calls"),
    ("walltime_budget_exceeded", "elapsed_seconds", "max_wall_seconds"),
]


def check_budget(envelope: dict) -> dict:
    violations: list[dict] = []
    if not isinstance(envelope, dict):
        envelope = {}
        violations.append({"type": "malformed_envelope"})
    for vtype, spent_key, max_key in BUDGET_CHECKS:
        for key in (spent_key, max_key):
            if key not in envelope:
                violations.append({"type": "missing_budget_field", "field": key})
        if spent_key not in envelope or max_key not in envelope:
            continue
        spent, spent_ok = as_number(envelope.get(spent_key))
        limit, limit_ok = as_number(envelope.get(max_key))
        if not spent_ok:
            violations.append({"type": "invalid_budget_number", "field": spent_key, "value": envelope.get(spent_key)})
            continue
        if not limit_ok:
            violations.append({"type": "invalid_budget_number", "field": max_key, "value": envelope.get(max_key)})
            continue
        if spent < 0 or limit < 0:
            violations.append({"type": "negative_budget_number", "spent_key": spent_key, "max_key": max_key, "spent": spent, "limit": limit})
            continue
        if spent > limit:
            violations.append({"type": vtype, "spent_key": spent_key, "max_key": max_key, "spent": spent, "limit": limit})
    passed = not violations
    return {
        "schema": "hermes_delegation_budget_v1",
        "passed": passed,
        "action": "proceed" if passed else "block",
        "violations": violations,
        "envelope_hash": sha256_json(envelope),
    }


def emit(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hermes long-term evolution governance guard")
    parser.add_argument("--root", default=None, help="Hermes root, default HERMES_HOME or ~/.hermes")
    parser.add_argument("--json", action="store_true", help="Retained for compatibility; output is always JSON")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("inventory", help="Build capability inventory")
    p.add_argument("--out", default=None)

    p = sub.add_parser("witness", help="Create local signed/HMAC witness")
    p.add_argument("--out", default=None)
    p.add_argument("--key", default=None)

    p = sub.add_parser("verify", help="Verify capability witness")
    p.add_argument("--witness", default=None)
    p.add_argument("--exit-code", action="store_true")

    p = sub.add_parser("claim", help="Claim a task lease")
    p.add_argument("--task", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--ttl", type=int, default=3600)
    p.add_argument("--metadata-json", default="{}")
    p.add_argument("--exit-code", action="store_true")

    p = sub.add_parser("claim-status", help="Inspect a task claim")
    p.add_argument("--task", required=True)

    p = sub.add_parser("release", help="Release a task claim")
    p.add_argument("--task", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--exit-code", action="store_true")

    p = sub.add_parser("handoff", help="Transfer a task claim")
    p.add_argument("--task", required=True)
    p.add_argument("--from-owner", required=True)
    p.add_argument("--to-owner", required=True)
    p.add_argument("--ttl", type=int, default=3600)
    p.add_argument("--exit-code", action="store_true")

    p = sub.add_parser("steal", help="Steal an expired or released task claim")
    p.add_argument("--task", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--ttl", type=int, default=3600)
    p.add_argument("--exit-code", action="store_true")

    p = sub.add_parser("ledger-verify", help="Verify claim event hash chain")
    p.add_argument("--exit-code", action="store_true")

    p = sub.add_parser("budget-check", help="Check delegation budget envelope")
    p.add_argument("--envelope", required=True, help="JSON object or path to JSON file")
    p.add_argument("--exit-code", action="store_true")
    return parser


def parse_json_arg(value: str) -> dict:
    path = Path(value).expanduser()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = resolve_root(args.root)
    code = 0
    if args.cmd == "inventory":
        data = build_inventory(root)
        if args.out:
            out = Path(args.out).expanduser().resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            data = {"ok": True, "inventory_path": str(out), **data}
    elif args.cmd == "witness":
        data = create_witness(root, args.out, args.key)
    elif args.cmd == "verify":
        data = verify_witness(args.witness or default_witness_path(), root=root)
        if args.exit_code and not data["passed"]:
            code = 2
    elif args.cmd == "claim":
        data = claim_task(args.task, args.owner, args.ttl, parse_json_arg(args.metadata_json))
        if args.exit_code and not data["ok"]:
            code = 2
    elif args.cmd == "claim-status":
        data = claim_status(args.task)
    elif args.cmd == "release":
        data = release_task(args.task, args.owner)
        if args.exit_code and not data["ok"]:
            code = 2
    elif args.cmd == "handoff":
        data = handoff_task(args.task, args.from_owner, args.to_owner, args.ttl)
        if args.exit_code and not data["ok"]:
            code = 2
    elif args.cmd == "steal":
        data = steal_task(args.task, args.owner, args.ttl)
        if args.exit_code and not data["ok"]:
            code = 2
    elif args.cmd == "ledger-verify":
        data = verify_ledger()
        if args.exit_code and not data["passed"]:
            code = 2
    elif args.cmd == "budget-check":
        data = check_budget(parse_json_arg(args.envelope))
        if args.exit_code and not data["passed"]:
            code = 2
    else:
        raise SystemExit(f"unknown command: {args.cmd}")
    emit(data)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
