#!/usr/bin/env bash
# canary-evaluator.sh — L5 灰度评估 (24h 后比对 canary vs stable)
# 每小时跑一次, 但只处理 canary-active.txt 中有记录的 skill
#
# canary 的 skill 在 canary-active.txt 中:
#   skill_name 启用时间(unix_ts)  描述
# 如:
#   router 1745712000 "自进化管线router skill v2"
#
# 24h 后自动决定: pass_rate 不降 → promote; 下降 → rollback
set -euo pipefail

CANARY_FILE=~/.hermes/canary-active.txt
EVOLVE_LOG=~/.hermes/logs/evolve.log
NOW=$(date +%s)
mkdir -p "$(dirname "$CANARY_FILE")"
touch "$CANARY_FILE"

evaluate_canary() {
    local skill="$1" started_at="$2" desc="$3"
    local age=$(( (NOW - started_at) / 3600 ))
    echo "[canary] $skill: age=${age}h (needs 24h)" >&2
    [ "$age" -lt 24 ] && return 0  # 没到 24h, 跳过

    # 取 canary 版本的 pass_rate (sklls-staging 或 canary 分支)
    local canary_pr=0 stable_pr=0

    # 稳定版: 从 route_outcomes 取 7d 该 skill 的 pass_rate
    stable_pr=$(python3 ~/.hermes/scripts/route_store.py stats \
        --skill "$skill" --hours 168 2>/dev/null | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('main_pass_rate', d.get('views',{}).get('main',{}).get('pass_rate', d.get('pass_rate', 0))))" 2>/dev/null || echo 0)

    # 灰度版: 从 canary 标记的 outcomes 取 (有 canary=true 字段)
    # 当前 route_outcomes 没有 canary 标记, 用最近 24h 该 skill 的数据近似
    canary_pr=$(python3 ~/.hermes/scripts/route_store.py stats \
        --skill "$skill" --hours 24 2>/dev/null | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('main_pass_rate', d.get('views',{}).get('main',{}).get('pass_rate', d.get('pass_rate', 0))))" 2>/dev/null || echo 0)

    echo "[canary] $skill: stable=$stable_pr canary=$canary_pr" >&2

    # 决策
    local delta
    delta=$(python3 -c "print($canary_pr - $stable_pr)" 2>/dev/null || echo 0)

    if python3 -c "exit(0 if float('$delta') < -0.05 else 1)" 2>/dev/null; then
        # 回滚
        echo "[canary] ⛔ $skill canary regressed (delta=$delta). Rolling back."
        local staging="$HOME/.hermes/skills-staging/$skill"
        rm -rf "$staging" 2>/dev/null
        # 清除 canary 配置
        hermes config set "skills.$skill.canary_ratio" 0.0 2>/dev/null || true
        # 从 canary-active 移除
        grep -v "^$skill " "$CANARY_FILE" > /tmp/canary.tmp
        mv /tmp/canary.tmp "$CANARY_FILE"

        local entry="{\"ts\":\"$(date -u +%FT%TZ)\",\"event\":\"canary_reject\",\"skill\":\"$skill\",\"desc\":\"$desc\",\"reason\":\"regression\",\"delta\":$delta}"
        echo "$entry" >> "$EVOLVE_LOG"
    elif python3 -c "exit(0 if float('$delta') >= 0 else 1)" 2>/dev/null; then
        # 100% rollout
        echo "[canary] ✅ $skill canary passes (delta=$delta). Promoting to 100%."
        hermes config set "skills.$skill.canary_ratio" 1.0 2>/dev/null || true
        # 从 staging promote 到 production
        local staging="$HOME/.hermes/skills-staging/$skill"
        local prod
        prod=$(find "$HOME/.hermes/skills" -name "SKILL.md" -path "*/$skill/*" 2>/dev/null)
        if [ -n "$prod" ] && [ -d "$staging" ]; then
            cp "$staging/SKILL.md" "$prod"
            rm -rf "$staging"
        fi
        # 从 canary-active 移除
        grep -v "^$skill " "$CANARY_FILE" > /tmp/canary.tmp
        mv /tmp/canary.tmp "$CANARY_FILE"

        local entry="{\"ts\":\"$(date -u +%FT%TZ)\",\"event\":\"canary_promote\",\"skill\":\"$skill\",\"desc\":\"$desc\",\"delta\":$delta}"
        echo "$entry" >> "$EVOLVE_LOG"
    else
        echo "[canary] ⏸️  $skill: delta=$delta, within threshold. Keeping canary 24h more."
    fi
}

main() {
    if [ ! -s "$CANARY_FILE" ]; then
        echo "[canary] No active canaries."
        exit 0
    fi

    local changes=0
    while IFS=' ' read -r skill started desc; do
        [ -z "$skill" ] && continue
        evaluate_canary "$skill" "$started" "$desc"
        changes=1
    done < "$CANARY_FILE"

    [ "$changes" -eq 0 ] && echo "[canary] No active canaries (empty file)."
}

main
