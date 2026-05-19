#!/usr/bin/env python3
"""Read-only knowledge atom collision candidate generator.

Suggests candidate relations/emergent atoms; never writes core atoms.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from collections import Counter

def tokens(text: str):
    return set(re.findall(r'[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}', text))

def load_atoms(atom_dir: Path, limit: int):
    files=sorted(atom_dir.glob('*.md'))[:limit]
    return [{'path':str(p), 'title':p.stem, 'tokens':tokens(p.read_text(errors='ignore'))} for p in files]

def suggest(atoms):
    pairs=[]
    for i,a in enumerate(atoms):
        for b in atoms[i+1:]:
            common=sorted((a['tokens'] & b['tokens']), key=len, reverse=True)[:8]
            if len(common)>=2:
                pairs.append({'a':a['title'],'b':b['title'],'shared_terms':common,'score':len(common)})
    pairs=sorted(pairs, key=lambda x:x['score'], reverse=True)
    candidates=[]
    for p in pairs[:3]:
        candidates.append({
            'candidate':'候选关系: '+p['a']+' × '+p['b'],
            'basis':p['shared_terms'],
            'source_gap':'需要人工/main核验共享词是否代表真实概念关系，而非同词偶合',
            'write_policy':'suggest_only_no_core_atom_write'
        })
    return candidates

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--atom-dir', default='brain/04-知识原子/atoms')
    ap.add_argument('--limit', type=int, default=12)
    ap.add_argument('--json', action='store_true')
    args=ap.parse_args()
    atoms=load_atoms(Path(args.atom_dir), args.limit)
    out={'status':'OK' if len(atoms)>=2 else 'WARN', 'atom_count':len(atoms), 'mode':'read_only_suggest_only', 'candidates':suggest(atoms), 'writes_core_atoms':False}
    print(json.dumps(out, ensure_ascii=False, indent=2) if args.json else out)
    return 0 if atoms else 1
if __name__ == '__main__': raise SystemExit(main())
