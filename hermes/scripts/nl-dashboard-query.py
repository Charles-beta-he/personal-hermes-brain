#!/usr/bin/env python3
"""
NL Dashboard Query — 自然语言查询系统状态
"""
import os, sys, json

HEALTH = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/health-history.jsonl")
PA_HEALTH = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/pa-health-history.jsonl")
DB = os.path.expanduser("~/.hermes/skills/bayesian-agent/confidence-db.json")

def load_jsonl(path):
    recs = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                try: recs.append(json.loads(line))
                except: pass
    return recs

def load_db():
    with open(DB) as f:
        return json.load(f)

def query(q):
    q = q.lower()
    
    # D grade check (before general skill check)
    if any(k in q for k in ["d级", "d grade", "d ", "最弱", "最差", "清零"]):
        db = load_db()
        d_skills = [n for n,d in db["skills"].items() if d.get("darwin_grade") == "D"]
        if d_skills:
            return f"D 级 skill: {', '.join(d_skills)}"
        return "🎉 D 级已清零！"
    
    # Skill distribution
    if any(k in q for k in ["skill", "等级", "分布", "a级", "b级", "c级"]):
        db = load_db()
        g = {"A":0,"B":0,"C":0,"D":0}
        for d in db["skills"].values():
            g[d.get("darwin_grade","C")] += 1
        return f"Skill 分布: A={g['A']} B={g['B']} C={g['C']} D={g['D']} (共 {sum(g.values())})"
    
    # PA
    if any(k in q for k in ["pa", "个人助理", "进化", "level"]):
        recs = load_jsonl(PA_HEALTH)
        if recs:
            latest = recs[-1]
            v = latest.get("V_pa", 0.5)
            level = "Level 1" if v < 0.6 else "Level 2" if v < 0.72 else "Level 3" if v < 0.82 else "Level 4" if v < 0.9 else "Level 5"
            return f"PA 健康度 V_PA = {v:.4f} ({level})"
        return "PA 暂无记录"
    
    # Health V
    if any(k in q for k in ["健康度", "health", "v ", "v值", "状态"]):
        recs = load_jsonl(HEALTH)
        if recs:
            latest = recs[-1]
            return f"最新健康度 V = {latest.get('V', 0):.4f} (记录 {len(recs)} 次)"
        return "暂无健康度记录"
    
    # Cronjob
    if any(k in q for k in ["cronjob", "定时", "任务", "job"]):
        return "当前 5 个 cronjob: 每日健康(0:00) | 每周分析(周一9:00) | 4H扫描 | PA日报(23:00) | 夜间审计(2:00)"
    
    return f"不知道 '{q}' 是什么意思。试试: 健康度、skill分布、PA等级、cronjob、D级清零"

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "状态"
    print(query(q))
