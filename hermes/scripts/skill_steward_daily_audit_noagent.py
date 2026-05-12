#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path.home() / ".hermes" / "scripts" / "skill-steward.py"


def main() -> int:
    cmd = [sys.executable, str(SCRIPT), "--graph-check", "--warn-only", "--json"]
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=300)
    stdout = (p.stdout or "").strip()
    stderr = (p.stderr or "").strip()
    data = None
    try:
        data = json.loads(stdout) if stdout else None
    except Exception:
        data = None
    payload = {
        "schema": "skill_steward_daily_audit_noagent_v1",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "OK" if p.returncode == 0 else "ERROR",
        "returncode": p.returncode,
        "graph_status": data.get("status") if isinstance(data, dict) else None,
        "graph_value": data.get("value") if isinstance(data, dict) else None,
        "stdout_tail": stdout[-3000:] if not isinstance(data, dict) else "",
        "stderr_tail": stderr[-1000:],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if p.returncode == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
