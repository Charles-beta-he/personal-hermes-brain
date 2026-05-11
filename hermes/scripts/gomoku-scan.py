#!/usr/bin/env python3
"""预采集脚本 — cron job 运行前自动收集项目状态"""
import os, subprocess, json, glob
from datetime import datetime

project = "/Users/charles/Desktop/folder/gomoku-react"
output = {}

# 1. Git status
r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=project)
output["git_status"] = r.stdout.strip()

# 2. Git log (recent 5)
r = subprocess.run(["git", "log", "--oneline", "-5"], capture_output=True, text=True, cwd=project)
output["git_log"] = r.stdout.strip()

# 3. Test results
r = subprocess.run(["pnpm", "test"], capture_output=True, text=True, timeout=60, cwd=project)
output["test_exit_code"] = r.returncode
output["test_summary"] = r.stdout[-500:] if r.stdout else ""

# 4. TODO/FIXME scan
patterns = ["apps/web/src/**/*.js", "apps/web/src/**/*.jsx", "packages/core/src/**/*.js"]
todos = []
for pat in patterns:
    for f in glob.glob(os.path.join(project, pat), recursive=True):
        try:
            with open(f) as fh:
                for i, line in enumerate(fh, 1):
                    if any(tag in line for tag in ["TODO", "FIXME", "HACK", "XXX"]):
                        rel = os.path.relpath(f, project)
                        todos.append(f"{rel}:{i}: {line.strip()[:100]}")
        except: pass
output["todos"] = todos[:20]

# 5. Existing loop reports
claude_dir = os.path.join(project, ".claude")
reports = sorted([f for f in os.listdir(claude_dir) if f.startswith("loop-report")]) if os.path.isdir(claude_dir) else []
output["existing_reports"] = reports
output["next_report_num"] = len(reports) + 1

# 6. Timestamp
output["timestamp"] = datetime.now().isoformat()

print(json.dumps(output, ensure_ascii=False, indent=2))
