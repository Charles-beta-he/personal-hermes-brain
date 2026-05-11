#!/usr/bin/env bash
# self-describe.sh — Hermes 自描述 v2 (增强版)
# 输出: /tmp/hermes-state.json (summary, <8K) + /tmp/hermes-state-full.json (full)
set -euo pipefail

OUT="/tmp/hermes-state.json"
FULL_OUT="/tmp/hermes-state-full.json"
NOW=$(date -u +%FT%TZ)
STATE_HASH=""  # computed after FULL_OUT is written
HOME_DIR="${HOME}/.hermes"

mkdir -p "$(dirname "$OUT")"

# ── 收集所有原始数据 ──
ROUTE_STORE="$HOME_DIR/scripts/route_store.py"

# route stats (JSON)
ROUTE_STATS=$(python3 "$ROUTE_STORE" stats 2>/dev/null || echo '{}')
ROUTE_SCORES=$(python3 "$ROUTE_STORE" scores 2>/dev/null || echo '[]')

# route summary (text)
ROUTE_SUMMARY=$(python3 "$ROUTE_STORE" summary 2>/dev/null || echo 'N/A')

# evolve log
EVOLVE_LOG_RAW=$(tail -20 "$HOME_DIR/logs/evolve.log" 2>/dev/null || echo '')

# cron
CRON_RAW=$(hermes cron status 2>/dev/null || echo '')
GATEWAY_RUNNING=0
echo "$CRON_RAW" | grep -q "Gateway is running" && GATEWAY_RUNNING=1

# config highlights
CONFIG_HIGHLIGHTS=$(python3 -c "
import yaml, json
with open('$HOME_DIR/config.yaml') as f:
    cfg = yaml.safe_load(f)
highlights = {}
# approvals
approvals = cfg.get('approvals', {})
highlights['cron_mode'] = approvals.get('cron_mode', '?')
# skills
skills = cfg.get('skills', {})
highlights['canary_ratio'] = skills.get('canary_ratio', 0)
# evolve
evolve = cfg.get('evolve', {})
for k in ['min_traces_for_action', 'min_traces_for_eval', 'min_traces_for_rollout']:
    if k in evolve:
        highlights[k] = evolve[k]
auto = evolve.get('auto_approve', {})
highlights['auto_approve_enabled'] = auto.get('enabled', False)
# hooks
hooks = cfg.get('hooks', {})
highlights['hooks_auto_accept'] = cfg.get('hooks_auto_accept', False)
# gateway
highlights['gateway_running'] = bool($GATEWAY_RUNNING)
# mcp
mcp = cfg.get('mcp_servers', {})
highlights['mcp_servers'] = list(mcp.keys())
print(json.dumps(highlights))
" 2>/dev/null || echo '{}')

# mcp count
MCP_COUNT=$(echo "$CONFIG_HIGHLIGHTS" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('mcp_servers',[])))" 2>/dev/null || echo 0)

