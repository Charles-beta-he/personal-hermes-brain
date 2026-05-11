#!/usr/bin/env python3
"""model_quota.py — provider quota observability and gating.

This module deliberately separates exact quota data from estimates and
unobservable subscription caps. Unknown is never treated as proof of abundance.
It is, however, allowed by default for routing/fan-out because many providers do
not expose an official quota API.
"""

import argparse
import email.utils
import json
import math
import os
import sys
import time
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or isinstance(value, bool):
        return default
    try:
        number = float(str(value).strip())
        if not math.isfinite(number):
            return default
        return int(number)
    except (TypeError, ValueError, OverflowError):
        return default


HERMES_HOME = os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes"))
STATE_DIR = os.path.join(HERMES_HOME, "state")
LOG_DIR = os.path.join(HERMES_HOME, "logs")
STATE_FILE = os.path.join(STATE_DIR, "model_quota_state.json")
LOG_FILE = os.path.join(LOG_DIR, "model-quota.jsonl")
_STATE_LOAD_ERROR_KEY = "__state_load_error__"
RISKY_STATUS_FOR_PROVIDER_RECONCILE = {"exhausted", "rate_limited", "malformed", "unavailable"}
VALID_QUOTA_STATUSES = {"ok", "low", "unknown", "unobservable", "exhausted", "rate_limited", "reset_elapsed", "stale_exhausted", "malformed", "unavailable"}
DEFAULT_STALE_AFTER_SECONDS = 300
LOW_TOKEN_THRESHOLD = _env_int("HERMES_QUOTA_LOW_TOKEN_THRESHOLD", 1000)
LOW_REQUEST_THRESHOLD = _env_int("HERMES_QUOTA_LOW_REQUEST_THRESHOLD", 3)
DEFAULT_T3_MODELS = ["claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro", "mimo-v2.5-pro"]
CONFIDENCE_BLOCKING_STATUSES = {"low", "unknown", "unobservable", "exhausted", "rate_limited", "malformed", "unavailable"}

SUBSCRIPTION_PROVIDERS = {"openai-codex", "qwen-oauth"}
HEADER_TOKEN_KEYS = (
    "x-ratelimit-remaining-tokens",
    "anthropic-ratelimit-tokens-remaining",
    "x-ratelimit-remaining-token",
    "ratelimit-remaining-tokens",
)
HEADER_REQUEST_KEYS = (
    "x-ratelimit-remaining-requests",
    "anthropic-ratelimit-requests-remaining",
    "x-ratelimit-remaining-request",
    "ratelimit-remaining-requests",
)
HEADER_RESET_KEYS = (
    "x-ratelimit-reset-tokens",
    "x-ratelimit-reset-requests",
    "anthropic-ratelimit-tokens-reset",
    "anthropic-ratelimit-requests-reset",
    "ratelimit-reset",
    "retry-after",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _format_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_reset_at(value: Any, now: Optional[datetime] = None) -> Optional[str]:
    """Normalize Retry-After / rate-limit reset values to UTC ISO-8601.

    Accepts delta seconds ("120"), ISO timestamps, and HTTP-date strings.
    Malformed/non-finite/bool inputs return None so routing remains fail-closed.
    """
    if value in (None, "") or isinstance(value, bool):
        return None
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        seconds = float(text)
        if math.isfinite(seconds) and seconds >= 0:
            return _format_utc_iso(now + timedelta(seconds=seconds))
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return _format_utc_iso(dt)
    except (TypeError, ValueError):
        pass
    try:
        dt = email.utils.parsedate_to_datetime(text)
        if dt is not None:
            return _format_utc_iso(dt)
    except (TypeError, ValueError, IndexError, OverflowError):
        pass
    return None


def seconds_until_reset(reset_at: Any, now: Optional[datetime] = None) -> Optional[int]:
    normalized = parse_reset_at(reset_at, now=now)
    if not normalized:
        return None
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None
    return int(math.ceil((dt - now.astimezone(timezone.utc)).total_seconds()))


def quota_key(provider: str, model: str) -> str:
    return f"{provider or 'unknown'}::{model}"


def provider_for_model(model: str, config: Optional[dict] = None) -> str:
    if config:
        provider = (
            config.get("pricing", {})
            .get("models", {})
            .get(model, {})
            .get("provider")
        )
        if provider:
            return provider
    lower = (model or "").lower()
    if "claude" in lower:
        return "anthropic"
    if "deepseek" in lower:
        return "deepseek"
    if "mimo" in lower:
        return "xiaomi"
    if "gpt" in lower or "codex" in lower:
        return "openai-codex"
    return "unknown"


def _load_env_file(path: Optional[str] = None) -> dict:
    path = path or os.path.join(HERMES_HOME, ".env")
    data = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                data[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return data


def _to_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).strip())
        if not math.isfinite(number):
            return None
        return int(number)
    except (TypeError, ValueError, OverflowError):
        return None


