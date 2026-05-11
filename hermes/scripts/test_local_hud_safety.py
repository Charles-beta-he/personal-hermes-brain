#!/usr/bin/env python3
"""HUD/API Mutation Surface Safety Verifier.

Inventories and verifies safety properties of any Hermes HUD or API surface:
- Bind host must be loopback (127.0.0.1 / ::1) by default
- CORS must NOT be wildcard ("*") when host is non-loopback
- Mutation endpoints (cron, plugins, gateway, memory, profiles) must have
  explicit trust boundary documentation and authentication
- WebSocket endpoints must require authentication for non-loopback hosts

Exit code 0 = safe, 2 = safety violations found, 1 = error.

Usage:
    # Scan a running HUD server (default localhost:3001)
    python3 test_local_hud_safety.py --url http://127.0.0.1:3001

    # Scan a FastAPI source tree for safety issues
    python3 test_local_hud_safety.py --source /path/to/backend/

    # Scan the hermes-hudui audit directory
    python3 test_local_hud_safety.py --source /tmp/hermes-hudui-audit/backend/
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

VERSION = 1

# Known mutation endpoint patterns (method + path regex)
MUTATION_ENDPOINTS = [
    ("POST", r"/cron", "cron_create", "Creates cron jobs that shell out to hermes CLI"),
    ("POST", r"/cron/[^/]+/(pause|resume|run)", "cron_control", "Controls cron job lifecycle"),
    ("DELETE", r"/cron/[^/]+", "cron_delete", "Deletes cron jobs"),
    ("POST", r"/gateway/restart", "gateway_restart", "Restarts the gateway process"),
    ("POST", r"/hermes/update", "hermes_update", "Runs hermes self-update"),
    ("POST", r"/plugins/install", "plugin_install", "Installs plugins (arbitrary code)"),
    ("POST", r"/plugins/[^/]+/enable", "plugin_enable", "Enables plugins"),
    ("POST", r"/plugins/[^/]+/disable", "plugin_disable", "Disables plugins"),
    ("POST", r"/plugins/[^/]+/update", "plugin_update", "Updates plugins"),
    ("PUT", r"/memory", "memory_write", "Writes to Hermes memory store"),
    ("DELETE", r"/memory", "memory_delete", "Deletes memory entries"),
    ("PUT", r"/profiles", "profile_write", "Writes profile data"),
    ("POST", r"/chat", "chat_create", "Creates chat sessions"),
    ("DELETE", r"/chat/[^/]+", "chat_delete", "Deletes chat sessions"),
    ("POST", r"/replay/runs/[^/]+/publish", "replay_publish", "Publishes replay data"),
    ("DELETE", r"/replay/runs/[^/]+/publish", "replay_unpublish", "Unpublishes replay data"),
]

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


@dataclass
class SafetyFinding:
    severity: str  # critical / high / medium / info
    category: str
    detail: str
    location: str = ""
    recommendation: str = ""


@dataclass
class SafetyReport:
    passed: bool
    findings: list[SafetyFinding] = field(default_factory=list)
    mutation_endpoints_found: list[dict[str, str]] = field(default_factory=list)
    host: str = "127.0.0.1"
    cors_origins: list[str] = field(default_factory=list)
    has_auth: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": VERSION,
            "passed": self.passed,
            "host": self.host,
            "cors_origins": self.cors_origins,
            "has_auth": self.has_auth,
            "mutation_endpoint_count": len(self.mutation_endpoints_found),
            "finding_count": len(self.findings),
            "findings": [
                {"severity": f.severity, "category": f.category, "detail": f.detail,
                 "location": f.location, "recommendation": f.recommendation}
                for f in self.findings
            ],
            "mutation_endpoints": self.mutation_endpoints_found,
        }


# ---------------------------------------------------------------------------
# Source code scanning
# ---------------------------------------------------------------------------

def scan_source_tree(source_dir: str) -> SafetyReport:
    """Scan a Python/FastAPI source tree for HUD safety issues."""
    source = Path(source_dir).expanduser().resolve()
    report = SafetyReport(passed=True)

    if not source.exists():
        report.passed = False
        report.findings.append(SafetyFinding(
            severity="critical", category="missing_source",
            detail=f"Source directory not found: {source}",
        ))
        return report

    # Scan main.py for CORS and host config
    main_py = source / "main.py"
    if main_py.exists():
        _scan_main_py(main_py, report)

    # Scan api/ directory for mutation endpoints
    api_dir = source / "api"
    if api_dir.is_dir():
        for py_file in sorted(api_dir.glob("*.py")):
            _scan_api_module(py_file, report)

    # Check for auth middleware
    _check_auth_middleware(source, report)

    # Evaluate overall safety
    critical = sum(1 for f in report.findings if f.severity == "critical")
    high = sum(1 for f in report.findings if f.severity == "high")
    report.passed = critical == 0 and high == 0

    return report


def _scan_main_py(path: Path, report: SafetyReport) -> None:
    """Scan main.py for CORS, host, and WebSocket configuration."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return

    # Check CORS configuration
    cors_match = re.search(
        r"CORSMiddleware.*?allow_origins\s*=\s*\[(.*?)\]",
        content, re.DOTALL,
    )
    if cors_match:
        origins_text = cors_match.group(1)
        origins = re.findall(r'"([^"]*)"', origins_text)
        report.cors_origins = origins
        if "*" in origins:
            report.findings.append(SafetyFinding(
                severity="critical",
                category="cors_wildcard",
                detail="CORS allow_origins=['*'] permits any origin to make cross-site requests",
                location=str(path),
                recommendation="Restrict CORS origins to specific trusted domains or localhost only",
            ))

    # Check default host binding
    host_match = re.search(r'--host.*?default[=:]\s*["\']([^"\']+)["\']', content)
    if host_match:
        host = host_match.group(1)
        report.host = host
        if host not in LOOPBACK_HOSTS and host != "0.0.0.0":
            report.findings.append(SafetyFinding(
                severity="high",
                category="non_loopback_default",
                detail=f"Default host is '{host}', not loopback",
                location=str(path),
                recommendation="Default to 127.0.0.1 for localhost-only binding",
            ))
        elif host == "0.0.0.0":
            report.findings.append(SafetyFinding(
                severity="high",
                category="bind_all_interfaces",
                detail="Default host 0.0.0.0 binds to all network interfaces",
                location=str(path),
                recommendation="Default to 127.0.0.1; require explicit --host 0.0.0.0 for network exposure",
            ))

    # Check WebSocket auth
    ws_match = re.search(r'@app\.websocket.*?\ndef.*?\(.*?\)', content, re.DOTALL)
    if ws_match:
        ws_block = content[ws_match.start():ws_match.start() + 500]
        if "auth" not in ws_block.lower() and "token" not in ws_block.lower():
            report.findings.append(SafetyFinding(
                severity="high",
                category="ws_no_auth",
                detail="WebSocket endpoint has no authentication check",
                location=str(path),
                recommendation="Add token-based or session-based auth for WebSocket connections",
            ))