# cron count
CRON_COUNT=$(python3 -c "
import json
with open('$HOME_DIR/cron/jobs.json') as f:
    data = json.load(f)
if isinstance(data, dict) and 'jobs' in data:
    print(len(data['jobs']))
elif isinstance(data, list):
    print(len(data))
else:
    print(0)
" 2>/dev/null || echo 0)

# skills count
SKILLS_COUNT=$(find "$HOME_DIR/skills" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')

# staging count
STAGING_COUNT=$(find "$HOME_DIR/skills-staging" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')

# evolve stats
EVOLVE_STATS=$(python3 -c "
import json, sys
try:
    with open('$HOME_DIR/logs/evolve.log') as f:
        lines = [json.loads(l.strip()) for l in f if l.strip()]
    total = len(lines)
    kept = sum(1 for l in lines if l.get('eval_result') == 'kept')
    rolled = sum(1 for l in lines if l.get('eval_result') == 'rolled_back')
    degraded = sum(1 for l in lines if l.get('degraded') == True)
    last = lines[-1] if lines else {}
    print(json.dumps({
        'total_ticks': total,
        'kept': kept,
        'rolled_back': rolled,
        'degraded': degraded,
        'latest_result': last.get('eval_result', '?'),
        'latest_diagnosis': last.get('diagnosis', '')[:200],
        'latest_ts': last.get('ts', ''),
    }))
except Exception as e:
    print(json.dumps({'error': str(e)}))
" 2>/dev/null || echo '{}')

# skill categories (top 10)
SKILL_CATS=$(python3 -c "
import os, json, collections
skills_dir = '$HOME_DIR/skills'
cats = collections.Counter()
for root, dirs, files in os.walk(skills_dir):
    for f in files:
        if f == 'SKILL.md':
            rel = root.replace(skills_dir + '/', '')
            cat = rel.split('/')[0] if '/' in rel else 'root'
            cats[cat] += 1
top = cats.most_common(10)
print(json.dumps({k: v for k, v in top}))
" 2>/dev/null || echo '{}')

# self-test
SELF_TEST=$(python3 "$HOME_DIR/scripts/self-test.py" 2>/dev/null | grep "ALL PASS\|Self-Test" || echo 'N/A')
SELF_TEST_PASS=0
echo "$SELF_TEST" | grep -q "ALL PASS" && SELF_TEST_PASS=1

# failure modes from route_outcomes
FAILURE_MODES=$(python3 -c "
import sqlite3, json
try:
    conn = sqlite3.connect('$HOME_DIR/route_outcomes.db')
    rows = conn.execute('''SELECT route, error, COUNT(*) as cnt 
        FROM route_outcomes WHERE verdict='fail' 
        GROUP BY route, error ORDER BY cnt DESC LIMIT 5''').fetchall()
    modes = [{'route': r[0], 'error': r[1][:60], 'count': r[2]} for r in rows]
    print(json.dumps(modes))
    conn.close()
except:
    print('[]')
" 2>/dev/null || echo '[]')

# ── Write Full Details ──
python3 -c "
import json, os
d = {
    'captured_at': '$NOW',
    'route_summary_text': '''$ROUTE_SUMMARY''',
    'route_scores': json.loads('''$ROUTE_SCORES'''),
    'route_stats': json.loads('''$ROUTE_STATS'''),
    'config_highlights': json.loads('''$CONFIG_HIGHLIGHTS'''),
    'skill_categories': json.loads('''$SKILL_CATS'''),
    'failure_modes': json.loads('''$FAILURE_MODES'''),
    'warnings': []
}
with open('$FULL_OUT', 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False, default=str)
" 2>/dev/null || true

# Compute state_hash after FULL_OUT is written
STATE_HASH=$(sha256sum "$FULL_OUT" 2>/dev/null | cut -d' ' -f1 || echo "00000000")

# ── Build Summary ──
python3 -c "
import json, os

evolve = json.loads('''$EVOLVE_STATS''')
config = json.loads('''$CONFIG_HIGHLIGHTS''')
failures = json.loads('''$FAILURE_MODES''')
cats = json.loads('''$SKILL_CATS''')

s = {
    'skills_count': int('$SKILLS_COUNT'),
    'skills_staging': int('$STAGING_COUNT'),
    'skill_categories_top5': dict(list(cats.items())[:5]) if cats else {},
    'cron_count': int('$CRON_COUNT'),
    'gateway_running': bool(int('$GATEWAY_RUNNING')),
    'mcp_count': int('$MCP_COUNT'),
    'self_test_pass': bool(int('$SELF_TEST_PASS')),
    'route_outcomes_traces': 0,
    'route_real_traces': 0,
    'route_synthetic_traces': 0,
    'pass_rate_7d': 'N/A',
    'pass_rate_overall_7d': 'N/A',
    'pass_rate_real_7d': 'N/A',
    'pass_rate_synthetic_7d': 'N/A',
    'pass_rate_main_7d': 'N/A',
    'route_main_excluded_counts': {},
    'top_failure_modes': [],
    'top_routes': '',
    'evolve_total_ticks': evolve.get('total_ticks', 0),
    'evolve_kept': evolve.get('kept', 0),
    'evolve_rolled_back': evolve.get('rolled_back', 0),
    'evolve_latest_result': evolve.get('latest_result', '?'),
    'evolve_latest_diagnosis': evolve.get('latest_diagnosis', '')[:150],
    'config_cron_mode': config.get('cron_mode', '?'),
    'config_canary_ratio': config.get('canary_ratio', 0),
    'config_auto_approve': config.get('auto_approve_enabled', False),
    'config_min_traces': config.get('min_traces_for_eval', '?'),
    'warnings': []
}

# Parse route stats for traces
try:
    stats = json.loads('''$ROUTE_STATS''')
    views = stats.get('views', {})
    overall = views.get('overall', stats)
    real_only = views.get('real_only', {})
    synthetic_only = views.get('synthetic_only', {})
    main = views.get('main', stats)
    s['route_outcomes_traces'] = overall.get('total', 0)
    s['route_real_traces'] = overall.get('real', 0)
    s['route_synthetic_traces'] = overall.get('synthetic', 0)
    s['pass_rate_overall_7d'] = str(overall.get('pass_rate', 'N/A'))
    s['pass_rate_real_7d'] = str(real_only.get('pass_rate', 'N/A'))
    s['pass_rate_synthetic_7d'] = str(synthetic_only.get('pass_rate', 'N/A'))
    s['pass_rate_main_7d'] = str(main.get('pass_rate', stats.get('main_pass_rate', 'N/A')))
    s['pass_rate_7d'] = s['pass_rate_main_7d']
    s['route_main_excluded_counts'] = {
        (r.get('route') if r.get('route') else 'blank'): r.get('total', 0)
        for r in stats.get('excluded_from_main', [])
    }
except:
    pass

# Top routes from scores
try:
    scores = json.loads('''$ROUTE_SCORES''')
    if isinstance(scores, list):
        items = [f\"{x.get('route','?')}: pass={x.get('pass_rate',0)} score={x.get('score',0)}\" for x in scores[:5]]
        s['top_routes'] = '; '.join(items)
except:
    pass

# Failure modes
if failures:
    s['top_failure_modes'] = [f\"{f['route']}: {f['error'][:40]} ({f['count']}x)\" for f in failures[:3]]

d = {
    'schema_version': '3',
    'captured_at': '$NOW',
    'state_hash': '$STATE_HASH',
    'mode': 'summary',
    'details_pointer': '$FULL_OUT',
    'summary': s,
}
with open('$OUT', 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False, default=str)
" 2>/dev/null || true

echo "$OUT"