def _to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return default
    try:
        number = float(str(value).strip())
        if not math.isfinite(number):
            return default
        return number
    except (TypeError, ValueError, OverflowError):
        return default


def _parse_utc_datetime(value: Any) -> Optional[datetime]:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _first_header(headers: dict, keys: Iterable[str]) -> Optional[str]:
    lowered = {str(k).lower(): v for k, v in (headers or {}).items()}
    for key in keys:
        if key in lowered and lowered[key] not in (None, ""):
            return str(lowered[key])
    return None


def _status_from_remaining(remaining_tokens: Optional[int], remaining_requests: Optional[int]) -> str:
    if (remaining_tokens is not None and remaining_tokens <= 0) or (remaining_requests is not None and remaining_requests <= 0):
        return "exhausted"
    if remaining_tokens is not None and remaining_tokens <= LOW_TOKEN_THRESHOLD:
        return "low"
    if remaining_requests is not None and remaining_requests <= LOW_REQUEST_THRESHOLD:
        return "low"
    return "ok"


def _transient_exhaustion_is_stale(snap: dict, now: datetime) -> bool:
    if snap.get("reset_at"):
        return False
    quota_type = str(snap.get("quota_type", ""))
    error_class = str(snap.get("error_class", ""))
    if quota_type not in {"rate_limit_window", "provider_overload"} and error_class not in {"rate_limit", "provider_overloaded"}:
        return False
    stale_after = _to_float(snap.get("stale_after_seconds"), default=DEFAULT_STALE_AFTER_SECONDS)
    if stale_after is None or stale_after <= 0:
        return False
    updated = _parse_utc_datetime(snap.get("last_updated"))
    if updated is None:
        return False
    return (now.astimezone(timezone.utc) - updated).total_seconds() > stale_after


def default_snapshot(model: str, provider: Optional[str] = None) -> dict:
    provider = provider or provider_for_model(model)
    if provider in SUBSCRIPTION_PROVIDERS:
        status = "unobservable"
        observability = "unobservable"
        quota_type = "subscription_cap"
        confidence = 0.2
    else:
        status = "unknown"
        observability = "unknown"
        quota_type = "unknown"
        confidence = 0.1
    return {
        "model": model,
        "provider": provider,
        "status": status,
        "observability": observability,
        "quota_type": quota_type,
        "remaining_tokens": None,
        "remaining_requests": None,
        "remaining_usd": None,
        "reset_at": None,
        "source": "default",
        "confidence": confidence,
        "stale_after_seconds": DEFAULT_STALE_AFTER_SECONDS,
        "last_updated": now_iso(),
    }


def snapshot_from_headers(model: str, provider: str, headers: dict, usage: Optional[dict] = None) -> dict:
    remaining_tokens = _to_int(_first_header(headers, HEADER_TOKEN_KEYS))
    remaining_requests = _to_int(_first_header(headers, HEADER_REQUEST_KEYS))
    reset_raw = _first_header(headers, HEADER_RESET_KEYS)
    reset_at = parse_reset_at(reset_raw) if reset_raw else None
    reset_after_seconds = seconds_until_reset(reset_at) if reset_at else None
    base = default_snapshot(model, provider)
    if remaining_tokens is None and remaining_requests is None and not reset_at:
        base.update({
            "source": "response_headers",
            "usage": usage or {},
            "last_updated": now_iso(),
        })
        return base
    base.update({
        "status": _status_from_remaining(remaining_tokens, remaining_requests),
        "observability": "window_exact",
        "quota_type": "rate_limit_window",
        "remaining_tokens": remaining_tokens,
        "remaining_requests": remaining_requests,
        "reset_at": reset_at,
        "reset_after_seconds": reset_after_seconds,
        "raw_reset": reset_raw,
        "source": "response_headers",
        "confidence": 0.9,
        "usage": usage or {},
        "last_updated": now_iso(),
    })
    return base


def _classify_error(text: str) -> Tuple[str, str]:
    text = (text or "").lower()
    if "429" in text or "rate limit" in text or "rate_limit" in text:
        return "rate_limit", "rate_limit_window"
    if "529" in text or "overloaded" in text or "503" in text or "temporarily unavailable" in text:
        return "provider_overloaded", "provider_overload"
    if "billing" in text or "quota" in text or "insufficient" in text or "balance" in text:
        return "billing_limit", "billing_balance"
    return "unknown", "unknown"


