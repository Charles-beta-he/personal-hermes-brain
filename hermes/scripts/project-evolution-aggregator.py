#!/usr/bin/env python3
"""
Project Evolution Aggregator — 汇总多个项目的进化状态
"""
import os, json, glob

PROJECTS = {
    "arc-dispatch": "/Users/charles/Desktop/folder/arc-dispatch/.evolution",
    "gomoku-react": "/Users/charles/Desktop/folder/gomoku-react/.evolution",
}

def main():
    print("=" * 60)
    print("Cross-Project Evolution Summary")
    print("=" * 60)
    
    for name, evo_path in PROJECTS.items():
        health = os.path.join(evo_path, "health-history.jsonl")
        if os.path.exists(health):
            with open(health) as f:
                lines = [l for l in f if l.strip()]
            if lines:
                latest = json.loads(lines[-1])
                V = latest.get("V", 0.5)
                tasks = latest.get("tasks_completed", 0)
                status = "🟢" if V > 0.7 else "🟡" if V > 0.5 else "🔴"
                print(f"  {status} {name:20s} V={V:.4f} tasks={tasks}")
        else:
            print(f"  ⚪ {name:20s} no data")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
