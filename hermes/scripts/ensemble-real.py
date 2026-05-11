#!/usr/bin/env python3
"""Minimal real ensemble wrapper for actual-usage corpus."""
from __future__ import annotations
import argparse, json, subprocess, time, uuid, urllib.request, os
from datetime import datetime, timezone
from pathlib import Path
H=Path.home()/'.hermes'; LOG=H/'logs'/'ensemble-votes.jsonl'; ENV=H/'.env'
def utc(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def load_env():
    d=dict(os.environ)
    if ENV.exists():
        for line in ENV.read_text(errors='ignore').splitlines():
            if '=' in line and not line.strip().startswith('#'):
                k,v=line.split('=',1); d.setdefault(k.strip(),v.strip().strip('"').strip("'"))
    return d
def call_cmd(cmd, timeout=90):
    t=time.perf_counter()
    try:
        r=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
        return {'ok':r.returncode==0,'text':(r.stdout or '').strip()[:1000],'err':(r.stderr or '').strip()[:500],'latency_ms':round((time.perf_counter()-t)*1000)}
    except Exception as e: return {'ok':False,'text':'','err':repr(e),'latency_ms':round((time.perf_counter()-t)*1000)}
def deepseek(prompt, timeout=90):
    key=load_env().get('DEEPSEEK_API_KEY')
    if not key: return {'ok':False,'text':'','err':'missing key','latency_ms':0}
    body=json.dumps({'model':'deepseek-chat','messages':[{'role':'user','content':prompt}],'max_tokens':80,'temperature':0}).encode(); req=urllib.request.Request('https://api.deepseek.com/chat/completions',data=body,headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'})
    t=time.perf_counter()
    try:
        with urllib.request.urlopen(req,timeout=timeout) as resp: data=json.loads(resp.read().decode())
        return {'ok':True,'text':data.get('choices',[{}])[0].get('message',{}).get('content','')[:1000],'err':'','latency_ms':round((time.perf_counter()-t)*1000)}
    except Exception as e: return {'ok':False,'text':'','err':repr(e),'latency_ms':round((time.perf_counter()-t)*1000)}
def verdict(text):
    low=(text or '').lower()
    if 'fail' in low or 'reject' in low: return 'fail'
    if 'pass' in low or 'approve' in low or 'yes' in low or 'ack' in low: return 'pass'
    return 'partial'
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('task', nargs='?', default='Smoke: reply PASS if real ensemble execution works.'); ap.add_argument('--skip-claude',action='store_true'); args=ap.parse_args(); rid=str(uuid.uuid4())[:8]
    # Individual models cannot know whether the whole ensemble is healthy.
    # Ask only for locally verifiable truth; the wrapper computes ensemble health.
    prompt=f"You are one voter in Hermes ensemble run={rid}. Task: {args.task}\nIf you are a real model invocation and received this prompt, return exactly: PASS real-call. Otherwise return FAIL."
    calls={'gpt-5.5':call_cmd(['hermes','chat','-q',prompt,'--provider','openai-codex','--model','gpt-5.5','--quiet','--ignore-rules','--max-turns','1','--source','tool']),'mimo-v2.5-pro':call_cmd(['hermes','chat','-q',prompt,'--provider','xiaomi','--model','mimo-v2.5-pro','--quiet','--ignore-rules','--max-turns','1','--source','tool']),'deepseek-v4-pro':deepseek(prompt)}
    if not args.skip_claude: calls['claude-opus-4-7']=call_cmd(['claude','-p',prompt,'--model','opus','--max-turns','1','--allowedTools',''])
    votes={m:verdict(v['text']) if v['ok'] else 'timeout' for m,v in calls.items()}; total=sum(1 for v in votes.values() if v!='timeout'); pass_votes=sum(1 for v in votes.values() if v=='pass')
    rec={'ts':utc(),'task':args.task,'run_id':rid,'execute':True,'strategy':'weighted_majority','models':list(calls.keys()),'votes':votes,'total_voters':total,'verdict':'pass' if pass_votes>=max(2,total//2+1) else 'fail','consensus':len(set(votes.values()))==1,'details':calls}
    LOG.parent.mkdir(parents=True,exist_ok=True); LOG.open('a').write(json.dumps(rec,ensure_ascii=False)+'\n'); print(json.dumps(rec,ensure_ascii=False,indent=2)); return 0 if rec['verdict']=='pass' else 2
if __name__=='__main__': raise SystemExit(main())
