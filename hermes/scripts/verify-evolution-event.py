#!/usr/bin/env python3
"""
verify-evolution-event.py — Hermes Private Evolution Compliance Checker

Verifies that a Hermes evolution event meets minimum compliance criteria
defined in ~/.hermes/notes/hermes-private-evolution-manifesto.md.

Usage:
  python3 verify-evolution-event.py <file/dir> [<file/dir>...] [--repo=<path>]

Exit code: 0 = compliant, 1 = non-compliant
"""
import json
import os
import subprocess
import sys
from pathlib import Path


HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))

MIN_VERIFICATIONS = {
    ".json": "python3 -m json.tool {path} >/dev/null 2>&1",
    ".py": "python3 -m py_compile {path}",
    ".md": None,
    "*": None,
}


def _find_repo_root(path):
    """Walk up from path to find git root."""
    p = Path(path).resolve()
    for parent in [p] + list(p.parents):
        if (parent / ".git").is_dir():
            return parent
    return None


def _check_git_commit(repo):
    """Check for local commits."""
    result = {}
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=repo,
        )
        result["head"] = head.stdout.strip() if head.returncode == 0 else "unknown"

        ab = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...origin/main"],
            capture_output=True, text=True, timeout=5, cwd=repo,
        )
        result["ahead_behind"] = ab.stdout.strip() if ab.returncode == 0 else "unknown"

        log = subprocess.run(
            ["git", "log", "--oneline", "-3"],
            capture_output=True, text=True, timeout=5, cwd=repo,
        )
        result["recent_commits"] = log.stdout.strip().split("\n") if log.returncode == 0 else []
    except Exception as e:
        result["error"] = str(e)
    return result


def _verify_file(path):
    """Verify a single file. Returns (passed, detail)."""
    p = Path(path)
    if not p.exists():
        return False, "file not found"

    st = p.stat()
    if st.st_size == 0:
        return False, "empty file"

    suffix = p.suffix.lower()
    cmd = MIN_VERIFICATIONS.get(suffix, MIN_VERIFICATIONS["*"])
    if cmd:
        full_cmd = cmd.format(path=p)
        try:
            r = subprocess.run(
                ["sh", "-c", full_cmd],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode != 0:
                return False, f"verifier failed: {r.stderr.strip()[:120]}"
        except Exception as e:
            return False, f"verifier error: {e}"
        return True, f"{st.st_size} bytes, {suffix} verified"

    if suffix == ".md":
        return True, f"{st.st_size} bytes, markdown"
    return True, f"{st.st_size} bytes"


def _has_verification_in_files(files):
    """Check if any markdown file contains verification commands."""
    markers = ["json.tool", "py_compile", "pytest", "HERMES_HOME=",
               "-m pytest", "## Verification", "verification"]
    for f in files:
        p = Path(f)
        if p.suffix == ".md" and p.exists():
            try:
                content = p.read_text()
                if any(m in content for m in markers):
                    return True
            except (UnicodeDecodeError, OSError):
                continue
    return False


def main():
    args = sys.argv[1:]
    if not args or "--help" in args or "-h" in args:
        print(__doc__.strip())
        sys.exit(0 if "-h" in args else 1)

    event_paths = []
    repo_base = None
    for arg in args:
        if arg.startswith("--repo="):
            repo_base = arg.split("=", 1)[1]
        else:
            event_paths.append(arg)

    if not event_paths:
        print("ERROR: No file paths provided")
        sys.exit(1)

    # Auto-detect repo
    if not repo_base:
        for p in event_paths:
            r = _find_repo_root(p)
            if r:
                repo_base = str(r)
                break

    # Collect all files
    all_files = []
    for item in event_paths:
        p = Path(item)
        if p.is_file():
            all_files.append(p)
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    all_files.append(f)

    if not all_files:
        print("ERROR: No files found")
        sys.exit(1)

    # Verify each file
    results = []
    all_ok = True
    for f in all_files:
        ok, detail = _verify_file(str(f))
        results.append((f, ok, detail))
        if not ok:
            all_ok = False

    # Git info
    git_info = {}
    if repo_base:
        git_info = _check_git_commit(repo_base)

    has_evolution_note = any("evolution" in str(f) for f in all_files)
    has_repo_artifact = bool(git_info.get("head") and git_info["head"] != "unknown")
    has_verification = _has_verification_in_files(all_files)

    # Summary
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    compliant = all_ok and (has_evolution_note or has_repo_artifact)

    status = "COMPLIANT" if compliant else "NON-COMPLIANT"
    print()
    print("=" * 60)
    print(f" Evolution Event Compliance: {status}")
    print("=" * 60)
    print()
    print(f"  Checks: {passed}/{total} passed")
    print(f"  Has evolution note: {'✅' if has_evolution_note else '❌'}")
    print(f"  Has repo artifact:  {'✅' if has_repo_artifact else '❌'}")
    print(f"  Has verification:   {'✅' if has_verification else '❌'}")

    if git_info:
        print()
        print(f"  Git HEAD: {git_info.get('head', 'N/A')}")
        print(f"  Ahead/Behind: {git_info.get('ahead_behind', 'N/A')}")
        if git_info.get("recent_commits"):
            print("  Recent commits:")
            for c in git_info["recent_commits"][:3]:
                print(f"    {c[:80]}")
        if "error" in git_info:
            print(f"  Git error: {git_info['error']}")

    print()
    for f, ok, detail in results:
        icon = "✅" if ok else "❌"
        short = str(f)[-80:]
        print(f"  {icon} {short}")
        if not ok:
            print(f"      {detail[:120]}")

    print()
    print("=" * 60)
    print(f"  Final: {status}")
    print("=" * 60)
    sys.exit(0 if compliant else 1)


if __name__ == "__main__":
    main()
