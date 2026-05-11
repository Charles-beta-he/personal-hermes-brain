#!/usr/bin/env python3
"""
Skill Recommender — 基于任务类型推荐最佳 skill 组合
用法: python3 skill-recommender.py <task_type>
"""
import os, sys, json

DB = os.path.expanduser("~/.hermes/skills/bayesian-agent/confidence-db.json")

# 任务 → skill 映射 (经验规则 + 历史数据)
TASK_SKILL_MAP = {
    "refactor": ["p7", "p9", "test-driven-development", "systematic-debugging", "requesting-code-review"],
    "system-activation": ["p10", "auto-optimize-loop", "loop", "hermes-workflow-orchestrator"],
    "obsidian-setup": ["obsidian", "note-taking", "sync-to-obsidian", "productivity"],
    "deploy": ["devops", "cloudflare-pages-pnpm", "semantic-release-monorepo", "post-deploy-verification"],
    "frontend": ["p7", "p9", "color-contrast-checker", "uimax-audit", "visual-regression"],
    "debug": ["p7", "systematic-debugging", "test-driven-development"],
    "planning": ["p10", "p9", "writing-plans", "requirement-clarification"],
    "research": ["research", "arxiv", "llm-wiki"],
    "creative": ["creative", "ascii-art", "excalidraw", "architecture-diagram"],
    "general": ["p7", "p9", "p10"],
}

def load_db():
    with open(DB) as f:
        return json.load(f)

def recommend(task_type):
    db = load_db()
    skills = TASK_SKILL_MAP.get(task_type, TASK_SKILL_MAP["general"])
    
    # 按等级排序 (S > A > B > C)
    grade_rank = {"S": 4, "A": 3, "B": 2, "C": 1, "D": 0}
    scored = []
    for s in skills:
        if s in db["skills"]:
            g = db["skills"][s].get("darwin_grade", "C")
            score = db["skills"][s].get("darwin_score", 0)
            scored.append((s, g, score, grade_rank.get(g, 0)))
        else:
            scored.append((s, "?", 0, 0))
    
    scored.sort(key=lambda x: (-x[3], -x[2]))
    return scored

def main():
    task = sys.argv[1] if len(sys.argv) > 1 else "general"
    recs = recommend(task)
    
    print(f"任务类型: {task}")
    print(f"推荐 skill (按优先级):")
    for i, (name, grade, score, _) in enumerate(recs, 1):
        icon = "⭐" if grade in ("S", "A") else "  "
        print(f"  {icon} {i}. {name:30s} [{grade}] ({score})")

if __name__ == "__main__":
    main()
