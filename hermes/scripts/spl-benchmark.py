#!/usr/bin/env python3
"""
spl-benchmark.py — SPL实战验证: Measure actual token savings with real API calls.

Sends both Natural Language and SPL-encoded versions of the same prompts
to DeepSeek, compares character counts, estimated tokens, latency, and
response quality.

Usage:
    python3 spl-benchmark.py              # Run full benchmark
    python3 spl-benchmark.py --dry-run    # Show SPL vs NL without API calls
    python3 spl-benchmark.py --json       # Output JSON results only
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ── Path setup ──
HERMES_HOME = os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes"))
SCRIPTS_DIR = os.path.join(HERMES_HOME, "scripts")
AGENT_DIR = os.path.join(HERMES_HOME, "hermes-agent")
RESULTS_PATH = os.path.join(SCRIPTS_DIR, "spl-benchmark-results.json")

# ── SPL import ──
sys.path.insert(0, AGENT_DIR)
from agent.spl import (
    SPLEncoder,
    SPLDecoder,
    SPLTier,
    estimate_tokens,
    reset_default_cache,
)

# ── DeepSeek API config ──
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

def _load_api_key():
    """Load API key from .env if not in environment."""
    global DEEPSEEK_API_KEY
    if DEEPSEEK_API_KEY:
        return
    env_path = os.path.join(HERMES_HOME, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY="):
                    DEEPSEEK_API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return

_load_api_key()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST PROMPTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Mock data for realistic prompts
MOCK_STATE = {
    "task": "Fix authentication module failing on OAuth refresh",
    "files": ["src/auth/oauth.py", "src/auth/refresh.py", "config/auth.yaml"],
    "error": "test_auth_refresh fails with 401 after token expiry",
    "status": "debugging",
    "recent_changes": ["migrated to v2 OAuth endpoints", "added retry logic"],
    "environment": "production",
    "priority": "high",
}

MOCK_DIFF = '''--- a/src/auth/oauth.py
+++ b/src/auth/oauth.py
@@ -45,7 +45,8 @@ class OAuthHandler:
     def refresh_token(self, token: str) -> str:
-        response = self.client.post("/oauth/refresh", json={"token": token})
-        if response.status_code == 401:
-            raise AuthError("Token expired")
+        for attempt in range(3):
+            response = self.client.post("/oauth/refresh", json={"token": token})
+            if response.status_code == 200:
+                return response.json()["access_token"]
+            time.sleep(2 ** attempt)
+        raise AuthError("Token refresh failed after 3 attempts")
'''


def get_test_prompts() -> List[Dict[str, Any]]:
    """Define the 3 test prompt pairs (NL + SPL)."""
    prompts = []

    # ── Prompt A: Planner ──
    nl_planner = SPLEncoder.fallback_to_natural_language(
        "planner",
        state=MOCK_STATE,
        model="deepseek-chat",
        state_hash="mock123",
        tier="T2",
    )
    spl_planner = SPLEncoder.encode_planner_call(
        state=MOCK_STATE,
        model="deepseek-chat",
        tier=SPLTier.T2,
    )
    prompts.append({
        "name": "planner",
        "description": "Analyze system and produce structured improvement plan",
        "nl": nl_planner,
        "spl": spl_planner,
    })

    # ── Prompt B: Validator ──
    nl_validator = SPLEncoder.fallback_to_natural_language(
        "vote",
        task=(
            "Validate these 3 architectural decisions:\n"
            "1. Is Singleton pattern right for DBConnection? Concurrency risk?\n"
            "2. Is circuit breaker complete? Missing half-open state?\n"
            "3. Should config persist to disk? Lost on restart?\n\n"
            "For each: pass/fail/partial with brief reasoning."
        ),
    )
    spl_validator = SPLEncoder.encode_vote_call(
        task=(
            "Validate these 3 architectural decisions:\n"
            "1. Is Singleton pattern right for DBConnection? Concurrency risk?\n"
            "2. Is circuit breaker complete? Missing half-open state?\n"
            "3. Should config persist to disk? Lost on restart?\n\n"
            "For each: pass/fail/partial with brief reasoning."
        ),
        model="deepseek-chat",
    )
    prompts.append({
        "name": "validator",
        "description": "Validate 3 architectural decisions",
        "nl": nl_validator,
        "spl": spl_validator,
    })

    # ── Prompt C: Voter ──
    nl_voter = SPLEncoder.fallback_to_natural_language(
        "vote",
        task=(
            "Vote on whether this code change is correct:\n\n"
            f"DIFF:\n{MOCK_DIFF}\n\n"
            "The change replaces a single-shot token refresh with a retry loop "
            "(3 attempts, exponential backoff). Is this correct? "
            "Consider: error handling, thread safety, timeout implications."
        ),
    )
    spl_voter = SPLEncoder.encode_vote_call(
        task=(
            "Vote on whether this code change is correct:\n\n"
            f"DIFF:\n{MOCK_DIFF}\n\n"
            "The change replaces a single-shot token refresh with a retry loop "
            "(3 attempts, exponential backoff). Is this correct? "
            "Consider: error handling, thread safety, timeout implications."
        ),
        model="deepseek-chat",
    )
    prompts.append({
        "name": "voter",
        "description": "Vote on code change correctness",
        "nl": nl_voter,
        "spl": spl_voter,
    })

    return prompts


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEEPSEEK API CALL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def call_deepseek(prompt: str, timeout: int = 60) -> Dict[str, Any]:
    """Send a prompt to DeepSeek via urllib (direct, no hermes overhead).

    Returns:
        {
            "ok": bool,
            "response": str,
            "response_chars": int,
            "latency_ms": int,
            "error": str | None,
            "usage": dict | None,  # if API returns usage data
        }
    """
    if not DEEPSEEK_API_KEY:
        return {
            "ok": False, "response": "", "response_chars": 0,
            "latency_ms": 0, "error": "DEEPSEEK_API_KEY not set", "usage": None,
        }

    url = f"{DEEPSEEK_BASE_URL}/v1/chat/completions"
    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful code analysis assistant. Be concise."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1024,
        "temperature": 0.3,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        latency_ms = int((time.time() - start) * 1000)

        content = ""
        usage = body.get("usage")
        if body.get("choices"):
            content = body["choices"][0].get("message", {}).get("content", "")

        return {
            "ok": True,
            "response": content[:500],  # truncate for storage
            "response_chars": len(content),
            "latency_ms": latency_ms,
            "error": None,
            "usage": usage,
        }
    except urllib.error.HTTPError as e:
        latency_ms = int((time.time() - start) * 1000)
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")[:300]
        except Exception:
            pass
        return {
            "ok": False, "response": "", "response_chars": 0,
            "latency_ms": latency_ms,
            "error": f"HTTP {e.code}: {err_body}",
            "usage": None,
        }
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return {
            "ok": False, "response": "", "response_chars": 0,
            "latency_ms": latency_ms,
            "error": str(e)[:200],
            "usage": None,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BENCHMARK RUNNER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_benchmark(dry_run: bool = False) -> Dict[str, Any]:
    """Run the full SPL benchmark.

    Returns a results dict with per-prompt comparisons.
    """
    reset_default_cache()
    prompts = get_test_prompts()
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": "deepseek-chat",
        "prompts": [],
        "summary": {},
    }

    total_nl_chars = 0
    total_spl_chars = 0
    total_nl_tokens = 0
    total_spl_tokens = 0

    for p in prompts:
        nl_chars = len(p["nl"])
        spl_chars = len(p["spl"])
        nl_tokens = estimate_tokens(p["nl"])
        spl_tokens = estimate_tokens(p["spl"])
        savings_pct = round((1 - spl_chars / max(1, nl_chars)) * 100, 1)

        total_nl_chars += nl_chars
        total_spl_chars += spl_chars
        total_nl_tokens += nl_tokens
        total_spl_tokens += spl_tokens

        entry = {
            "name": p["name"],
            "description": p["description"],
            "nl_chars": nl_chars,
            "spl_chars": spl_chars,
            "nl_tokens_est": nl_tokens,
            "spl_tokens_est": spl_tokens,
            "savings_pct": savings_pct,
            "nl_preview": p["nl"][:200],
            "spl_preview": p["spl"][:200],
            "api_calls": {},
        }

        if not dry_run:
            print(f"\n  [{p['name']}] Calling DeepSeek with NL prompt ({nl_chars} chars)...")
            nl_result = call_deepseek(p["nl"])
            entry["api_calls"]["nl"] = nl_result

            print(f"  [{p['name']}] Calling DeepSeek with SPL prompt ({spl_chars} chars)...")
            spl_result = call_deepseek(p["spl"])
            entry["api_calls"]["spl"] = spl_result

            # Check response quality
            nl_ok = nl_result["ok"] and nl_result["response_chars"] > 50
            spl_ok = spl_result["ok"] and spl_result["response_chars"] > 50
            entry["nl_valid_response"] = nl_ok
            entry["spl_valid_response"] = spl_ok

        results["prompts"].append(entry)

    overall_savings = round((1 - total_spl_chars / max(1, total_nl_chars)) * 100, 1)
    results["summary"] = {
        "total_nl_chars": total_nl_chars,
        "total_spl_chars": total_spl_chars,
        "total_nl_tokens_est": total_nl_tokens,
        "total_spl_tokens_est": total_spl_tokens,
        "overall_savings_pct": overall_savings,
    }

    return results


def print_table(results: Dict[str, Any]):
    """Print a human-readable comparison table."""
    print("\n" + "=" * 78)
    print("  SPL BENCHMARK RESULTS — Structured Protocol Language vs Natural Language")
    print("=" * 78)
    print(f"  Timestamp: {results['timestamp']}")
    print(f"  Model:     {results['model']}")
    print("-" * 78)

    # Header
    print(f"  {'Prompt':<12} {'NL chars':>9} {'SPL chars':>10} {'Savings':>8} "
          f"{'NL tok':>7} {'SPL tok':>8} {'NL OK':>6} {'SPL OK':>7}")
    print("-" * 78)

    for p in results["prompts"]:
        nl_ok = ""
        spl_ok = ""
        if "api_calls" in p and p["api_calls"]:
            nl_ok = "YES" if p.get("nl_valid_response") else "NO"
            spl_ok = "YES" if p.get("spl_valid_response") else "NO"
        else:
            nl_ok = "---"
            spl_ok = "---"

        print(f"  {p['name']:<12} {p['nl_chars']:>9,} {p['spl_chars']:>10,} "
              f"{p['savings_pct']:>7.1f}% "
              f"{p['nl_tokens_est']:>7,} {p['spl_tokens_est']:>8,} "
              f"{nl_ok:>6} {spl_ok:>7}")

    print("-" * 78)
    s = results["summary"]
    print(f"  {'TOTAL':<12} {s['total_nl_chars']:>9,} {s['total_spl_chars']:>10,} "
          f"{s['overall_savings_pct']:>7.1f}% "
          f"{s['total_nl_tokens_est']:>7,} {s['total_spl_tokens_est']:>8,}")
    print("=" * 78)

    # API call details
    if any(p.get("api_calls") for p in results["prompts"]):
        print("\n  API CALL DETAILS:")
        print("-" * 78)
        for p in results["prompts"]:
            calls = p.get("api_calls", {})
            if not calls:
                continue
            nl_call = calls.get("nl", {})
            spl_call = calls.get("spl", {})
            print(f"\n  [{p['name']}]")
            print(f"    NL:  latency={nl_call.get('latency_ms','?')}ms  "
                  f"resp_chars={nl_call.get('response_chars','?')}  "
                  f"ok={nl_call.get('ok','?')}  "
                  f"error={nl_call.get('error','none')}")
            print(f"    SPL: latency={spl_call.get('latency_ms','?')}ms  "
                  f"resp_chars={spl_call.get('response_chars','?')}  "
                  f"ok={spl_call.get('ok','?')}  "
                  f"error={spl_call.get('error','none')}")

            # Show usage if available
            for label, call in [("NL", nl_call), ("SPL", spl_call)]:
                usage = call.get("usage")
                if usage:
                    print(f"    {label} usage: prompt_tokens={usage.get('prompt_tokens','?')}  "
                          f"completion_tokens={usage.get('completion_tokens','?')}  "
                          f"total={usage.get('total_tokens','?')}")

    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SPL Benchmark: SPL vs Natural Language")
    parser.add_argument("--dry-run", action="store_true", help="Show comparisons without API calls")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    if not args.json:
        print("\n  SPL Benchmark — Structured Protocol Language 实战验证")
        print("  Testing token savings with real DeepSeek API calls...\n")

        if not DEEPSEEK_API_KEY:
            print("  WARNING: DEEPSEEK_API_KEY not set. Running in dry-run mode.")
            args.dry_run = True

    results = run_benchmark(dry_run=args.dry_run)

    # Save results
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print_table(results)
        print(f"  Results saved to: {RESULTS_PATH}")
        print()


if __name__ == "__main__":
    main()
