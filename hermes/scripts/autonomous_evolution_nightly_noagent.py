#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path.home() / ".hermes" / "scripts" / "autonomous-evolution-nightly.py"


def main() -> int:
    p = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True, timeout=300)
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    payload = {
        "schema": "autonomous_evolution_nightly_noagent_v1",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "OK" if p.returncode == 0 else "ERROR",
        "returncode": p.returncode,
        "stdout_tail": out[-3000:],
        "stderr_tail": err[-1000:],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if p.returncode == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