def _scan_api_module(path: Path, report: SafetyReport) -> None:
    """Scan an API module for mutation endpoints without trust boundary docs."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return

    module_name = path.stem

    for method, pattern, endpoint_id, description in MUTATION_ENDPOINTS:
        # Look for route decorators matching this endpoint
        decorator_pattern = rf'@router\.{method.lower()}\s*\(\s*["\']({pattern})["\']'
        for match in re.finditer(decorator_pattern, content):
            route_path = match.group(1)
            # Check if there's a trust boundary comment nearby
            line_num = content[:match.start()].count("\n") + 1
            context_start = max(0, match.start() - 200)
            context = content[context_start:match.start()]

            has_trust_doc = any(term in context.lower() for term in [
                "trust boundary", "localhost", "loopback", "auth", "security",
                "rce", "mutation", "side-effect",
            ])

            report.mutation_endpoints_found.append({
                "method": method,
                "path": route_path,
                "module": module_name,
                "id": endpoint_id,
                "line": str(line_num),
                "has_trust_doc": str(has_trust_doc),
            })

            if not has_trust_doc:
                report.findings.append(SafetyFinding(
                    severity="high" if endpoint_id in {
                        "cron_create", "hermes_update", "plugin_install", "gateway_restart"
                    } else "medium",
                    category="mutation_no_trust_boundary",
                    detail=f"Mutation endpoint {method} {route_path} ({description}) lacks trust boundary documentation",
                    location=f"{path}:{line_num}",
                    recommendation="Add explicit trust boundary comment documenting RCE-equivalent threat model",
                ))


def _check_auth_middleware(source: Path, report: SafetyReport) -> None:
    """Check if auth middleware exists in the application."""
    # Check for auth-related imports and middleware
    auth_patterns = [
        r"Depends\(.*auth",
        r"middleware.*auth",
        r"HTTPBearer",
        r"HTTPBasic",
        r"APIKey",
        r"auth_middleware",
        r"verify_token",
        r"check_auth",
    ]
    found_auth = False
    for py_file in source.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern in auth_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                found_auth = True
                break
        if found_auth:
            break

    report.has_auth = found_auth
    if not found_auth:
        report.findings.append(SafetyFinding(
            severity="critical",
            category="no_auth_middleware",
            detail="No authentication middleware or dependency injection found in source tree",
            location=str(source),
            recommendation="Add authentication middleware; at minimum require local trust token for mutation endpoints",
        ))


# ---------------------------------------------------------------------------
# Runtime probing (optional — tests against a running server)
# ---------------------------------------------------------------------------

def probe_server(url: str) -> SafetyReport:
    """Probe a running HUD server for safety issues."""
    report = SafetyReport(passed=True, host=url)

    try:
        import urllib.request
        import urllib.error
    except ImportError:
        report.passed = False
        report.findings.append(SafetyFinding(
            severity="critical", category="import_error",
            detail="urllib not available",
        ))
        return report

    # Check if server is reachable
    try:
        req = urllib.request.Request(f"{url}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                pass  # reachable
    except urllib.error.URLError as e:
        report.passed = False
        report.findings.append(SafetyFinding(
            severity="info", category="server_unreachable",
            detail=f"Server not reachable at {url}: {e}",
            recommendation="Start the server first, or use --source to scan source code",
        ))
        return report
    except Exception as e:
        report.findings.append(SafetyFinding(
            severity="info", category="server_error",
            detail=f"Error reaching {url}: {e}",
        ))
        return report

    # Test CORS preflight on mutation endpoints
    for method, path_pattern, endpoint_id, desc in MUTATION_ENDPOINTS[:6]:
        # Extract a concrete path from the regex
        concrete_path = re.sub(r"\[.*?\]", "test", path_pattern).replace("\\", "").replace("?:", "").replace("(", "").replace(")", "").replace("+", "").replace("?", "")
        if "|" in concrete_path:
            concrete_path = concrete_path.split("|")[0]
        test_url = f"{url}{concrete_path}"

        # Send OPTIONS to check CORS
        try:
            req = urllib.request.Request(test_url, method="OPTIONS")
            req.add_header("Origin", "https://evil.example.com")
            with urllib.request.urlopen(req, timeout=3) as resp:
                acao = resp.headers.get("Access-Control-Allow-Origin", "")
                if acao == "*":
                    report.findings.append(SafetyFinding(
                        severity="critical",
                        category="cors_reflects_origin",
                        detail=f"CORS reflects wildcard for {method} {concrete_path}",
                        location=test_url,
                        recommendation="Reject non-whitelisted origins for mutation endpoints",
                    ))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            pass  # Expected for most endpoints

    report.passed = not any(f.severity in ("critical", "high") for f in report.findings)
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="HUD/API Mutation Surface Safety Verifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source", help="Path to backend source directory to scan")
    group.add_argument("--url", help="URL of running HUD server to probe")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of human-readable")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.source:
        report = scan_source_tree(args.source)
    else:
        report = probe_server(args.url)

    if args.json or not sys.stdout.isatty():
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_report(report)

    return 0 if report.passed else 2


def _print_report(report: SafetyReport) -> None:
    status = "PASS" if report.passed else "FAIL"
    print(f"Safety Report: {status}")
    print(f"  Host: {report.host}")
    print(f"  CORS origins: {report.cors_origins or '(none detected)'}")
    print(f"  Auth middleware: {'yes' if report.has_auth else 'NO'}")
    print(f"  Mutation endpoints found: {len(report.mutation_endpoints_found)}")
    print(f"  Findings: {len(report.findings)}")
    print()

    if report.findings:
        for f in report.findings:
            icon = {"critical": "!!!", "high": "!! ", "medium": "!  ", "info": "   "}.get(f.severity, "   ")
            print(f"  [{icon}] {f.severity.upper()}: {f.category}")
            print(f"         {f.detail}")
            if f.location:
                print(f"         Location: {f.location}")
            if f.recommendation:
                print(f"         Fix: {f.recommendation}")
            print()


if __name__ == "__main__":
    raise SystemExit(main())
