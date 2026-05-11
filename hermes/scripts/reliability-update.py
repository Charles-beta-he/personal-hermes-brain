#!/usr/bin/env python3
"""
reliability-update.py — Compute rolling hallucination rates and update
provider reliability scores in ModelHealthMonitor.

Reads cross-check.jsonl history, computes rolling hallucination rate
per provider (last N checks), and calls update_reliability_from_data()
on the health monitor.

Usage:
    python3 reliability-update.py
    python3 reliability-update.py --window 50
    python3 reliability-update.py --dry-run
    python3 reliability-update.py --json   (machine-readable output)

Output: Summary table of provider reliability stats.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
logger = logging.getLogger("reliability-update")


def load_cross_check_history() -> List[Dict[str, Any]]:
    """Load all entries from cross-check.jsonl."""
    entries: List[Dict[str, Any]] = []
    if not CROSS_CHECK_LOG.exists():
        logger.info("No cross-check log found at %s", CROSS_CHECK_LOG)
        return entries

    with open(CROSS_CHECK_LOG) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed line %d in cross-check.jsonl", line_num)

    logger.info("Loaded %d entries from %s", len(entries), CROSS_CHECK_LOG)
    return entries


def compute_rolling_rates(
    entries: List[Dict[str, Any]], window: int = 50
) -> Dict[str, Dict[str, Any]]:
    """Compute rolling hallucination rate per provider from last N checks.

    Returns dict: provider -> {
        "total_checks": int,
        "hallucinations": int,
        "rate": float,
        "avg_score": float,
        "avg_latency_ms": float,
        "last_check_ts": float,
        "api_failures": int,
    }
    """
    # Group by provider
    by_provider: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        provider = entry.get("provider", "unknown")
        by_provider[provider].append(entry)

    results: Dict[str, Dict[str, Any]] = {}

    for provider, provider_entries in by_provider.items():
        # Take last N entries (rolling window)
        recent = provider_entries[-window:]

        total = len(recent)
        hallucinations = sum(1 for e in recent if e.get("hallucination", False))
        api_failures = sum(1 for e in recent if not e.get("api_ok", True))
        valid_checks = sum(1 for e in recent if e.get("api_ok", True))

        # Average match score (only from valid API calls)
        scores = [e.get("score", 0.0) for e in recent if e.get("api_ok", True)]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Average latency
        latencies = [
            e.get("latency_ms", 0.0) for e in recent if e.get("api_ok", True)
        ]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        # Hallucination rate (only counting valid API responses)
        rate = hallucinations / max(valid_checks, 1)

        # Last check timestamp
        last_ts = max((e.get("ts", 0) for e in recent), default=0)

        results[provider] = {
            "total_checks": total,
            "hallucinations": hallucinations,
            "api_failures": api_failures,
            "valid_checks": valid_checks,
            "rate": round(rate, 4),
            "avg_score": round(avg_score, 4),
            "avg_latency_ms": round(avg_latency, 1),
            "last_check_ts": last_ts,
        }

    return results


def update_model_health(
    rates: Dict[str, Dict[str, Any]], dry_run: bool = False
) -> bool:
    """Update ModelHealthMonitor with computed hallucination rates.

    Returns True if update succeeded.
    """
    try:
        agent_dir = str(HERMES_AGENT_DIR)
        if agent_dir not in sys.path:
            sys.path.insert(0, agent_dir)
        from agent.model_health import get_monitor
        monitor = get_monitor()

        for provider, stats in rates.items():
            hallucination_rate = stats["rate"]
            if dry_run:
                logger.info(
                    "DRY RUN: Would update %s with hallucination_rate=%.4f",
                    provider,
                    hallucination_rate,
                )
            else:
                monitor.update_reliability_from_data(provider, hallucination_rate)
                logger.info(
                    "Updated %s: hallucination_rate=%.4f (from %d checks)",
                    provider,
                    hallucination_rate,
                    stats["valid_checks"],
                )
        return True
    except ImportError:
        logger.warning("Could not import ModelHealthMonitor")
        return False
    except AttributeError:
        logger.warning(
            "ModelHealthMonitor missing update_reliability_from_data() method. "
            "Ensure model_health.py has been updated."
        )
        return False
    except Exception as e:
        logger.warning("Failed to update model health: %s", e)
        return False


def print_summary_table(
    rates: Dict[str, Dict[str, Any]], as_json: bool = False
):
    """Print a formatted summary table or JSON."""
    if as_json:
        print(json.dumps(rates, indent=2))
        return

    if not rates:
        print("\n  No cross-check data found. Run cross-check.py first.\n")
        return

    # Sort by hallucination rate (worst first)
    sorted_providers = sorted(rates.items(), key=lambda x: x[1]["rate"], reverse=True)

    print()
    print("=" * 78)
    print("  PROVIDER RELIABILITY SUMMARY (rolling window)")
    print("=" * 78)
    print(
        f"  {'Provider':<20} {'Checks':>7} {'Halluc':>7} {'Rate':>8} "
        f"{'AvgScr':>8} {'Latency':>9} {'API Err':>8}"
    )
    print("-" * 78)

    for provider, stats in sorted_providers:
        rate_pct = f"{stats['rate'] * 100:.1f}%"
        latency = f"{stats['avg_latency_ms']:.0f}ms"
        print(
            f"  {provider:<20} {stats['valid_checks']:>7} "
            f"{stats['hallucinations']:>7} {rate_pct:>8} "
            f"{stats['avg_score']:>8.3f} {latency:>9} "
            f"{stats['api_failures']:>8}"
        )

    print("-" * 78)

    # Show last check time
    for provider, stats in sorted_providers:
        if stats["last_check_ts"] > 0:
            dt = datetime.fromtimestamp(stats["last_check_ts"], tz=timezone.utc)
            print(f"  {provider:<20} last check: {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    print("=" * 78)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Compute rolling hallucination rates and update provider reliability.",
    )
    parser.add_argument(
        "--window",
        "-w",
        type=int,
        default=50,
        help="Rolling window size (default: 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute rates but don't update model health",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of table",
    )
    args = parser.parse_args()

    # Load history
    entries = load_cross_check_history()
    if not entries:
        print("\n  No cross-check data found.")
        print(f"  Expected log file: {CROSS_CHECK_LOG}")
        print("  Run cross-check.py first to generate data.\n")
        sys.exit(0)

    # Compute rolling rates
    rates = compute_rolling_rates(entries, window=args.window)

    # Print summary
    print_summary_table(rates, as_json=args.json)

    # Update model health
    if rates:
        success = update_model_health(rates, dry_run=args.dry_run)
        if success:
            if args.dry_run:
                logger.info("Dry run complete. No changes made.")
            else:
                logger.info("Provider reliability scores updated successfully.")
        else:
            logger.warning(
                "Could not update model health. "
                "Ensure model_health.py has update_reliability_from_data()."
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