def snapshot_from_error(
    model: str,
    provider: str,
    error: str,
    retry_after: Optional[str] = None,
    now: Optional[datetime] = None,
) -> dict:
    text = (error or "").lower()
    error_class, quota_type = _classify_error(text)
    reset_at = parse_reset_at(retry_after, now=now) if retry_after else None
    reset_after = seconds_until_reset(reset_at, now=now) if reset_at else None
    snap = default_snapshot(model, provider)
    if error_class in {"rate_limit", "provider_overloaded"}:
        snap.update({
            "status": "exhausted",
            "observability": "inferred",
            "quota_type": quota_type,
            "error_class": error_class,
            "reset_at": reset_at,
            "reset_after_seconds": reset_after,
            "raw_retry_after": retry_after,
            "source": "error_inference",
            "confidence": 0.7 if reset_at else 0.6,
        })
    elif error_class == "billing_limit":
        snap.update({
            "status": "exhausted",
            "observability": "inferred",
            "quota_type": quota_type,
            "error_class": error_class,
            "source": "error_inference",
            "confidence": 0.75,
        })
    else:
        snap.update({"source": "error_inference", "error_class": error_class, "confidence": 0.2})
    snap["last_updated"] = now_iso()
    return snap


def snapshot_unobservable_success(
    model: str,
    provider: str,
    *,
    source: str,
    quota_type: str,
    header_names: Optional[List[str]] = None,
    usage: Optional[dict] = None,
    evidence_note: str = "successful_call_without_quota_headers",
    confidence: float = 0.35,
) -> dict:
    """Record a real successful call that exposed no quota/balance evidence.

    This is positive runtime availability evidence, not budget evidence. It keeps
    routing/actionability honest by distinguishing "not checked" from "checked,
    but provider route is unobservable", while still failing confidence gates.
    """
    snap = default_snapshot(model, provider)
    snap.update({
        "status": "unobservable",
        "observability": "unobservable",
        "quota_type": quota_type,
        "remaining_tokens": None,
        "remaining_requests": None,
        "remaining_usd": None,
        "reset_at": None,
        "source": source,
        "confidence": max(0.0, min(float(confidence), 0.49)),
        "usage": usage or {},
        "header_names": sorted({str(k).lower() for k in (header_names or [])}),
        "evidence_note": evidence_note,
        "policy_scope": "low_risk_routing_only; not_budget_handoff_certification",
        "stale_after_seconds": DEFAULT_STALE_AFTER_SECONDS,
        "last_updated": now_iso(),
    })
    return snap


def load_state(path: str = STATE_FILE) -> dict:
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        return {_STATE_LOAD_ERROR_KEY: {"status": "malformed", "reason": type(exc).__name__}}
    if data is None:
        return {_STATE_LOAD_ERROR_KEY: {"status": "malformed", "reason": "null_state"}}
    if not isinstance(data, dict):
        return {_STATE_LOAD_ERROR_KEY: {"status": "malformed", "reason": "non_dict_state"}}
    return data


