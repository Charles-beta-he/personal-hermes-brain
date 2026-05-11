#!/usr/bin/env python3
"""evidence_manifest.py — Sidecar evidence manifest for mission artifacts.

Creates and verifies .evidence.json sidecar files alongside mission notes.
Each evidence entry contains: path, sha256, type, created timestamp.
Enables tamper detection and reproducible evidence bundles.

Usage:
    python3 evidence_manifest.py create <mission_note.md> [evidence_paths...]
    python3 evidence_manifest.py verify <mission_note.md>
    python3 evidence_manifest.py hash <file_path>
    python3 evidence_manifest.py list <mission_note.md>

Sidecar format: <mission_note>.evidence.json (same directory)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=8))


def sha256_file(path: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """Compute SHA-256 hash of text content."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def now_ts() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sidecar_path(mission_note: str) -> Path:
    """Return the sidecar .evidence.json path for a mission note."""
    p = Path(mission_note)
    return p.parent / f"{p.stem}.evidence.json"


def create_manifest(mission_note: str, evidence_paths: list[str]) -> dict:
    """Create or update sidecar evidence manifest."""
    note_path = Path(mission_note)
    if not note_path.exists():
        print(f"ERROR: Mission note not found: {mission_note}", file=sys.stderr)
        return {"error": "note_not_found"}

    # Compute hash of the mission note itself
    note_hash = sha256_file(str(note_path))

    # Load existing manifest or create new
    sidecar = sidecar_path(mission_note)
    if sidecar.exists():
        with open(sidecar, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {
            "mission_note": str(note_path),
            "mission_note_hash": note_hash,
            "created_at": now_ts(),
            "evidence": [],
        }

    # Update note hash
    manifest["mission_note_hash"] = note_hash
    manifest["updated_at"] = now_ts()

    # Add new evidence entries
    existing_paths = {e["path"] for e in manifest["evidence"]}
    added = 0
    for ev_path in evidence_paths:
        ev_path = os.path.expanduser(ev_path)
        if ev_path in existing_paths:
            # Update hash for existing entry
            for entry in manifest["evidence"]:
                if entry["path"] == ev_path:
                    if os.path.isfile(ev_path):
                        entry["sha256"] = sha256_file(ev_path)
                        entry["verified_at"] = now_ts()
                    break
            continue

        if os.path.isfile(ev_path):
            ev_hash = sha256_file(ev_path)
            ev_type = _guess_type(ev_path)
        elif os.path.isdir(ev_path):
            ev_hash = "directory"
            ev_type = "directory"
        else:
            ev_hash = "missing"
            ev_type = "missing"

        manifest["evidence"].append({
            "id": f"ev-{len(manifest['evidence']) + 1:03d}",
            "path": ev_path,
            "sha256": ev_hash,
            "type": ev_type,
            "created_at": now_ts(),
        })
        existing_paths.add(ev_path)
        added += 1

    # Write sidecar
    with open(sidecar, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"Manifest: {sidecar}")
    print(f"Mission note hash: {note_hash}")
    print(f"Total evidence: {len(manifest['evidence'])} ({added} new)")
    return manifest


def verify_manifest(mission_note: str) -> dict:
    """Verify mission note hash and all evidence hashes."""
    sidecar = sidecar_path(mission_note)
    if not sidecar.exists():
        print(f"ERROR: No sidecar manifest found: {sidecar}", file=sys.stderr)
        return {"error": "no_manifest"}

    with open(sidecar, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    results = {"note_ok": False, "evidence_ok": 0, "evidence_fail": 0, "evidence_missing": 0}

    # Verify mission note hash
    note_path = Path(mission_note)
    if note_path.exists():
        current_hash = sha256_file(str(note_path))
        results["note_ok"] = current_hash == manifest.get("mission_note_hash")
        if not results["note_ok"]:
            print(f"FAIL: Mission note hash mismatch")
            print(f"  Expected: {manifest.get('mission_note_hash')}")
            print(f"  Current:  {current_hash}")
        else:
            print(f"OK: Mission note hash verified")
    else:
        print(f"FAIL: Mission note not found: {mission_note}")

    # Verify evidence
    for ev in manifest.get("evidence", []):
        ev_path = ev["path"]
        if ev["sha256"] in ("directory", "missing"):
            if ev["sha256"] == "missing":
                results["evidence_missing"] += 1
                print(f"WARN: Evidence missing: {ev_path}")
            continue

        if not os.path.isfile(ev_path):
            results["evidence_missing"] += 1
            print(f"WARN: Evidence file not found: {ev_path}")
            continue

        current_hash = sha256_file(ev_path)
        if current_hash == ev["sha256"]:
            results["evidence_ok"] += 1
            print(f"OK: {ev['id']} {os.path.basename(ev_path)}")
        else:
            results["evidence_fail"] += 1
            print(f"FAIL: {ev['id']} {os.path.basename(ev_path)} hash mismatch")

    total = results["evidence_ok"] + results["evidence_fail"] + results["evidence_missing"]
    print(f"\nSummary: {results['evidence_ok']}/{total} verified, {results['evidence_fail']} failed, {results['evidence_missing']} missing")
    return results


def list_manifest(mission_note: str) -> None:
    """Print the evidence manifest for a mission note."""
    sidecar = sidecar_path(mission_note)
    if not sidecar.exists():
        print(f"No sidecar manifest: {sidecar}")
        return

    with open(sidecar, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"Mission: {manifest.get('mission_note')}")
    print(f"Note hash: {manifest.get('mission_note_hash')}")
    print(f"Created: {manifest.get('created_at')}")
    print(f"Updated: {manifest.get('updated_at')}")
    print(f"\nEvidence ({len(manifest.get('evidence', []))} entries):")
    for ev in manifest.get("evidence", []):
        print(f"  {ev['id']}: {ev['path']}")
        print(f"       sha256: {ev['sha256'][:16]}...")
        print(f"       type: {ev['type']}, created: {ev['created_at']}")


def hash_file(path: str) -> None:
    """Print SHA-256 hash of a file."""
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        return
    h = sha256_file(path)
    print(f"{h}  {path}")


def _guess_type(path: str) -> str:
    """Guess evidence type from file extension."""
    ext = Path(path).suffix.lower()
    return {
        ".json": "json-data",
        ".md": "markdown",
        ".txt": "text",
        ".jpg": "screenshot",
        ".jpeg": "screenshot",
        ".png": "screenshot",
        ".py": "script",
        ".sh": "script",
        ".log": "log",
        ".csv": "tabular",
        ".html": "web-artifact",
    }.get(ext, "unknown")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("  evidence_manifest.py create <mission_note.md> [evidence_paths...]")
        print("  evidence_manifest.py verify <mission_note.md>")
        print("  evidence_manifest.py list <mission_note.md>")
        print("  evidence_manifest.py hash <file_path>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "create":
        create_manifest(sys.argv[2], sys.argv[3:])
    elif cmd == "verify":
        verify_manifest(sys.argv[2])
    elif cmd == "list":
        list_manifest(sys.argv[2])
    elif cmd == "hash":
        hash_file(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
