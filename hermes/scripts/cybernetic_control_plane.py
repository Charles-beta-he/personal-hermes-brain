#!/usr/bin/env python3
"""Warn-only cybernetic observer/feedforward precheck for Hermes brain tasks."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

def classify_text(text: str) -> dict:
    signals=[]
    low=text.lower()
    checks=[
        ('missing_acceptance_evidence', 'acceptance_evidence:' not in text),
        ('model_only_truth_risk', '多模型同意' in text and 'source' not in low and 'evidence' not in low),
        ('dev_boundary_risk', 'dev' in low and 'return_to_brain' not in text and 'handback' not in low),
        ('hard_gate_risk', 'hard block' in low or '硬阻塞' in text),
        ('runtime_surface', 'dispatch' in low or 'taskpool' in low or 'autorun' in low),
    ]
    for name, hit in checks:
        if hit: signals.append(name)
    score=sum({'missing_acceptance_evidence':2,'model_only_truth_risk':3,'dev_boundary_risk':2,'hard_gate_risk':3,'runtime_surface':1}[s] for s in signals)
    level='low' if score < 3 else 'medium' if score < 6 else 'high'
    return {"mode":"warn_only", "risk_level":level, "score":score, "signals":signals, "blocks_dispatch":False,
            "recommendation":"emit warning and require explicit evidence/handback before closure" if score>=3 else "no warning"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('path', nargs='?')
    p.add_argument('--text')
    p.add_argument('--demo', action='store_true')
    p.add_argument('--json', action='store_true')
    args=p.parse_args()
    if args.demo:
        text='多模型同意 dev taskpool dispatch 硬阻塞 but no handback source packet'
    elif args.text:
        text=args.text
    elif args.path:
        text=Path(args.path).read_text()
    else:
        text=''
    out=classify_text(text)
    print(json.dumps(out, ensure_ascii=False, indent=2) if args.json else out)
    return 0
if __name__ == '__main__': raise SystemExit(main())
