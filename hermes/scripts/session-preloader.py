#!/usr/bin/env python3
"""
Session Preloader — 根据意图预测预加载 skill
用法: python3 session-preloader.py [optional_task_hint]
"""
import os, json, sys

HEALTH = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/health-history.jsonl")
PRED = os.path.expanduser("~/.hermes/notes/reports/intent-prediction.md")

def load_jsonl(path):
    recs = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                try: recs.append(json.loads(line))
                except: pass
    return recs

def predict_task():
    """基于历史频率预测下一个任务类型"""
    recs = load_jsonl(HEALTH)
    from collections import Counter
    freq = Counter(r.get("task_type", "general") for r in recs)
    if not freq:
        return "general", 0.0
    top = freq.most_common(1)[0]
    return top[0], top[1] / len(recs)

SKILL_MAP = {
    "refactor": ["p7", "p9", "test-driven-development", "systematic-debugging"],
    "system-activation": ["p10", "auto-optimize-loop", "loop"],
    "obsidian-setup": ["obsidian", "note-taking", "sync-to-obsidian"],
    "general": ["p7", "p9"],
    "unknown": ["p7", "p9", "p10"],
}

def main():
    task, confidence = predict_task()
    hint = sys.argv[1] if len(sys.argv) > 1 else None
    
    # 如果有用户提示，优先使用
    if hint:
        task = hint
        confidence = 1.0
    
    skills = SKILL_MAP.get(task, ["p7", "p9"])
    
    print(f"意图预测: {task} (置信度 {confidence:.0%})")
    print(f"预加载 skills: {', '.join(skills)}")
    print()
    print("建议操作:")
    for s in skills:
        print(f"  skill_view('{s}')")
    
    # 保存预加载建议
    preload_path = os.path.expanduser("~/.hermes/.preload-recommendation.json")
    with open(preload_path, "w") as f:
        json.dump({
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "predicted_task": task,
            "confidence": confidence,
            "recommended_skills": skills,
        }, f)

if __name__ == "__main__":
    main()
