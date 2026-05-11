#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path

VAULT = Path.home() / 'Documents' / 'brain'
REQUIRED = [
 '05-实践与项目/projects/agent-systems-engineering-control-plane/Project - Agent系统工程控制面.md',
 '05-实践与项目/projects/agent-systems-engineering-control-plane/P10 - 系统工程式Agent自进化策略.md',
 '05-实践与项目/projects/agent-systems-engineering-control-plane/P9 - 实施Backlog.md',
 '07-仪表盘/Agent技能树路由矩阵.md',
 '08-模板/项目工作记忆模板.md',
 '05-实践与项目/实践方案/前端闭环验收标准.md',
 '04-知识原子/atoms/系统工程四环Agent映射.md',
 '06-治理与评审/reviews/2026-05-08-qian-systems-engineering-agent-gap-review.md',
 '06-治理与评审/reviews/2026-05-08-qian-systems-engineering-agent-gap-certification.json',
 '05-实践与项目/tasks/2026-05-08-qian-systems-engineering-control-plane-landing-log.md',
 '06-治理与评审/进化日志/2026-05-08-agent-systems-engineering-control-plane.md',
]
# Use exact title / bilingual keyword queries that the current brainctl FTS tokenizer reliably matches.
QUERIES = ['Agent技能树路由矩阵', 'Project Workpad', 'frontend closure testing', '系统工程四环 Agent 映射']

def run(cmd):
    p = subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def main():
    missing=[]
    for rel in REQUIRED:
        if not (VAULT/rel).exists():
            missing.append(rel)
    query_results=[]
    for q in QUERIES:
        code,out,err=run(f"python3 ~/.hermes/scripts/brainctl.py --json search {json.dumps(q, ensure_ascii=False)} --limit 5")
        try:
            parsed=json.loads(out) if out else []
        except Exception:
            parsed=[]
        query_results.append({'query':q,'exit_code':code,'hits':len(parsed),'top':parsed[:1]})
    status='PASS' if not missing and all(x['hits']>0 for x in query_results) else 'FAIL'
    result={'status':status,'missing':missing,'query_results':query_results,'vault':str(VAULT)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if status=='PASS' else 2
if __name__ == '__main__':
    raise SystemExit(main())
