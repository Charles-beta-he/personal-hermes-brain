#!/usr/bin/env python3
"""Dashboard Frontend Hygiene Gate.

Enforces frontend/dashboard quality gates before any Hermes dashboard work
can be considered complete:

1. npm audit — moderate+ with fixAvailable must be resolved or explicitly accepted
2. Production build — must pass without errors
3. Bundle budget — main JS chunk must be under configured threshold
4. TypeScript — must compile without errors

Exit code 0 = all gates pass, 2 = gate failure, 1 = error.

Usage:
    # Run all gates on a frontend directory
    python3 dashboard_hygiene_gate.py --frontend /path/to/frontend/

    # Run with custom bundle budget (default 500kB gzip)
    python3 dashboard_hygiene_gate.py --frontend /path/to/frontend/ --budget-kb 600

    # Run on the hermes-hudui audit
    python3 dashboard_hygiene_gate.py --frontend /tmp/hermes-hudui-audit/frontend/

    # Skip specific gates
    python3 dashboard_hygiene_gate.py --frontend /path/ --skip-audit --skip-build
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

VERSION = 1
DEFAULT_BUDGET_KB = 500  # Vite default warning threshold


@dataclass
class GateResult:
    gate: str
    passed: bool
    detail: str
    severity: str = "info"  # critical / high / medium / info
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class HygieneReport:
    passed: bool
    gates: list[GateResult] = field(default_factory=list)
    frontend_path: str = ""
    budget_kb: int = DEFAULT_BUDGET_KB

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": VERSION,
            "passed": self.passed,
            "frontend_path": self.frontend_path,
            "budget_kb": self.budget_kb,
            "gate_count": len(self.gates),
            "passed_count": sum(1 for g in self.gates if g.passed),
            "failed_count": sum(1 for g in self.gates if not g.passed),
            "gates": [
                {
                    "gate": g.gate, "passed": g.passed, "detail": g.detail,
                    "severity": g.severity, "metrics": g.metrics,
                }
                for g in self.gates
            ],
        }


def _run(cmd: list[str], cwd: str, timeout: int = 120) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except OSError as e:
        return -1, "", str(e)


# ---------------------------------------------------------------------------
# Gate: npm audit
# ---------------------------------------------------------------------------

def gate_npm_audit(frontend: Path) -> GateResult:
    """Check npm audit for moderate+ vulnerabilities with fixAvailable."""
    code, stdout, stderr = _run(
        ["npm", "audit", "--json"], cwd=str(frontend), timeout=60,
    )

    if code == -1:
        return GateResult(
            gate="npm_audit", passed=False,
            detail=f"Could not run npm audit: {stderr}",
            severity="critical",
        )

    try:
        audit = json.loads(stdout) if stdout.strip() else {}
    except json.JSONDecodeError:
        return GateResult(
            gate="npm_audit", passed=code == 0,
            detail="npm audit completed (non-JSON output)" if code == 0 else f"npm audit failed: {stderr[:200]}",
            severity="medium" if code == 0 else "high",
        )

    # Parse vulnerabilities
    vulns = audit.get("vulnerabilities", {})
    moderate_plus = {}
    for name, info in vulns.items():
        severity = info.get("severity", "")
        fix_available = info.get("fixAvailable", False)
        if severity in ("moderate", "high", "critical") and fix_available:
            moderate_plus[name] = {
                "severity": severity,
                "fixAvailable": True,
                "via": [v if isinstance(v, str) else v.get("title", "?") for v in info.get("via", [])],
            }

    advisory_count = audit.get("metadata", {}).get("vulnerabilities", {})
    total_advisories = sum(v for v in advisory_count.values() if isinstance(v, int))

    if moderate_plus:
        names = ", ".join(sorted(moderate_plus.keys()))
        return GateResult(
            gate="npm_audit", passed=False,
            detail=f"{len(moderate_plus)} fixable moderate+ vulnerabilities: {names}",
            severity="high",
            metrics={
                "fixable_vulnerabilities": moderate_plus,
                "total_advisories": total_advisories,
            },
        )

    return GateResult(
        gate="npm_audit", passed=True,
        detail=f"No fixable moderate+ vulnerabilities (total advisories: {total_advisories})",
        severity="info",
        metrics={"total_advisories": total_advisories},
    )


# ---------------------------------------------------------------------------
# Gate: Production build
# ---------------------------------------------------------------------------

def gate_build(frontend: Path) -> GateResult:
    """Run npm run build and check for success."""
    # Clean first
    _run(["rm", "-rf", "dist"], cwd=str(frontend))

    code, stdout, stderr = _run(
        ["npm", "run", "build"], cwd=str(frontend), timeout=180,
    )

    combined = stdout + stderr

    if code != 0:
        # Extract error lines
        errors = [line for line in combined.splitlines() if "error" in line.lower() or "Error" in line]
        return GateResult(
            gate="build", passed=False,
            detail=f"Build failed (exit {code}): {'; '.join(errors[:3])}",
            severity="critical",
        )

    return GateResult(
        gate="build", passed=True,
        detail="Production build succeeded",
        severity="info",
    )


# ---------------------------------------------------------------------------
# Gate: Bundle budget
# ---------------------------------------------------------------------------

def gate_bundle_budget(frontend: Path, budget_kb: int) -> GateResult:
    """Check that the main JS chunk is under the budget threshold."""
    dist = frontend / "dist"
    if not dist.is_dir():
        return GateResult(
            gate="bundle_budget", passed=False,
            detail="dist/ directory not found; run build first",
            severity="high",
        )

    # Find JS chunks
    js_chunks = []
    for p in dist.rglob("*.js"):
        size_kb = p.stat().st_size / 1024
        js_chunks.append((p.name, size_kb))

    if not js_chunks:
        return GateResult(
            gate="bundle_budget", passed=True,
            detail="No JS chunks found in dist/",
            severity="info",
        )

    # Sort by size descending
    js_chunks.sort(key=lambda x: x[1], reverse=True)
    largest_name, largest_kb = js_chunks[0]

    # Estimate gzip size (typically 25-35% of original for JS)
    estimated_gzip_kb = largest_kb * 0.28

    passed = largest_kb <= budget_kb
    severity = "info" if passed else ("high" if largest_kb > budget_kb * 1.5 else "medium")

    detail = (
        f"Largest chunk: {largest_name} ({largest_kb:.0f} kB, ~{estimated_gzip_kb:.0f} kB gzip)"
        f" — {'within' if passed else 'EXCEEDS'} {budget_kb} kB budget"
    )

    return GateResult(
        gate="bundle_budget", passed=passed,
        detail=detail,
        severity=severity,
        metrics={
            "largest_chunk": largest_name,
            "size_kb": round(largest_kb, 1),
            "estimated_gzip_kb": round(estimated_gzip_kb, 1),
            "budget_kb": budget_kb,
            "all_chunks": [{"name": n, "size_kb": round(s, 1)} for n, s in js_chunks[:10]],
        },
    )


# ---------------------------------------------------------------------------
# Gate: TypeScript compilation
# ---------------------------------------------------------------------------

def gate_typescript(frontend: Path) -> GateResult:
    """Check TypeScript compilation (tsc --noEmit)."""
    # Check if tsconfig exists
    if not (frontend / "tsconfig.json").exists():
        return GateResult(
            gate="typescript", passed=True,
            detail="No tsconfig.json found; skipping TypeScript check",
            severity="info",
        )

    code, stdout, stderr = _run(
        ["npx", "tsc", "--noEmit"], cwd=str(frontend), timeout=60,
    )

    if code != 0:
        errors = [line for line in (stdout + stderr).splitlines() if "error" in line.lower()]
        return GateResult(
            gate="typescript", passed=False,
            detail=f"TypeScript errors: {'; '.join(errors[:5])}",
            severity="high",
            metrics={"error_count": len(errors)},
        )

    return GateResult(
        gate="typescript", passed=True,
        detail="TypeScript compilation passed",
        severity="info",
    )


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_hygiene_gates(
    frontend_path: str,
    budget_kb: int = DEFAULT_BUDGET_KB,
    skip_audit: bool = False,
    skip_build: bool = False,
    skip_ts: bool = False,
) -> HygieneReport:
    """Run all hygiene gates on a frontend directory."""
    frontend = Path(frontend_path).expanduser().resolve()
    report = HygieneReport(passed=True, frontend_path=str(frontend), budget_kb=budget_kb)

    if not frontend.is_dir():
        report.passed = False
        report.gates.append(GateResult(
            gate="directory", passed=False,
            detail=f"Frontend directory not found: {frontend}",
            severity="critical",
        ))
        return report

    # Check if package.json exists
    if not (frontend / "package.json").exists():
        report.passed = False
        report.gates.append(GateResult(
            gate="package_json", passed=False,
            detail="No package.json found in frontend directory",
            severity="critical",
        ))
        return report

    # npm audit
    if not skip_audit:
        report.gates.append(gate_npm_audit(frontend))

    # TypeScript
    if not skip_ts:
        report.gates.append(gate_typescript(frontend))

    # Build (needed for bundle budget, but only if not skipped)
    build_passed = True
    if not skip_build:
        build_result = gate_build(frontend)
        report.gates.append(build_result)
        build_passed = build_result.passed

    # Bundle budget (only if build succeeded)
    if build_passed:
        report.gates.append(gate_bundle_budget(frontend, budget_kb))

    # Overall pass: all gates must pass
    report.passed = all(g.passed for g in report.gates)
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dashboard Frontend Hygiene Gate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--frontend", required=True, help="Path to frontend directory")
    parser.add_argument("--budget-kb", type=int, default=DEFAULT_BUDGET_KB,
                        help=f"Bundle budget in kB (default: {DEFAULT_BUDGET_KB})")
    parser.add_argument("--skip-audit", action="store_true", help="Skip npm audit gate")
    parser.add_argument("--skip-build", action="store_true", help="Skip build gate")
    parser.add_argument("--skip-ts", action="store_true", help="Skip TypeScript gate")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    report = run_hygiene_gates(
        args.frontend,
        budget_kb=args.budget_kb,
        skip_audit=args.skip_audit,
        skip_build=args.skip_build,
        skip_ts=args.skip_ts,
    )

    if args.json or not sys.stdout.isatty():
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_report(report)

    return 0 if report.passed else 2


def _print_report(report: HygieneReport) -> None:
    status = "PASS" if report.passed else "FAIL"
    print(f"Dashboard Hygiene Report: {status}")
    print(f"  Frontend: {report.frontend_path}")
    print(f"  Budget: {report.budget_kb} kB")
    print(f"  Gates: {sum(1 for g in report.gates if g.passed)}/{len(report.gates)} passed")
    print()

    for g in report.gates:
        icon = "PASS" if g.passed else "FAIL"
        print(f"  [{icon}] {g.gate}")
        print(f"         {g.detail}")
        if g.metrics:
            for k, v in g.metrics.items():
                if k != "all_chunks":
                    print(f"         {k}: {v}")
        print()


if __name__ == "__main__":
    raise SystemExit(main())
