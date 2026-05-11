#!/usr/bin/env python3
"""
cross-check.py — Cross-check verification for model health monitoring.

Takes a JSON file of test cases, queries each provider, compares output
against expected answers using fuzzy matching, and records hallucinations
in the ModelHealthMonitor.

Usage:
    python3 cross-check.py test_cases.json
    python3 cross-check.py test_cases.json --threshold 0.7
    python3 cross-check.py test_cases.json --use-spl
    python3 cross-check.py test_cases.json --dry-run

Test case format (JSON array):
    [
        {
            "prompt": "What is 2+2?",
            "expected_answer": "4",
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514"
        },
        ...
    ]

Exit codes:
    0 — all checks passed
    1 — at least one hallucination detected
    2 — script error (bad input, missing deps, etc.)
"""

from __future__ import annotations

import argparse
import difflib
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Paths
HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
LOG_DIR = HERMES_HOME / "logs"
CROSS_CHECK_LOG = LOG_DIR / "cross-check.jsonl"
HERMES_AGENT_DIR = HERMES_HOME / "hermes-agent"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cross-check")

# SPL Integration (lazy import)

_spl_available = False
_SPLEncoder = None
_SPLTier = None


def _try_import_spl():
    """Attempt to import SPL encoder from the hermes-agent codebase."""
    global _spl_available, _SPLEncoder, _SPLTier
    try:
        agent_dir = str(HERMES_AGENT_DIR)
        if agent_dir not in sys.path:
            sys.path.insert(0, agent_dir)
        from agent.spl import SPLEncoder, SPLTier
        _SPLEncoder = SPLEncoder
        _SPLTier = SPLTier
        _spl_available = True
    except ImportError:
        _spl_available = False


def encode_prompt_spl(prompt: str, expected_answer: str) -> str:
    """Encode a cross-check prompt using SPL protocol.

    Uses the vote/verify pattern since we're asking a model to produce
    an answer that will be verified against expected.
    """
    if not _spl_available or _SPLEncoder is None:
        return prompt
    return _SPLEncoder.encode_vote_call(
        task=prompt,
        model="cross-check",
    )


# Fuzzy Matching


def normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, collapse whitespace."""
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    # Remove common markdown/formatting artifacts
    text = re.sub(r"[*_`#>]", "", text)
    return text


def extract_key_facts(text: str) -> set:
    """Extract key factual tokens from text (numbers, proper nouns, code)."""
    facts: set = set()
    # Numbers (including decimals)
    facts.update(re.findall(r"\b\d+\.?\d*\b", text))
    # Quoted strings
    facts.update(re.findall(r'"([^"]*)"', text))
    facts.update(re.findall(r"'([^']*)'", text))
    # Code-like tokens (snake_case, camelCase)
    facts.update(re.findall(r"\b[a-z_][a-z0-9_]*\b", text.lower()))
    return facts


def fuzzy_match(
    actual: str, expected: str, threshold: float = 0.6
) -> Tuple[bool, float]:
    """Compare actual output against expected answer with fuzzy matching.

    Returns (passed, similarity_score).

    Matching strategy (in order):
    1. Exact match (normalized) -> pass
    2. Expected is substring of actual -> pass
    3. Key fact overlap -> pass if >threshold of expected facts found
    4. SequenceMatcher ratio -> pass if >=threshold
    """
    actual_norm = normalize_text(actual)
    expected_norm = normalize_text(expected)

    # 1. Exact match
    if actual_norm == expected_norm:
        return True, 1.0

    # 2. Substring containment (expected found within actual)
    if expected_norm in actual_norm:
        return True, 0.95

    # 3. Key fact overlap
    expected_facts = extract_key_facts(expected)
    actual_facts = extract_key_facts(actual)
    if expected_facts:
        overlap = expected_facts & actual_facts
        fact_ratio = len(overlap) / len(expected_facts)
        if fact_ratio >= threshold:
            return True, fact_ratio

    # 4. Sequence similarity
    ratio = difflib.SequenceMatcher(None, actual_norm, expected_norm).ratio()
    return ratio >= threshold, ratio


# Provider Invocation


def query_provider(
    prompt: str,
    provider: str,
    model: str = "",
    use_spl: bool = False,
    timeout: int = 120,
) -> Tuple[str, float, bool]:
    """Query a provider via `hermes chat` CLI.

    Returns (output, latency_ms, success).
    """
    if use_spl:
        send_prompt = encode_prompt_spl(prompt, "")
    else:
        send_prompt = prompt

    cmd = ["hermes", "chat", "-q", "--provider", provider, "--quiet", send_prompt]
    if model:
        cmd.extend(["--model", model])

    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        if result.returncode != 0:
            stderr = result.stderr.strip()
            logger.warning(
                "Provider %s returned rc=%d: %s", provider, result.returncode, stderr[:200]
            )
            return stderr or "(no output)", elapsed_ms, False
        output = result.stdout.strip()
        return output, elapsed_ms, True
    except subprocess.TimeoutExpired:
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.warning("Provider %s timed out after %ds", provider, timeout)
        return "(timeout)", elapsed_ms, False
    except FileNotFoundError:
        logger.error("`hermes` CLI not found in PATH")
        return "(hermes not found)", 0.0, False
    except Exception as e:
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.error("Error querying %s: %s", provider, e)
        return f"(error: {e})", elapsed_ms, False


# Hallucination Recording


def record_hallucination(provider: str, model: str = ""):
    """Record a hallucination event in ModelHealthMonitor.

    Imports and calls the monitor's record_hallucination method.
    Falls back to local-only logging if import fails.
    """
    try:
        agent_dir = str(HERMES_AGENT_DIR)
        if agent_dir not in sys.path:
            sys.path.insert(0, agent_dir)
        from agent.model_health import get_monitor
        monitor = get_monitor()
        monitor.record_hallucination(provider, model)
        logger.info(
            "Recorded hallucination for %s/%s via ModelHealthMonitor", provider, model
        )
    except ImportError:
        logger.warning(
            "Could not import ModelHealthMonitor; logging hallucination locally only"
        )
    except Exception as e:
        logger.warning("Failed to record hallucination in monitor: %s", e)


# Logging


def log_result(entry: Dict[str, Any]):
    """Append a result entry to cross-check.jsonl."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CROSS_CHECK_LOG, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.warning("Failed to log result: %s", e)


