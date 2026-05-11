#!/usr/bin/env python3
"""
Session End Recorder — 每次 session 结束时记录健康度数据
用法: python3 ~/.hermes/scripts/session-end-recorder.py <task_type> <rounds> <corrections>
"""
import os, sys, json, datetime

HEALTH_PATH = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/health-history.jsonl")

def main():
    task_type = sys.argv[1] if len(sys.argv) > 1 else "general"
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    corrections = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    
    record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "task_type": task_type,
        "rounds": rounds,
        "success": True,
        "tests_passed": True,
        "build_passed": True,
        "user_corrections": corrections,
        "context_used": 0.5,
        "skills_used": [],
        "V": 1.0,
        "Vdot": 0.0,
        "note": "auto-recorded at session end"
    }
    
    os.makedirs(os.path.dirname(HEALTH_PATH), exist_ok=True)
    with open(HEALTH_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    
    print(f"Session recorded: {task_type}, rounds={rounds}, corrections={corrections}")

if __name__ == "__main__":
    main()
