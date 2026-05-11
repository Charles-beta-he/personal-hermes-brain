#!/usr/bin/env python3
"""Real multi-model smoke calls for Hermes actual-usage and warm-up scoring.

This script intentionally writes only real call outcomes to route_outcomes.db
(is_synthetic=0). It can be used by cron wrappers for periodic smoke checks or
by router-readiness recovery to warm non-dominant models with bounded, auditable
calls.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

HOME = Path.home()
HERMES = HOME / ".hermes"
DB = Path(os.environ.get("HERMES_ROUTE_DB_PATH", str(HERMES / "route_outcomes.db"))).expanduser()
LOG = HERMES / "logs" / "multi-model-smoke.jsonl"
ENV_FILE = HERMES / ".env"
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
try:  # optional: smoke must still work if quota module is temporarily broken
    import model_quota  # type: ignore
except Exception:  # pragma: no cover - defensive runtime isolation
    model_quota = None  # type: ignore

MODELS: Dict[str, Dict[str, Any]] = {
    "gpt-5.5": {
        "provider": "openai-codex",
        "unobservable_on_success_no_headers": "oauth_subscription_no_quota_headers",
        "cmd": ["hermes", "chat", "-q", "{prompt}", "--provider", "openai-codex", "--model", "gpt-5.5", "--quiet", "--ignore-rules", "--max-turns", "1", "--source", "tool"],
        "in": 0.0,
        "out": 0.0,
    },
    "mimo-v2.5-pro": {
        "provider": "xiaomi",
        "direct": "openai_chat",
        "api_model": "mimo-v2.5-pro",
        "api_key_env": "XIAOMI_API_KEY",
        "base_url_env": "XIAOMI_BASE_URL",
        "base_url_default": "https://token-plan-cn.xiaomimimo.com/v1",
        "cmd": ["hermes", "chat", "-q", "{prompt}", "--provider", "xiaomi", "--model", "mimo-v2.5-pro", "--quiet", "--ignore-rules", "--max-turns", "1", "--source", "tool"],
        "in": 2.4,
        "out": 9.6,
    },
    "claude-opus-4-7": {
        "provider": "anthropic",
        "unobservable_on_success_no_headers": "external_cli_no_quota_headers",
        "cmd": ["claude", "-p", "{prompt}", "--model", "opus", "--max-turns", "1", "--allowedTools", ""],
        "in": 15.0,
        "out": 75.0,
    },
    "deepseek-v4-pro": {
        "provider": "deepseek",
        "direct": "deepseek",
        "api_model": "deepseek-chat",
        "in": 0.2,
        "out": 0.6,
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_env() -> dict:
    env = dict(os.environ)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / 4) + 1)


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    m = MODELS[model]
    return round((tokens_in * float(m.get("in", 0)) + tokens_out * float(m.get("out", 0))) / 1_000_000, 8)


def append_route(model: str, ok: bool, duration_s: float, tokens_in: int, tokens_out: int, cost: float, task_id: str, route: str, error: str = "") -> None:
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS route_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, skill TEXT NOT NULL,
            task_class TEXT NOT NULL DEFAULT '', route TEXT NOT NULL DEFAULT '', verdict TEXT NOT NULL DEFAULT 'unknown',
            duration_s REAL DEFAULT 0, tokens_in INTEGER DEFAULT 0, tokens_out INTEGER DEFAULT 0, task_id TEXT DEFAULT '',
            model_chain TEXT DEFAULT '', cost_usd REAL DEFAULT 0, error TEXT DEFAULT '', is_synthetic INTEGER DEFAULT 0,
            chain_id TEXT)"""
        )
        conn.execute(
            """INSERT INTO route_outcomes
            (ts, skill, task_class, route, verdict, duration_s, tokens_in, tokens_out, task_id, model_chain, cost_usd, error, is_synthetic, chain_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (
                utc_now(),
                "multi-model-smoke",
                "actual_usage",
                route,
                "pass" if ok else "fail",
                round(duration_s, 3),
                int(tokens_in),
                int(tokens_out),
                task_id,
                json.dumps([model]),
                float(cost),
                error[:500],
                "actual-usage-smoke",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def run_subprocess(model: str, prompt: str, timeout: int) -> Tuple[bool, str, float, str]:
    spec = MODELS[model]
    cmd = [prompt if x == "{prompt}" else x for x in spec["cmd"]]
    t0 = time.perf_counter()
    try:
        r = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        dt = time.perf_counter() - t0
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        return r.returncode == 0 and bool(out), out[:1000], dt, err[:1000]
    except Exception as e:
        return False, "", time.perf_counter() - t0, repr(e)


def run_deepseek(prompt: str, timeout: int, env: dict) -> Tuple[bool, str, float, str, Dict[str, str]]:
    key = env.get("DEEPSEEK_API_KEY")
    if not key:
        return False, "", 0.0, "DEEPSEEK_API_KEY missing", {}
    body = json.dumps({"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 16, "temperature": 0}).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            headers = dict(resp.headers.items())
            raw = resp.read().decode("utf-8", "replace")
        dt = time.perf_counter() - t0
        data = json.loads(raw)
        usage = data.get("usage", {}) or {}
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return True, json.dumps({"content": content, "usage": usage}, ensure_ascii=False), dt, "", headers
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        return False, "", time.perf_counter() - t0, f"HTTP {e.code}: {body}", dict(e.headers.items()) if e.headers else {}
    except Exception as e:
        return False, "", time.perf_counter() - t0, repr(e), {}


def run_openai_chat(model: str, prompt: str, timeout: int, env: dict) -> Tuple[bool, str, float, str, Dict[str, str]]:
    spec = MODELS[model]
    key = env.get(str(spec.get("api_key_env") or ""))
    base = (env.get(str(spec.get("base_url_env") or "")) or spec.get("base_url_default") or "").rstrip("/")
    api_model = str(spec.get("api_model") or model)
    if not key:
        return False, "", 0.0, f"{spec.get('api_key_env')} missing", {}
    if not base:
        return False, "", 0.0, f"{spec.get('base_url_env')} missing", {}
    body = json.dumps({"model": api_model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 16, "temperature": 0}).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            headers = dict(resp.headers.items())
            raw = resp.read().decode("utf-8", "replace")
        dt = time.perf_counter() - t0
        data = json.loads(raw)
        usage = data.get("usage", {}) or {}
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return True, json.dumps({"content": content, "usage": usage}, ensure_ascii=False), dt, "", headers
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        return False, "", time.perf_counter() - t0, f"HTTP {e.code}: {body}", dict(e.headers.items()) if e.headers else {}
    except Exception as e:
        return False, "", time.perf_counter() - t0, repr(e), {}


def maybe_probe_deepseek_balance(enabled: bool) -> Optional[dict]:
    if not enabled or model_quota is None:
        return None
    try:
        snap = model_quota.probe_deepseek_balance()
        if snap:
            model_quota.record_snapshot(snap)
        return snap
    except Exception as exc:  # pragma: no cover - defensive runtime isolation
        return {"status": "probe_error", "error": repr(exc)[:300]}


def has_quota_headers(headers: Dict[str, str]) -> bool:
    if not headers:
        return False
    keys = {str(k).lower() for k in headers}
    quota_markers = (
        "x-ratelimit-remaining",
        "x-ratelimit-reset",
        "anthropic-ratelimit",
        "ratelimit-remaining",
        "ratelimit-reset",
        "retry-after",
    )
    return any(any(marker in key for marker in quota_markers) for key in keys)


def route_for(template: str, model: str, run_id: str, iteration: int) -> str:
    try:
        return template.format(model=model, run_id=run_id, iteration=iteration)
    except Exception:
        return template


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run real multi-model smoke/warm-up calls and record route evidence")
    ap.add_argument("--model", action="append", choices=sorted(MODELS))
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--skip-claude", action="store_true")
    ap.add_argument("--repeat", type=int, default=1, help="Repeat each selected model N times")
    ap.add_argument("--route", default="probe:smoke", help="Route template; supports {model}, {run_id}, {iteration}")
    ap.add_argument("--probe-deepseek-balance", action="store_true", help="Refresh DeepSeek exact billing balance before calls")
    args = ap.parse_args(argv)

    env = load_env()
    models = args.model or list(MODELS)
    if args.skip_claude:
        models = [m for m in models if not m.startswith("claude-")]
    repeat = max(1, int(args.repeat or 1))
    run_id = str(uuid.uuid4())[:8]
    quota_probe = maybe_probe_deepseek_balance(args.probe_deepseek_balance)
    if quota_probe:
        print(json.dumps({"event": "quota_probe", "provider": "deepseek", "snapshot": quota_probe}, ensure_ascii=False))

    results = []
    for iteration in range(1, repeat + 1):
        for model in models:
            prompt = f"Hermes actual-usage smoke {run_id} {iteration} {model}: reply exactly ACK."
            spec = MODELS[model]
            headers: Dict[str, str] = {}
            usage: Dict[str, Any] = {}
            if spec.get("direct") == "deepseek":
                ok, out, dt, err, headers = run_deepseek(prompt, args.timeout, env)
                if out:
                    try:
                        usage = json.loads(out).get("usage", {}) or {}
                    except Exception:
                        usage = {}
                tin = int(usage.get("prompt_tokens") or estimate_tokens(prompt))
                tout = int(usage.get("completion_tokens") or estimate_tokens(out or "ACK"))
            elif spec.get("direct") == "openai_chat":
                ok, out, dt, err, headers = run_openai_chat(model, prompt, args.timeout, env)
                if out:
                    try:
                        usage = json.loads(out).get("usage", {}) or {}
                    except Exception:
                        usage = {}
                tin = int(usage.get("prompt_tokens") or estimate_tokens(prompt))
                tout = int(usage.get("completion_tokens") or estimate_tokens(out or "ACK"))
            else:
                ok, out, dt, err = run_subprocess(model, prompt, args.timeout)
                tin = estimate_tokens(prompt)
                tout = estimate_tokens(out or "ACK")
            cost = estimate_cost(model, tin, tout)
            if ok and cost == 0:
                cost = 0.00000001
            route = route_for(args.route, model, run_id, iteration)
            task_id = f"smoke-{run_id}-{iteration}-{model}"
            append_route(model, ok, dt, tin, tout, cost, task_id, route=route, error=err)
            # Preserve quota observability without pretending empty subprocess
            # headers are exact budget evidence. DeepSeek exact balance is handled
            # by --probe-deepseek-balance; response headers are recorded only when
            # the provider exposes them.
            if model_quota is not None:
                try:
                    if has_quota_headers(headers):
                        model_quota.record_call(model=model, provider=spec["provider"], ok=ok, headers=headers, usage=usage, error=err)
                    elif ok and spec.get("direct") == "openai_chat":
                        snap = model_quota.snapshot_unobservable_success(
                            model=model,
                            provider=spec["provider"],
                            source="direct_api_no_quota_headers",
                            quota_type="provider_api_no_quota_headers",
                            header_names=list(headers.keys()),
                            usage=usage,
                            evidence_note="direct API success exposed no quota or rate-limit headers",
                            confidence=0.35,
                        )
                        model_quota.record_snapshot(snap)
                    elif ok and spec.get("unobservable_on_success_no_headers"):
                        snap = model_quota.snapshot_unobservable_success(
                            model=model,
                            provider=spec["provider"],
                            source="subprocess_success_no_quota_headers",
                            quota_type=str(spec.get("unobservable_on_success_no_headers")),
                            header_names=[],
                            usage=usage,
                            evidence_note="external CLI/OAuth route succeeded but exposes no response headers to Hermes",
                            confidence=0.3,
                        )
                        model_quota.record_snapshot(snap)
                except Exception:
                    pass
            rec = {
                "ts": utc_now(),
                "run_id": run_id,
                "iteration": iteration,
                "model": model,
                "provider": spec["provider"],
                "ok": ok,
                "duration_s": round(dt, 3),
                "tokens_in": tin,
                "tokens_out": tout,
                "cost_usd": cost,
                "route": route,
                "task_id": task_id,
                "error": err[:500],
                "output_preview": out[:200],
            }
            append_jsonl(LOG, rec)
            results.append(rec)
            print(json.dumps(rec, ensure_ascii=False))
    ok_all = all(r["ok"] for r in results)
    print(json.dumps({"status": "pass" if ok_all else "partial_fail", "models": len(results), "passed": sum(1 for r in results if r["ok"]), "run_id": run_id}, ensure_ascii=False))
    return 0 if ok_all else 2


if __name__ == "__main__":
    raise SystemExit(main())
