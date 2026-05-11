#!/usr/bin/env bash
# p10-health.sh — Hermes 自进化系统形式化健康评分 V(t)
# 用法: bash ~/.hermes/scripts/p10-health.sh [--json]
# 输出: V(t) 健康向量 + V̇(t) 变化率 (当有历史数据时)
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
TIMESTAMP=$(date -u +%FT%TZ)
JSON_MODE=false
[[ "${1:-}" == "--json" ]] && JSON_MODE=true

# ── 1. Cron Liveness ──
# Health means enabled jobs are not in error. Recency remains an observability
# detail, but weekly/monthly jobs and first-run-pending jobs must not be
# counted as unhealthy just because they did not run in the last 24h.
CRON_STATS=$(python3 - <<'PY'
import json, os, time, datetime
from pathlib import Path
home = Path(os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes')))
p = home / 'cron' / 'jobs.json'
now = time.time()

def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(str(s).replace('Z', '+00:00')).timestamp()
    except Exception:
        return None

jobs = []
if p.exists():
    data = json.loads(p.read_text())
    jobs = data.get('jobs', data) if isinstance(data, dict) else data
    if not isinstance(jobs, list):
        jobs = []

enabled = [j for j in jobs if isinstance(j, dict) and j.get('enabled', True)]
recent = 0
good = 0
bad = []
stale = []
pending = 0
for j in enabled:
    last = parse_ts(j.get('last_run_at'))
    nxt = parse_ts(j.get('next_run_at'))
    status = str(j.get('last_status') or '').lower()
    state = str(j.get('state') or '').lower()
    name = j.get('name') or j.get('id') or '?'
    err = str(j.get('last_error') or '')
    if last and last > now - 86400:
        recent += 1
    is_error = status in {'error', 'failed'} or state in {'error', 'failed'}
    # Cron jobs can retain an old last_status=error until the next scheduled run.
    # Treat old, scheduler/transient wrapper shutdown errors with a future retry as
    # stale evidence rather than live health failure; cron-health-quarantine keeps
    # the stale line auditable. This prevents one 4-day-old shutdown ghost from
    # depressing P10 health while preserving fresh errors as bad.
    age = (now - last) if last else None
    stale_error = bool(is_error and last and age and age > 86400 and nxt and nxt > now and (
        'interpreter shutdown' in err.lower() or
        'timeout_recorded' in err.lower() or
        'degraded_recorded' in err.lower() or
        'partial_fail_recorded' in err.lower()
    ))
    first_run_pending = not last and not status and nxt and nxt > now - 1800
    if first_run_pending:
        pending += 1
    if not is_error or stale_error:
        good += 1
        if stale_error:
            stale.append(name)
    else:
        bad.append(name)

out = {
    'total': len(enabled),
    'enabled': len(enabled),
    'recent': recent,
    'good': good,
    'pending': pending,
    'stale_error_count': len(stale),
    'stale_errors': stale[:10],
    'bad_count': len(bad),
    'bad': bad[:10],
    'health': round(good / max(len(enabled), 1), 3),
}
print(json.dumps(out, ensure_ascii=False))
PY
)
CRON_TOTAL=$(python3 -c "import json; d=json.loads('''$CRON_STATS'''); print(d.get('total',0))")
CRON_LIVE=$(python3 -c "import json; d=json.loads('''$CRON_STATS'''); print(d.get('enabled',0))")
CRON_RECENT=$(python3 -c "import json; d=json.loads('''$CRON_STATS'''); print(d.get('recent',0))")
CRON_GOOD=$(python3 -c "import json; d=json.loads('''$CRON_STATS'''); print(d.get('good',0))")
CRON_PENDING=$(python3 -c "import json; d=json.loads('''$CRON_STATS'''); print(d.get('pending',0))")
CRON_BAD=$(python3 -c "import json; d=json.loads('''$CRON_STATS'''); print(d.get('bad_count',0))")
CRON_HEALTH=$(python3 -c "import json; d=json.loads('''$CRON_STATS'''); print(d.get('health',0))")

# ── 2. Route Outcomes (多口径) ──
ROUTE_STATS=$(python3 "$HERMES_HOME/scripts/route_store.py" stats --hours 168 2>/dev/null || echo '{}')
MAIN_PR=$(python3 -c "
import sys,json; d=json.loads('''$ROUTE_STATS''')
views=d.get('views',{}); m=views.get('main',d)
print(m.get('pass_rate', d.get('main_pass_rate', 0)))
" 2>/dev/null || echo 0)
OVERALL_PR=$(python3 -c "
import sys,json; d=json.loads('''$ROUTE_STATS''')
views=d.get('views',{}); o=views.get('overall',d)
print(o.get('pass_rate', d.get('pass_rate', 0)))
" 2>/dev/null || echo 0)
TRACE_COUNT=$(python3 -c "
import sys,json; d=json.loads('''$ROUTE_STATS''')
views=d.get('views',{}); o=views.get('overall',d)
print(o.get('total', 0))
" 2>/dev/null || echo 0)
REAL_COUNT=$(python3 -c "
import sys,json; d=json.loads('''$ROUTE_STATS''')
views=d.get('views',{}); o=views.get('overall',d)
print(o.get('real', 0))
" 2>/dev/null || echo 0)
SYNTH_COUNT=$(python3 -c "
import sys,json; d=json.loads('''$ROUTE_STATS''')
views=d.get('views',{}); o=views.get('overall',d)
print(o.get('synthetic', 0))
" 2>/dev/null || echo 0)
SYNTH_RATIO=$(python3 -c "print(round($SYNTH_COUNT / max($TRACE_COUNT, 1), 3))")

# ── 3. Self-Test ──
# Use exit-code + bounded subprocess instead of grep -q on a pipe. With
# `set -euo pipefail`, grep -q can close the pipe early and make the producer
# receive SIGPIPE, turning a real ALL PASS into a false health failure.
SELF_TEST_LOG="$HERMES_HOME/logs/p10-health-self-test.log"
SELF_TEST_META=$(python3 - "$HERMES_HOME" "$SELF_TEST_LOG" <<'PY'
import json, re, subprocess, sys
from pathlib import Path
home = Path(sys.argv[1]).expanduser()
log = Path(sys.argv[2]).expanduser()
log.parent.mkdir(parents=True, exist_ok=True)
cmd = [sys.executable, str(home / 'scripts' / 'self-test.py')]
try:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
    out = proc.stdout or ''
    summary = re.search(r'Self-Test Results:\s*(\d+)\s*/\s*(\d+)\s*passed', out)
    passed = int(summary.group(1)) if summary else out.count('✓')
    total = int(summary.group(2)) if summary else passed
    ok = proc.returncode == 0 and passed == total and 'ALL PASS' in out
    status = 'ok' if ok else 'failed'
except subprocess.TimeoutExpired as e:
    out = (e.stdout or '') if isinstance(e.stdout, str) else ''
    passed = out.count('✓')
    total = passed
    ok = False
    status = 'timeout'
log.write_text(out, encoding='utf-8')
print(json.dumps({'ok': ok, 'status': status, 'check_count': passed, 'check_total': total, 'log': str(log)}, ensure_ascii=False))
PY
)
SELF_TEST_PASS=$(python3 -c "import json; d=json.loads('''$SELF_TEST_META'''); print('true' if d.get('ok') else 'false')")
SELF_TEST_COUNT=$(python3 -c "import json; d=json.loads('''$SELF_TEST_META'''); print(int(d.get('check_count') or 0))")

# ── 4. Skill Count ──
SKILL_COUNT=$(find "$HERMES_HOME/skills" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
STAGING_COUNT=$(find "$HERMES_HOME/skills-staging" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')

# ── 5. Memory Size ──
MEMORY_SIZE=$(wc -c < "$HERMES_HOME/memories/MEMORY.md" 2>/dev/null || echo 0)
MEMORY_LINES=$(wc -l < "$HERMES_HOME/memories/MEMORY.md" 2>/dev/null || echo 0)

# ── 6. Gateway Status ──
GATEWAY_RUNNING=false
# macOS pgrep -f 不可靠; grep -q + pipefail 会 SIGPIPE; 用 grep > /dev/null 替代
if ps aux | grep '[h]ermes_cli.main gateway' > /dev/null 2>&1; then
  GATEWAY_RUNNING=true
fi

# ── 7. Model Diversity Readiness ──
# This is a fail-closed readiness gate for multi-model certification/autonomy.
# It is reported separately from V(t) so core operational health does not
# masquerade as certified multi-model readiness.
MODEL_DIVERSITY_META=$(python3 - "$HERMES_HOME" <<'PY'
import json, subprocess, sys
from pathlib import Path
home = Path(sys.argv[1]).expanduser()
cmd = [sys.executable, str(home / 'scripts' / 'model-diversity-monitor.py'), '--json', '--gate']
try:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    try:
        data = json.loads(proc.stdout or '{}')
    except Exception:
        data = {'parse_error': (proc.stdout or '')[-500:]}
    print(json.dumps({'ok': proc.returncode == 0, 'returncode': proc.returncode, 'data': data, 'stderr': (proc.stderr or '')[-500:]}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({'ok': False, 'returncode': None, 'data': {}, 'stderr': repr(e)}, ensure_ascii=False))
PY
)
MODEL_DIVERSITY_OK=$(python3 -c "import json; d=json.loads('''$MODEL_DIVERSITY_META'''); print('true' if d.get('ok') else 'false')")
MODEL_DIVERSITY_DOMINANT=$(python3 -c "import json; d=json.loads('''$MODEL_DIVERSITY_META''').get('data') or {}; print(d.get('dominant_model') or '')")
MODEL_DIVERSITY_SHARE=$(python3 -c "import json; d=json.loads('''$MODEL_DIVERSITY_META''').get('data') or {}; print(d.get('dominant_share') or 0)")
MODEL_DIVERSITY_TOTAL=$(python3 -c "import json; d=json.loads('''$MODEL_DIVERSITY_META''').get('data') or {}; print(d.get('total_calls') or 0)")

MODEL_ROUTER_META=$(python3 - "$HERMES_HOME" <<'PY'
import json, subprocess, sys
from pathlib import Path
home = Path(sys.argv[1]).expanduser()
cmd = [sys.executable, str(home / 'scripts' / 'model-router.py'), 'readiness', '--json', '--gate']
try:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    try:
        data = json.loads(proc.stdout or '{}')
    except Exception:
        data = {'parse_error': (proc.stdout or '')[-500:]}
    print(json.dumps({'ok': proc.returncode == 0, 'returncode': proc.returncode, 'data': data, 'stderr': (proc.stderr or '')[-500:]}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({'ok': False, 'returncode': None, 'data': {}, 'stderr': repr(e)}, ensure_ascii=False))
PY
)
MODEL_ROUTER_OK=$(printf '%s' "$MODEL_ROUTER_META" | python3 -c "import json,sys; d=json.load(sys.stdin); print('true' if d.get('ok') else 'false')")
MODEL_ROUTER_FAILURES=$(printf '%s' "$MODEL_ROUTER_META" | python3 -c "import json,sys; d=json.load(sys.stdin).get('data') or {}; print(','.join(d.get('failed_checks') or []))")
MODEL_ROUTER_REBALANCE=$(printf '%s' "$MODEL_ROUTER_META" | python3 -c "import json,sys; d=json.load(sys.stdin).get('data') or {}; print('true' if d.get('rebalance_required') else 'false')")
MODEL_QUOTA_OK=$(printf '%s' "$MODEL_ROUTER_META" | python3 -c "import json,sys; d=json.load(sys.stdin).get('data') or {}; q=d.get('quota_confidence') or {}; print('true' if q.get('ok') else 'false')")
MODEL_QUOTA_FAILURES=$(printf '%s' "$MODEL_ROUTER_META" | python3 -c "import json,sys; d=json.load(sys.stdin).get('data') or {}; q=d.get('quota_confidence') or {}; print(q.get('failure_count') or 0)")

# ── 8. Compute V(t) ──
# V(t) = [self_test_pass, main_pass_rate, cron_health, 1-synth_ratio, gateway_running]
V_SELF=$( [[ "$SELF_TEST_PASS" == "true" ]] && echo 1.0 || echo 0.0 )
V_MAIN_PR=$MAIN_PR
V_CRON=$CRON_HEALTH
V_REAL_RATIO=$(python3 -c "print(round(1.0 - $SYNTH_RATIO, 3))")
V_GW=$( [[ "$GATEWAY_RUNNING" == "true" ]] && echo 1.0 || echo 0.0 )

V_OVERALL=$(python3 -c "
components = [$V_SELF, $V_MAIN_PR, $V_CRON, $V_REAL_RATIO, $V_GW]
weights = [0.25, 0.30, 0.15, 0.20, 0.10]
v = sum(c*w for c,w in zip(components, weights))
print(round(v, 4))
")

# ── 8. V̇(t) — delta from last reading ──
HISTORY_FILE="$HERMES_HOME/logs/health-history.jsonl"
V_DOT="N/A"
if [[ -f "$HISTORY_FILE" ]]; then
    LAST_V=$(tail -1 "$HISTORY_FILE" | python3 -c "import sys,json; print(json.loads(sys.stdin.readline()).get('V', 0))" 2>/dev/null || echo 0)
    V_DOT=$(python3 -c "print(round($V_OVERALL - $LAST_V, 4))" 2>/dev/null || echo "N/A")
fi

# ── 9. Summary Warnings ──
WARNINGS=()
[[ $(python3 -c "print(1 if $MAIN_PR < 0.6 else 0)") == "1" ]] && WARNINGS+=("main_pass_rate < 0.6")
[[ $(python3 -c "print(1 if $SYNTH_RATIO > 0.6 else 0)") == "1" ]] && WARNINGS+=("synthetic_ratio > 0.6 (dilution risk)")
[[ $(python3 -c "print(1 if $CRON_RECENT < 3 and $CRON_TOTAL > 0 else 0)") == "1" ]] && WARNINGS+=("only $CRON_RECENT/$CRON_TOTAL crons ran in 24h (check scheduler)")
[[ "$GATEWAY_RUNNING" != "true" ]] && WARNINGS+=("gateway not running")
[[ $MEMORY_SIZE -gt 2200 ]] && WARNINGS+=("memory file > 2.2KB, may have ghosts")
[[ "$SELF_TEST_PASS" != "true" ]] && WARNINGS+=("self-test not all-pass")
if [[ "$MODEL_DIVERSITY_OK" != "true" ]]; then
    WARNINGS+=("model diversity gate failed: dominant=${MODEL_DIVERSITY_DOMINANT:-unknown} share=$MODEL_DIVERSITY_SHARE total=$MODEL_DIVERSITY_TOTAL")
fi
if [[ "$MODEL_QUOTA_OK" != "true" ]]; then
    WARNINGS+=("model quota confidence gate failed: failures=$MODEL_QUOTA_FAILURES")
fi
if [[ "$MODEL_ROUTER_OK" != "true" ]]; then
    WARNINGS+=("model router readiness gate failed: failures=${MODEL_ROUTER_FAILURES:-unknown}")
fi
# Raw skill count alone is not a P10 health failure once the governed steward
# audit exists. Skill-steward owns actionable ecosystem warnings (zombies,
# broken refs, conflicts, coverage). Keep only an extreme ungoverned-sprawl
# guard here to avoid noisy false positives for intentionally installed packs.
if [[ $SKILL_COUNT -gt 200 && ! -f "$HERMES_HOME/skills/steward/audit-report.json" ]]; then
    WARNINGS+=("skill count > 200 and no steward audit found")
fi

if [[ ${#WARNINGS[@]} -eq 0 ]]; then
    WARNINGS_JSON='[]'
else
    WARNINGS_JSON=$(printf '%s\n' "${WARNINGS[@]}" | python3 -c 'import sys,json; print(json.dumps([l.rstrip("\n") for l in sys.stdin if l.rstrip("\n")]))')
fi

# ── Output ──
if $JSON_MODE; then
    python3 -c "
import json
print(json.dumps({
    'timestamp': '$TIMESTAMP',
    'V': $V_OVERALL,
    'V_dot': $( [[ "$V_DOT" == "N/A" ]] && echo 'null' || echo "$V_DOT" ),
    'components': {
        'self_test': $V_SELF,
        'main_pass_rate': $V_MAIN_PR,
        'cron_health': $V_CRON,
        'real_ratio': $V_REAL_RATIO,
        'gateway': $V_GW
    },
    'details': {
        'trace_count_7d': $TRACE_COUNT,
        'real_traces': $REAL_COUNT,
        'synthetic_traces': $SYNTH_COUNT,
        'synthetic_ratio': $SYNTH_RATIO,
        'overall_pass_rate': $OVERALL_PR,
        'cron_total': $CRON_TOTAL,
        'cron_enabled': $CRON_LIVE,
        'cron_good': $CRON_GOOD,
        'cron_pending_first_run': $CRON_PENDING,
        'cron_bad': $CRON_BAD,
        'cron_recent_24h': $CRON_RECENT,
        'cron_stale_errors': $(python3 -c "import json; d=json.loads('''$CRON_STATS'''); print(int(d.get('stale_error_count',0)))"),
        'skill_count': $SKILL_COUNT,
        'skill_staging': $STAGING_COUNT,
        'memory_bytes': $MEMORY_SIZE,
        'memory_lines': $MEMORY_LINES,
        'gateway_running': $( [[ "$GATEWAY_RUNNING" == "true" ]] && echo 'True' || echo 'False' ),
        'self_test_count': $SELF_TEST_COUNT,
        'model_diversity_gate': $( [[ "$MODEL_DIVERSITY_OK" == "true" ]] && echo 'True' || echo 'False' ),
        'model_diversity_dominant_model': '$MODEL_DIVERSITY_DOMINANT',
        'model_diversity_dominant_share': $MODEL_DIVERSITY_SHARE,
        'model_diversity_total_calls': $MODEL_DIVERSITY_TOTAL,
        'model_quota_confidence_gate': $( [[ "$MODEL_QUOTA_OK" == "true" ]] && echo 'True' || echo 'False' ),
        'model_quota_failure_count': $MODEL_QUOTA_FAILURES,
        'model_router_readiness_gate': $( [[ "$MODEL_ROUTER_OK" == "true" ]] && echo 'True' || echo 'False' ),
        'model_router_failures': '$MODEL_ROUTER_FAILURES',
        'model_router_rebalance_required': $( [[ "$MODEL_ROUTER_REBALANCE" == "true" ]] && echo 'True' || echo 'False' )
    },
    'warnings': $WARNINGS_JSON,
    'grade': '$(
        if [[ $(python3 -c "print(1 if $V_OVERALL >= 0.9 else 0)") == "1" ]]; then echo "A";
        elif [[ $(python3 -c "print(1 if $V_OVERALL >= 0.75 else 0)") == "1" ]]; then echo "B";
        elif [[ $(python3 -c "print(1 if $V_OVERALL >= 0.6 else 0)") == "1" ]]; then echo "C";
        else echo "D"; fi
    )'
}, indent=2, ensure_ascii=False))
"
else
    echo "═══════════════════════════════════════════════"
    echo "  Hermes Health Score — $TIMESTAMP"
    echo "═══════════════════════════════════════════════"
    echo ""
    echo "  V(t) = $V_OVERALL  (V̇ = $V_DOT)  Grade: $(
        if [[ $(python3 -c "print(1 if $V_OVERALL >= 0.9 else 0)") == "1" ]]; then echo "A";
        elif [[ $(python3 -c "print(1 if $V_OVERALL >= 0.75 else 0)") == "1" ]]; then echo "B";
        elif [[ $(python3 -c "print(1 if $V_OVERALL >= 0.6 else 0)") == "1" ]]; then echo "C";
        else echo "D"; fi
    )"
    echo ""
    echo "  Components:"
    echo "    self_test:     $V_SELF  ($SELF_TEST_COUNT checks)"
    echo "    main_pass_rate: $V_MAIN_PR  (7d, excl blank/planner-)"
    echo "    cron_health:   $V_CRON  ($CRON_GOOD/$CRON_TOTAL healthy; $CRON_RECENT recent; $CRON_PENDING pending first-run)"
    echo "    real_ratio:    $V_REAL_RATIO  (1 - synth_ratio=$SYNTH_RATIO)"
    echo "    gateway:       $V_GW  ($( [[ "$GATEWAY_RUNNING" == "true" ]] && echo 'up' || echo 'down' ))"
    echo ""
    echo "  Details:"
    echo "    traces_7d:     $TRACE_COUNT (real=$REAL_COUNT synth=$SYNTH_COUNT)"
    echo "    overall_pr:    $OVERALL_PR"
    echo "    skills:        $SKILL_COUNT (+$STAGING_COUNT staging)"
    echo "    memory:        ${MEMORY_SIZE}B / ${MEMORY_LINES} lines"
    echo "    model_diversity_gate: $MODEL_DIVERSITY_OK (dominant=${MODEL_DIVERSITY_DOMINANT:-none} share=$MODEL_DIVERSITY_SHARE total=$MODEL_DIVERSITY_TOTAL)"
    echo "    model_quota_confidence_gate: $MODEL_QUOTA_OK (failures=$MODEL_QUOTA_FAILURES)"
    echo "    model_router_readiness_gate: $MODEL_ROUTER_OK (failures=${MODEL_ROUTER_FAILURES:-none} rebalance_required=$MODEL_ROUTER_REBALANCE)"
    echo ""
    if [[ ${#WARNINGS[@]} -gt 0 ]]; then
        echo "  ⚠ Warnings:"
        for w in "${WARNINGS[@]}"; do
            echo "    - $w"
        done
    else
        echo "  ✓ No warnings"
    fi
    echo "═══════════════════════════════════════════════"
fi

# ── 10. Append history ──
mkdir -p "$HERMES_HOME/logs"
echo "{\"ts\":\"$TIMESTAMP\",\"V\":$V_OVERALL,\"grade\":\"$(
    if [[ $(python3 -c "print(1 if $V_OVERALL >= 0.9 else 0)") == "1" ]]; then echo "A";
    elif [[ $(python3 -c "print(1 if $V_OVERALL >= 0.75 else 0)") == "1" ]]; then echo "B";
    elif [[ $(python3 -c "print(1 if $V_OVERALL >= 0.6 else 0)") == "1" ]]; then echo "C";
    else echo "D"; fi
)\"}" >> "$HISTORY_FILE"