def save_state(state: dict, path: str = STATE_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="model_quota_", suffix=".json", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except OSError:
            pass


def append_log(entry: dict, path: str = LOG_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def _snapshot_age_seconds(snapshot: dict) -> Optional[int]:
    updated = _parse_utc_datetime((snapshot or {}).get("last_updated")) if isinstance(snapshot, dict) else None
    if updated is None:
        return None
    return int(max(0, (datetime.now(timezone.utc) - updated).total_seconds()))


def _is_snapshot_stale(snapshot: dict) -> bool:
    if not isinstance(snapshot, dict):
        return True
    age = _snapshot_age_seconds(snapshot)
    if age is None:
        return True
    stale_after = _to_float(snapshot.get("stale_after_seconds"), default=DEFAULT_STALE_AFTER_SECONDS)
    return bool(stale_after and stale_after > 0 and age > stale_after)


def _quota_snapshot_quality(snapshot: dict) -> Tuple[int, float]:
    """Return comparable evidence quality for update ordering.

    Higher tier is better. Exhaustion/rate-limit evidence is intentionally high
    because safety blockers must overwrite optimistic prior snapshots. Empty
    response headers are low-quality and must not erase a fresh exact balance.
    """
    if not isinstance(snapshot, dict):
        return (0, 0.0)
    status = str(snapshot.get("status") or "unknown")
    observability = str(snapshot.get("observability") or "unknown")
    quota_type = str(snapshot.get("quota_type") or "unknown")
    confidence = _to_float(snapshot.get("confidence"), default=0.0) or 0.0
    if status in {"exhausted", "rate_limited"}:
        return (5, confidence)
    if observability in {"exact", "window_exact"} or observability.startswith("exact"):
        return (4, confidence)
    if observability.startswith("estimated"):
        return (3, confidence)
    if quota_type in {"rate_limit_window", "billing_balance"} and confidence >= 0.5:
        return (3, confidence)
    if status == "low":
        return (2, confidence)
    if observability == "unobservable":
        return (1, confidence)
    return (0, confidence)


def _should_replace_snapshot(existing: Optional[dict], incoming: dict) -> Tuple[bool, str]:
    if not isinstance(existing, dict):
        return True, "no_existing_snapshot"
    existing_quality = _quota_snapshot_quality(existing)
    incoming_quality = _quota_snapshot_quality(incoming)
    if str(incoming.get("status") or "") in {"exhausted", "rate_limited"}:
        return True, "incoming_safety_blocker"
    if _is_snapshot_stale(existing):
        return True, "existing_stale"
    if incoming_quality[0] > existing_quality[0]:
        return True, "incoming_higher_observability"
    if incoming_quality[0] == existing_quality[0] and incoming_quality[1] >= existing_quality[1]:
        return True, "incoming_equal_or_higher_confidence"
    return False, "preserve_higher_confidence_existing_snapshot"


def record_snapshot(snapshot: dict, state_path: str = STATE_FILE, log_path: str = LOG_FILE, *, preserve_higher_confidence: bool = True) -> dict:
    state = load_state(state_path)
    key = quota_key(snapshot.get("provider", "unknown"), snapshot.get("model", "unknown"))
    existing = state.get(key) if isinstance(state, dict) else None
    should_replace, reason = _should_replace_snapshot(existing, snapshot) if preserve_higher_confidence else (True, "forced_replace")
    if should_replace:
        state[key] = snapshot
        save_state(state, state_path)
        append_log({"ts": now_iso(), "event": "quota_snapshot", "key": key, "snapshot": snapshot, "update_reason": reason}, log_path)
        return snapshot
    preserved = dict(existing)
    preserved["preserved_from_lower_confidence_update"] = True
    preserved["ignored_update"] = {
        "status": snapshot.get("status"),
        "observability": snapshot.get("observability"),
        "source": snapshot.get("source"),
        "confidence": snapshot.get("confidence"),
        "last_updated": snapshot.get("last_updated"),
        "reason": reason,
    }
    append_log({"ts": now_iso(), "event": "quota_snapshot_preserved", "key": key, "snapshot": preserved, "incoming": snapshot, "update_reason": reason}, log_path)
    return preserved


def record_call(
    model: str,
    provider: Optional[str] = None,
    ok: bool = True,
    headers: Optional[dict] = None,
    usage: Optional[dict] = None,
    error: str = "",
    state_path: str = STATE_FILE,
    log_path: str = LOG_FILE,
) -> dict:
    provider = provider or provider_for_model(model)
    if ok:
        snapshot = snapshot_from_headers(model, provider, headers or {}, usage=usage)
    else:
        retry_after = _first_header(headers or {}, ("retry-after", "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens"))
        snapshot = snapshot_from_error(model, provider, error, retry_after=retry_after)
    return record_snapshot(snapshot, state_path=state_path, log_path=log_path)


def snapshot_models(
    models: List[str],
    config: Optional[dict] = None,
    state_path: str = STATE_FILE,
    providers: Optional[dict] = None,
) -> dict:
    state = load_state(state_path)
    state_error = state.get(_STATE_LOAD_ERROR_KEY) if isinstance(state, dict) else None
    providers = providers or {}
    result = {}
    for model in models:
        provider = providers.get(model) or provider_for_model(model, config)
        key = quota_key(provider, model)
        if state_error:
            result[key] = {
                "model": model,
                "provider": provider,
                "status": "malformed",
                "observability": "malformed",
                "quota_type": "state_file",
                "source": "quota_state",
                "reason": "quota_state_malformed",
                "state_error": state_error,
                "confidence": 1.0,
            }
        else:
            exact_snapshot = state.get(key)
            if isinstance(exact_snapshot, dict):
                raw_status = exact_snapshot.get("status")
                snap_model = exact_snapshot.get("model")
                snap_provider = exact_snapshot.get("provider")
                valid_exact = (
                    isinstance(raw_status, str)
                    and raw_status.strip() in VALID_QUOTA_STATUSES
                    and snap_model == model
                    and snap_provider == provider
                )
                if valid_exact:
                    result[key] = exact_snapshot
                else:
                    result[key] = {
                        "model": model,
                        "provider": provider,
                        "status": "malformed",
                        "observability": "malformed",
                        "quota_type": "state_entry",
                        "source": "quota_state",
                        "reason": "quota_snapshot_malformed",
                        "state_entry_key": key,
                        "malformed_status": raw_status,
                        "state_model": snap_model,
                        "state_provider": snap_provider,
                        "confidence": 1.0,
                    }
                continue
            if key in state:
                result[key] = {
                    "model": model,
                    "provider": provider,
                    "status": "malformed",
                    "observability": "malformed",
                    "quota_type": "state_entry",
                    "source": "quota_state",
                    "reason": "quota_snapshot_malformed",
                    "state_entry_key": key,
                    "confidence": 1.0,
                }
                continue
            reconciled = None
            reconciled_key = None
            for state_key, candidate in state.items():
                if state_key == _STATE_LOAD_ERROR_KEY or not isinstance(candidate, dict):
                    continue
                candidate_model = candidate.get("model")
                key_model = str(state_key).split("::", 1)[1] if "::" in str(state_key) else None
                if candidate_model != model and key_model != model:
                    continue
                status = candidate.get("status")
                if isinstance(status, str) and status.strip() in RISKY_STATUS_FOR_PROVIDER_RECONCILE:
                    reconciled = dict(candidate)
                    reconciled_key = state_key
                    break
            if reconciled is not None:
                previous_provider = reconciled.get("provider")
                reconciled.update({
                    "model": model,
                    "provider": provider,
                    "reconciled_from_key": reconciled_key,
                    "reconciled_from_provider": previous_provider,
                })
                result[key] = reconciled
            else:
                result[key] = default_snapshot(model, provider)
    return result


def gate_models(
    models: List[str],
    snapshots: Optional[dict] = None,
    providers: Optional[dict] = None,
    now: Optional[datetime] = None,
) -> Tuple[List[str], List[dict]]:
    if snapshots is None:
        snapshots = {}
    if not isinstance(snapshots, dict):
        providers = providers or {}
        return [], [
            {
                "model": model,
                "provider": providers.get(model) or provider_for_model(model),
                "reason": "quota_snapshot_malformed",
                "snapshot": {"model": model, "status": "malformed", "source": "quota_state"},
            }
            for model in models
        ]
    providers = providers or {}
    now = now or datetime.now(timezone.utc)
    allowed: List[str] = []
    skipped: List[dict] = []
    for model in models:
        provider = providers.get(model) or provider_for_model(model)
        snap = snapshots.get(quota_key(provider, model)) or snapshots.get(model)
        if snap is None:
            for snapshot_key, candidate in snapshots.items():
                if not isinstance(candidate, dict):
                    continue
                candidate_model = candidate.get("model")
                key_model = str(snapshot_key).split("::", 1)[1] if "::" in str(snapshot_key) else None
                status = candidate.get("status")
                if (candidate_model == model or key_model == model) and isinstance(status, str) and status.strip() in RISKY_STATUS_FOR_PROVIDER_RECONCILE:
                    snap = dict(candidate)
                    snap.update({
                        "model": model,
                        "provider": provider,
                        "reconciled_from_key": snapshot_key,
                        "reconciled_from_provider": candidate.get("provider"),
                    })
                    break
        if snap is None:
            snap = default_snapshot(model, provider)
        if not isinstance(snap, dict):
            skipped.append({
                "model": model,
                "provider": provider,
                "reason": "quota_snapshot_malformed",
                "reset_at": None,
                "seconds_until_reset": None,
                "snapshot": {"model": model, "provider": provider, "status": "malformed", "source": "quota_state"},
            })
            continue
        snap_model = snap.get("model")
        snap_provider = snap.get("provider")
        if snap_model != model or snap_provider != provider:
            skipped.append({
                "model": model,
                "provider": provider,
                "reason": "quota_snapshot_malformed",
                "reset_at": snap.get("reset_at"),
                "seconds_until_reset": None,
                "snapshot": snap,
            })
            continue
        raw_status = snap.get("status")
        if not isinstance(raw_status, str) or not raw_status.strip() or raw_status.strip() not in VALID_QUOTA_STATUSES:
            skipped.append({
                "model": model,
                "provider": provider,
                "reason": "quota_snapshot_malformed_status",
                "reset_at": snap.get("reset_at"),
                "seconds_until_reset": None,
                "snapshot": snap,
            })
            continue
        status = raw_status.strip()
        if status in {"malformed", "unavailable"}:
            skipped.append({
                "model": model,
                "provider": provider,
                "reason": snap.get("reason") or f"quota_snapshot_{status}",
                "reset_at": snap.get("reset_at"),
                "seconds_until_reset": None,
                "snapshot": snap,
            })
            continue
        if status in {"exhausted", "rate_limited"}:
            reset_at = snap.get("reset_at")
            seconds_left = seconds_until_reset(reset_at, now=now) if reset_at else None
            if reset_at and seconds_left is not None and seconds_left <= 0:
                snap["previous_status"] = "exhausted"
                snap["status"] = "reset_elapsed"
                snap["reset_elapsed"] = True
                confidence = _to_float(snap.get("confidence"), default=0.5)
                snap["confidence"] = max(0.0, min(confidence if confidence is not None else 0.5, 0.55))
                allowed.append(model)
                continue
            if _transient_exhaustion_is_stale(snap, now):
                snap["previous_status"] = "exhausted"
                snap["status"] = "stale_exhausted"
                snap["stale_elapsed"] = True
                confidence = _to_float(snap.get("confidence"), default=0.4)
                snap["confidence"] = max(0.0, min(confidence if confidence is not None else 0.4, 0.45))
                allowed.append(model)
                continue
            reason = "quota_exhausted"
            if reset_at and seconds_left is not None:
                reason = "quota_exhausted_until_reset"
            elif reset_at and seconds_left is None:
                reason = "quota_exhausted_reset_malformed"
            skipped.append({
                "model": model,
                "provider": provider,
                "reason": reason,
                "reset_at": reset_at,
                "seconds_until_reset": seconds_left,
                "snapshot": snap,
            })
        else:
            allowed.append(model)
    return allowed, skipped


def quota_observability_evidence(snapshots: dict, min_confidence: float = 0.50) -> dict:
    """Summarize quota observability as machine-readable evidence.

    This is deliberately separate from the pass/fail decision so downstream
    gates can cite why a provider is or is not safe for budget handoff without
    treating absence of data as success.
    """
    generated = datetime.now(timezone.utc)
    by_model = {}
    counts = {
        "total": 0,
        "usable": 0,
        "exact": 0,
        "estimated": 0,
        "unknown": 0,
        "unobservable": 0,
        "malformed": 0,
        "stale": 0,
        "low_confidence": 0,
    }
    refresh_actions = []
    for key, snap in sorted((snapshots or {}).items()):
        counts["total"] += 1
        if not isinstance(snap, dict):
            counts["malformed"] += 1
            by_model[str(key)] = {
                "status": "malformed",
                "observability": "malformed",
                "confidence": 0.0,
                "evidence_state": "invalid_snapshot",
                "refresh_action": "repair_model_quota_state_json",
            }
            refresh_actions.append("repair_model_quota_state_json")
            continue
        observability = str(snap.get("observability") or "unknown")
        if observability in counts:
            counts[observability] += 1
        elif observability.startswith("exact"):
            counts["exact"] += 1
        elif observability.startswith("estimated"):
            counts["estimated"] += 1
        else:
            counts["unknown"] += 1
        confidence = _to_float(snap.get("confidence"), default=0.0) or 0.0
        updated = _parse_utc_datetime(snap.get("last_updated"))
        age_seconds = None
        stale = False
        if updated is not None:
            age_seconds = int(max(0, (generated - updated).total_seconds()))
            stale_after = _to_float(snap.get("stale_after_seconds"), default=DEFAULT_STALE_AFTER_SECONDS)
            stale = bool(stale_after and stale_after > 0 and age_seconds > stale_after)
        else:
            stale = True
        if stale:
            counts["stale"] += 1
        if confidence < min_confidence:
            counts["low_confidence"] += 1
        refresh_action = "none"
        provider = str(snap.get("provider") or "unknown")
        status = str(snap.get("status") or "unknown")
        usable_for_budget = status == "ok" and confidence >= min_confidence and not stale
        if usable_for_budget:
            counts["usable"] += 1
        if observability == "unobservable":
            if str(snap.get("source") or "").startswith("direct_api_no_quota_headers"):
                refresh_action = "provider_unobservable_lower_risk_tier_or_documented_policy"
            elif str(snap.get("source") or "").startswith("subprocess_success_no_quota_headers"):
                refresh_action = "use_api_route_for_headers_or_lower_risk_tier"
            else:
                refresh_action = "manual_budget_confirmation_or_lower_risk_tier"
        elif not usable_for_budget and provider == "deepseek":
            refresh_action = "probe_deepseek_balance"
        elif not usable_for_budget and (status in {"unknown", "malformed", "unavailable"} or stale or confidence < min_confidence):
            refresh_action = "record_provider_response_headers"
        if refresh_action != "none":
            refresh_actions.append(refresh_action)
        by_model[str(key)] = {
            "model": snap.get("model"),
            "provider": snap.get("provider"),
            "status": status,
            "observability": observability,
            "quota_type": snap.get("quota_type"),
            "confidence": round(confidence, 4),
            "source": snap.get("source"),
            "last_updated": snap.get("last_updated"),
            "age_seconds": age_seconds,
            "stale": stale,
            "reset_at": snap.get("reset_at"),
            "evidence_state": "usable" if usable_for_budget else "not_sufficient_for_budget_handoff",
            "refresh_action": refresh_action,
        }
    return {
        "schema_version": 1,
        "generated_at": _format_utc_iso(generated),
        "min_confidence": min_confidence,
        "counts": counts,
        "by_model": by_model,
        "refresh_actions": sorted(set(refresh_actions)),
        "policy": "quota observability evidence is advisory for routing but mandatory for budget-handoff/autonomy certification",
    }


def assess_quota_confidence(
    models: List[str],
    min_confidence: float = 0.50,
    config: Optional[dict] = None,
    providers: Optional[dict] = None,
    fail_statuses: Optional[set] = None,
) -> dict:
    """Fail-closed readiness assessment for budget handoff / certification.

    Routing can keep unknown/unobservable providers eligible for low-risk use, but
    budget handoff and autonomous execution require an explicit confidence gate.
    Missing state is converted through snapshot_models() into unknown or
    unobservable snapshots so absence of evidence is never treated as readiness.
    """
    models = [m for m in (models or []) if m]
    min_confidence = max(0.0, min(1.0, _to_float(min_confidence, default=0.50) or 0.50))
    fail_statuses = fail_statuses or CONFIDENCE_BLOCKING_STATUSES
    snapshots = snapshot_models(models, config=config, providers=providers)
    failures: List[dict] = []
    passes: List[dict] = []
    for key, snap in sorted((snapshots or {}).items()):
        if not isinstance(snap, dict):
            failures.append({"key": str(key), "status": "malformed", "reason": "non_dict_snapshot", "confidence": 0.0})
            continue
        model = snap.get("model")
        status = str(snap.get("status") or "unknown").strip()
        confidence = _to_float(snap.get("confidence"), default=0.0) or 0.0
        updated = _parse_utc_datetime(snap.get("last_updated"))
        age_seconds = None
        stale = False
        if updated is None:
            stale = True
        else:
            now = datetime.now(timezone.utc)
            age_seconds = int(max(0, (now - updated).total_seconds()))
            stale_after = _to_float(snap.get("stale_after_seconds"), default=DEFAULT_STALE_AFTER_SECONDS)
            stale = bool(stale_after and stale_after > 0 and age_seconds > stale_after)
        entry = {
            "key": str(key),
            "model": model,
            "provider": snap.get("provider"),
            "status": status,
            "observability": snap.get("observability"),
            "quota_type": snap.get("quota_type"),
            "confidence": round(confidence, 4),
            "source": snap.get("source"),
            "remaining_tokens": snap.get("remaining_tokens"),
            "remaining_requests": snap.get("remaining_requests"),
            "remaining_usd": snap.get("remaining_usd"),
            "reset_at": snap.get("reset_at"),
            "last_updated": snap.get("last_updated"),
            "age_seconds": age_seconds,
            "stale": stale,
        }
        reasons: List[str] = []
        if status in fail_statuses:
            reasons.append(f"status_{status}")
        if confidence < min_confidence:
            reasons.append("low_confidence")
        if stale:
            reasons.append("stale_quota_evidence" if updated is not None else "missing_quota_timestamp")
        if reasons:
            entry["reasons"] = reasons
            failures.append(entry)
        else:
            passes.append(entry)
    status = "PASS" if not failures else "FAIL_CLOSED"
    return {
        "schema_version": 1,
        "status": status,
        "ok": not failures,
        "models_checked": models,
        "min_confidence": min_confidence,
        "blocking_statuses": sorted(fail_statuses),
        "pass_count": len(passes),
        "failure_count": len(failures),
        "passes": passes,
        "failures": failures,
        "snapshots": snapshots,
        "observability_evidence": quota_observability_evidence(snapshots, min_confidence=min_confidence),
        "policy": "unknown/unobservable/low/exhausted quota is allowed for low-risk routing only; budget handoff and autonomy fail closed",
    }


def probe_deepseek_balance(model: str = "deepseek-v4-pro", timeout: int = 10) -> Optional[dict]:
    env_file = _load_env_file()
    key = os.environ.get("DEEPSEEK_API_KEY") or env_file.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    req = urllib.request.Request(
        "https://api.deepseek.com/user/balance",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    balance_infos = data.get("balance_infos") or []
    remaining_usd = None
    total = 0.0
    saw_number = False
    for item in balance_infos:
        amount = item.get("total_balance") or item.get("granted_balance") or item.get("topped_up_balance")
        try:
            parsed = float(amount)
            if not math.isfinite(parsed):
                continue
            total += parsed
            saw_number = True
        except (TypeError, ValueError, OverflowError):
            pass
    if saw_number:
        remaining_usd = round(total, 6)
    snap = default_snapshot(model, "deepseek")
    if remaining_usd is None:
        status = "unknown"
    else:
        status = "ok" if remaining_usd > 0 else "exhausted"
    snap.update({
        "status": status,
        "observability": "exact" if remaining_usd is not None else "unknown",
        "quota_type": "billing_balance",
        "remaining_usd": remaining_usd,
        "source": "balance_endpoint",
        "confidence": 0.85 if remaining_usd is not None else 0.3,
        "raw_balance_available": data.get("is_available"),
        "last_updated": now_iso(),
    })
    return snap


def render_table(snapshots: dict) -> str:
    lines = []
    lines.append(f"{'MODEL':30s} {'PROVIDER':15s} {'STATUS':14s} {'OBS':14s} {'TOKENS':>10s} {'REQ':>6s} {'USD':>10s} RESET")
    for _, snap in sorted(snapshots.items()):
        lines.append(
            f"{str(snap.get('model',''))[:30]:30s} "
            f"{str(snap.get('provider',''))[:15]:15s} "
            f"{str(snap.get('status',''))[:14]:14s} "
            f"{str(snap.get('observability',''))[:14]:14s} "
            f"{str(snap.get('remaining_tokens')):>10s} "
            f"{str(snap.get('remaining_requests')):>6s} "
            f"{str(snap.get('remaining_usd')):>10s} "
            f"{snap.get('reset_at') or '-'}"
        )
    return "\n".join(lines)


def cli() -> None:
    parser = argparse.ArgumentParser(description="Model Quota Monitor — exact/estimated/unobservable quota snapshots")
    sub = parser.add_subparsers(dest="cmd")

    status = sub.add_parser("status", help="Show quota snapshots")
    status.add_argument("--json", action="store_true")
    status.add_argument("--model", action="append", default=[])

    record = sub.add_parser("record-call", help="Record a call result from JSON headers/usage")
    record.add_argument("--model", required=True)
    record.add_argument("--provider", default="")
    record.add_argument("--ok", action="store_true", default=False)
    record.add_argument("--headers-json", default="{}")
    record.add_argument("--usage-json", default="{}")
    record.add_argument("--error", default="")

    confidence_gate = sub.add_parser("confidence-gate", help="Fail-closed quota confidence readiness gate")
    confidence_gate.add_argument("--json", action="store_true")
    confidence_gate.add_argument("--gate", action="store_true", help="Exit non-zero when readiness is not PASS")
    confidence_gate.add_argument("--min-confidence", type=float, default=0.50)
    confidence_gate.add_argument("--model", action="append", default=[], help="Model to check; defaults to T3 certification set")

    probe = sub.add_parser("probe", help="Probe non-token balance endpoints where available")
    probe.add_argument("--deepseek", action="store_true")
    probe.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.cmd == "status":
        if args.model:
            snapshots = snapshot_models(args.model)
        else:
            snapshots = load_state()
        if args.json:
            print(json.dumps(snapshots, indent=2, ensure_ascii=False, sort_keys=True))
        else:
            print(render_table(snapshots))
    elif args.cmd == "record-call":
        try:
            headers = json.loads(args.headers_json)
            usage = json.loads(args.usage_json)
        except json.JSONDecodeError as e:
            print(f"invalid JSON: {e}", file=sys.stderr)
            sys.exit(2)
        snap = record_call(args.model, args.provider or None, ok=args.ok, headers=headers, usage=usage, error=args.error)
        print(json.dumps(snap, indent=2, ensure_ascii=False, sort_keys=True))
    elif args.cmd == "confidence-gate":
        report = assess_quota_confidence(args.model or DEFAULT_T3_MODELS, min_confidence=args.min_confidence)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
        else:
            print(render_table(report.get("snapshots", {})))
            print(f"quota_confidence_gate: {report['status']} failures={report['failure_count']} min_confidence={report['min_confidence']}")
        if args.gate and not report.get("ok"):
            sys.exit(2)

    elif args.cmd == "probe":
        snaps = {}
        if args.deepseek:
            snap = probe_deepseek_balance()
            if snap:
                record_snapshot(snap)
                snaps[quota_key(snap["provider"], snap["model"])] = snap
        if args.json:
            print(json.dumps(snaps, indent=2, ensure_ascii=False, sort_keys=True))
        else:
            print(render_table(snaps))
    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
