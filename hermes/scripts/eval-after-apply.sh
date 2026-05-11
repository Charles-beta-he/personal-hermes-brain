#!/usr/bin/env bash
# eval-after-apply.sh — Eval Gate + 自动回滚
#
# Usage: eval-after-apply.sh [--baseline PASS_RATE] [--threshold 0.05]
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
EVOLVE_LOG=~/.hermes/logs/evolve.log
THRESHOLD=${THRESHOLD:-0.05}
DEGRADED_FILE="/tmp/hermes-plan.degraded"

echo "[eval] Eval Gate — baseline comparison"

extract_main_pass_rate() {
    python3 ~/.hermes/scripts/route_store.py stats --hours "$1" 2>/dev/null | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('main_pass_rate', d.get('views',{}).get('main',{}).get('pass_rate', d.get('pass_rate', 0))))" 2>/dev/null || echo "0"
}

# 获取 baseline (7天前)
BASELINE=$(extract_main_pass_rate 168)
echo "[eval] Baseline (7d main window): pass_rate=$BASELINE"

# 如果是 degraded 模式, 跳过 eval
if [ -f "$DEGRADED_FILE" ]; then
    echo "[eval] DEGRADED mode — skipping eval gate, keeping changes"
    echo '[eval] Result: KEPT (degraded)'
    # 更新 evolve.log
    if [ -f "$EVOLVE_LOG" ]; then
        LAST_LINE=$(tail -1 "$EVOLVE_LOG")
        python3 -c "
import json
entry = json.loads('$LAST_LINE')
entry['eval_result'] = 'kept_degraded'
entry['baseline'] = $BASELINE
entry['delta'] = 0
print(json.dumps(entry))
" > /tmp/evolve_last.json 2>/dev/null || true
        # 替换最后一行
        sed '$d' "$EVOLVE_LOG" > /tmp/evolve_log.tmp 2>/dev/null
        cat /tmp/evolve_last.json >> /tmp/evolve_log.tmp
        mv /tmp/evolve_log.tmp "$EVOLVE_LOG"
    fi
    exit 0
fi

# 跑回归集 (85条 baseline)
echo "[eval] Running regression suite..."
python3 "$HERE/eval-harness.py" --evaluate "current_production" > /tmp/eval_result.json 2>&1 || true

# 获取新 pass_rate (1h窗口, apply 后的短期指标)
sleep 2
NEW=$(extract_main_pass_rate 1)
echo "[eval] New (1h main window): pass_rate=$NEW"

# 计算 delta
DELTA=$(python3 -c "print($NEW - $BASELINE)" 2>/dev/null || echo "0")
echo "[eval] Delta: ${DELTA} (threshold: -${THRESHOLD})"

# 判断
REJECT=false
KEEP=false

if python3 -c "import sys; exit(0 if float('$DELTA') < -float('$THRESHOLD') else 1)" 2>/dev/null; then
    echo "[eval] ⛔ REGRESSION detected (delta < -$THRESHOLD)"
    REJECT=true
else
    echo "[eval] ✅ Pass — no significant regression"
    KEEP=true
fi

# 回滚或保留
if [ "$REJECT" = "true" ]; then
    SNAP=$(cat /tmp/hermes-last-snapshot 2>/dev/null || echo "")
    if [ -n "$SNAP" ]; then
        echo "[eval] Rolling back to $SNAP..."
        # 恢复 config.yaml
        if [ -f "$SNAP/config.yaml.bak" ]; then
            cp "$SNAP/config.yaml.bak" ~/.hermes/config.yaml
            echo "[eval]   config.yaml restored"
        fi
        # 恢复 cron/jobs.json
        if [ -f "$SNAP/cron.json.bak" ]; then
            cp "$SNAP/cron.json.bak" ~/.hermes/cron/jobs.json
            echo "[eval]   cron/jobs.json restored"
        fi
        # 恢复 skill 文件
        for bak in "$SNAP"/skill-*.bak; do
            [ -e "$bak" ] || continue
            skill_name=$(basename "$bak" | sed 's/skill-\(.*\)\.bak/\1/')
            target=$(find ~/.hermes/skills -name "SKILL.md" -path "*/$skill_name/*" 2>/dev/null)
            if [ -n "$target" ]; then
                cp "$bak" "$target"
                echo "[eval]   skill/$skill_name restored"
            fi
        done
        echo "[eval] Rollback complete (from $SNAP)"
    else
        echo "[eval] No snapshot found — manual rollback required!"
    fi
    RESULT="rolled_back"
elif [ "$KEEP" = "true" ]; then
    RESULT="kept"
fi

echo "[eval] Result: $RESULT"

# 更新 evolve.log
if [ -f "$EVOLVE_LOG" ]; then
    LAST_LINE=$(tail -1 "$EVOLVE_LOG")
    python3 -c "
import json
entry = json.loads('$LAST_LINE')
entry['eval_result'] = '$RESULT'
entry['baseline'] = $BASELINE
entry['new'] = $NEW
entry['delta'] = $DELTA
print(json.dumps(entry))
" > /tmp/evolve_last.json 2>/dev/null || true
    sed '$d' "$EVOLVE_LOG" > /tmp/evolve_log.tmp 2>/dev/null
    cat /tmp/evolve_last.json >> /tmp/evolve_log.tmp
    mv /tmp/evolve_log.tmp "$EVOLVE_LOG"
fi

# 3 连败告警
if [ "$REJECT" = "true" ]; then
    CONSECUTIVE=$(tail -10 "$EVOLVE_LOG" | python3 -c "
import sys, json
count = 0
for line in sys.stdin:
    try:
        e = json.loads(line)
        if e.get('eval_result') == 'rolled_back':
            count += 1
        else:
            count = 0
    except:
        pass
print(count)
" 2>/dev/null || echo "0")
    if [ "$CONSECUTIVE" -ge 3 ]; then
        echo "[eval] ⚠️  3 consecutive rollbacks — system degraded. Pausing evolve cron."
        echo "[eval] Human intervention required."

        # 实际暂停 cron — 找双脑进化 cron 的 job_id 并 pause
        EVOLVE_JID=$(hermes cron list --json 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, dict):
        for jid, j in data.items():
            if '双脑' in j.get('name', '') or 'self-evolve' in j.get('name', '').lower():
                print(jid)
    elif isinstance(data, list):
        for j in data:
            if '双脑' in j.get('name', '') or 'self-evolve' in j.get('name', '').lower():
                print(j.get('job_id', ''))
except:
    pass
" 2>/dev/null || echo "")

        if [ -n "$EVOLVE_JID" ]; then
            hermes cron pause "$EVOLVE_JID" 2>/dev/null || true
            echo "[eval] Cron $EVOLVE_JID paused."
            # 写 evolve.log
            python3 -c "
import json
entry = {
    'ts': '$(date -u +%FT%TZ)',
    'event': 'cron_paused',
    'reason': '3 consecutive rollbacks',
    'cron_job_id': '$EVOLVE_JID',
    'note': 'Human review required before resume'
}
log = open('$EVOLVE_LOG', 'a')
log.write(json.dumps(entry) + chr(10))
" 2>/dev/null || true
        else
            echo "[eval] WARN: Could not find evolve cron job_id to pause."
            echo "[eval] Manual: hermes cron list → find 双脑 job_id → hermes cron pause <id>"
        fi
    fi
fi

echo "[eval] Done."