# Main


def load_test_cases(path: str) -> List[Dict[str, Any]]:
    """Load test cases from a JSON file."""
    p = Path(path)
    if not p.exists():
        logger.error("Test case file not found: %s", path)
        sys.exit(2)

    with open(p) as f:
        data = json.load(f)

    if not isinstance(data, list):
        logger.error("Test case file must contain a JSON array")
        sys.exit(2)

    for i, tc in enumerate(data):
        if "prompt" not in tc:
            logger.error("Test case %d missing 'prompt' field", i)
            sys.exit(2)
        if "expected_answer" not in tc:
            logger.error("Test case %d missing 'expected_answer' field", i)
            sys.exit(2)
        if "provider" not in tc:
            logger.error("Test case %d missing 'provider' field", i)
            sys.exit(2)

    return data


def run_cross_check(
    test_cases: List[Dict[str, Any]],
    threshold: float = 0.6,
    use_spl: bool = False,
    dry_run: bool = False,
) -> Tuple[int, int, int]:
    """Run cross-check verification on all test cases.

    Returns (total, passed, hallucinations).
    """
    total = len(test_cases)
    passed = 0
    hallucinations = 0

    logger.info(
        "Running %d test cases (threshold=%.2f, spl=%s, dry_run=%s)",
        total,
        threshold,
        use_spl,
        dry_run,
    )

    for i, tc in enumerate(test_cases):
        prompt = tc["prompt"]
        expected = tc["expected_answer"]
        provider = tc["provider"]
        model = tc.get("model", "")

        logger.info(
            "[%d/%d] Provider=%s | Prompt: %s", i + 1, total, provider, prompt[:80]
        )

        if dry_run:
            logger.info("  DRY RUN - skipping provider call")
            passed += 1
            continue

        # Query the provider
        output, latency_ms, api_ok = query_provider(prompt, provider, model, use_spl)

        if not api_ok:
            # API failure is not a hallucination - it's a health issue
            logger.warning("  API call failed for %s: %s", provider, output[:100])
            log_result(
                {
                    "ts": time.time(),
                    "provider": provider,
                    "model": model,
                    "prompt": prompt[:200],
                    "expected": expected[:200],
                    "actual": output[:200],
                    "match": False,
                    "score": 0.0,
                    "api_ok": False,
                    "latency_ms": round(latency_ms, 1),
                    "hallucination": False,
                }
            )
            continue

        # Compare output
        is_match, score = fuzzy_match(output, expected, threshold)

        status = "PASS" if is_match else "FAIL"
        logger.info("  %s (score=%.2f) latency=%.0fms", status, score, latency_ms)
        if not is_match:
            logger.info("    Expected: %s", expected[:100])
            logger.info("    Actual:   %s", output[:100])

        # Log result
        entry = {
            "ts": time.time(),
            "provider": provider,
            "model": model,
            "prompt": prompt[:200],
            "expected": expected[:200],
            "actual": output[:200],
            "match": is_match,
            "score": round(score, 4),
            "api_ok": True,
            "latency_ms": round(latency_ms, 1),
            "hallucination": not is_match,
        }
        log_result(entry)

        if is_match:
            passed += 1
        else:
            hallucinations += 1
            record_hallucination(provider, model)

    return total, passed, hallucinations


def main():
    parser = argparse.ArgumentParser(
        description="Cross-check model outputs against expected answers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "test_file",
        help="JSON file with test cases (array of {prompt, expected_answer, provider})",
    )
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=0.6,
        help="Fuzzy match threshold (0.0-1.0, default: 0.6)",
    )
    parser.add_argument(
        "--use-spl",
        action="store_true",
        help="Encode prompts using SPL protocol (compact format)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load test cases but don't call providers",
    )
    args = parser.parse_args()

    # Try importing SPL if requested
    if args.use_spl:
        _try_import_spl()
        if _spl_available:
            logger.info("SPL encoding enabled")
        else:
            logger.warning("SPL not available; falling back to plain prompts")

    # Load and run
    test_cases = load_test_cases(args.test_file)
    total, passed, hallucinations = run_cross_check(
        test_cases,
        threshold=args.threshold,
        use_spl=args.use_spl,
        dry_run=args.dry_run,
    )

    # Summary
    print()
    print("=" * 60)
    print("  CROSS-CHECK RESULTS")
    print(
        f"  Total: {total}  |  Passed: {passed}  |  Hallucinations: {hallucinations}"
    )
    print(f"  Hallucination rate: {hallucinations / max(total, 1) * 100:.1f}%")
    print(f"  Log: {CROSS_CHECK_LOG}")
    print("=" * 60)

    if hallucinations > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
