#!/usr/bin/env bash
# apply-plan.sh — 落地执行 (Patch 4: drain 阶段)
# 先 drain 正在跑的 task → backup → apply → 恢复
#
# Usage: apply-plan.sh [--dry-run] [plan.json]
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PLAN="${1:-/tmp/hermes-plan.json}"
DRY_RUN=${DRY_RUN:-0}
SNAPSHOT_DIR=~/.hermes/snapshots
SNAPSHOT="$SNAPSHOT_DIR/pre_$(date +%s)"
EVOLVE_LOG=~/.hermes/logs/evolve.log
DEGRADED_FILE="/tmp/hermes-plan.degraded"
mkdir -p "$SNAPSHOT_DIR" ~/.hermes/logs

# ── Patch 4: Drain 阶段 (拒收新 task) ──

drain_inflight() {
    local max_wait=600 waited=0

    # 检查是否有 scheduler 配置
    if hermes config get scheduler.accept_new >/dev/null 2>&1; then
        echo "[apply] Draining: pausing new task acceptance..."
        hermes config set scheduler.accept_new false 2>/dev/null || true
    fi

    # 等待 inflight 完成
    while true; do
        local running
        running=$(hermes sessions list --status running --json 2>/dev/null | jq 'length' 2>/dev/null || echo 0)
        if [ "$running" -eq 0 ]; then
            echo "[apply] All in-flight tasks complete."
            break
        fi
        echo "[apply] Waiting... $running in-flight (${waited}s)"
        sleep 5
        waited=$((waited + 5))
        if [ "$waited" -gt "$max_wait" ]; then
            echo "[apply] ABORT: drain timeout after ${max_wait}s"
            hermes config set scheduler.accept_new true 2>/dev/null || true
            return 1
        fi
    done
    return 0
}

# ── Backup ──

take_snapshot() {
    echo "[apply] Snapshot -> $SNAPSHOT"
    mkdir -p "$SNAPSHOT"
    # 备份关键文件
    cp ~/.hermes/config.yaml "$SNAPSHOT/config.yaml.bak" 2>/dev/null || true
    cp ~/.hermes/cron/jobs.json "$SNAPSHOT/cron.json.bak" 2>/dev/null || true
    # 备份 skill 目录 (增量, 只备份被改的)
    if [ -n "${SKILLS_TO_TOUCH:-}" ]; then
        for s in $SKILLS_TO_TOUCH; do
            local src="$HOME/.hermes/skills/$s"
            if [ -d "$src" ]; then
                cp -r "$src" "$SNAPSHOT/skill-$s.bak"
            fi
        done
    fi
    # 全量 backup — hermes backup 不走 -o (不支持自定义路径)
    # 我们用增量文件备份代替, 更快更可靠
    hermes backup -q 2>/dev/null || true
    echo "$SNAPSHOT" > /tmp/hermes-last-snapshot
}

# ── Parse Plan ──

parse_plan() {
    local f="$1"
    # 先尝试提取 ```json 块
    local block
    block=$(sed -n '/```json/,/```/p' "$f" 2>/dev/null)
    if [ -n "$block" ]; then
        echo "$block" | sed '1d;$d' 2>/dev/null
        return
    fi
    # fallback: 直接读文件
    cat "$f"
}

# ── Apply single step ──

apply_step() {
    local op="$1" args="$2"

    case "$op" in
        cron_add)
            local name schedule prompt
            name=$(echo "$args" | jq -r '.name // "evolve"')
            schedule=$(echo "$args" | jq -r '.schedule // "0 3 * * *"')
            prompt=$(echo "$args" | jq -r '.prompt // "/self-evolve"')
            echo "[apply]   hermes cron add --name $name --schedule $schedule"
            if [ "$DRY_RUN" != "1" ]; then
                hermes cron add --name "$name" --schedule "$schedule" --prompt "$prompt" --deliver local 2>/dev/null || true
            fi
            ;;

        cron_remove)
            local name
            name=$(echo "$args" | jq -r '.name // ""')
            echo "[apply]   hermes cron remove $name"
            if [ "$DRY_RUN" != "1" ] && [ -n "$name" ]; then
                # 需要先查 job_id
                local jid
                jid=$(hermes cron list --json 2>/dev/null | jq -r ".[] | select(.name==\"$name\") | .job_id" | head -1)
                [ -n "$jid" ] && hermes cron remove "$jid" 2>/dev/null || true
            fi
            ;;

        skill_install)
            local name url
            name=$(echo "$args" | jq -r '.name // ""')
            url=$(echo "$args" | jq -r '.url // ""')
            echo "[apply]   hermes skills install $name"
            if [ "$DRY_RUN" != "1" ] && [ -n "$name" ]; then
                if [ -n "$url" ]; then
                    hermes skills install "$name" --url "$url" 2>/dev/null || true
                else
                    hermes skills install "$name" 2>/dev/null || true
                fi
            fi
            ;;

        skill_edit)
            # Patch 5 (secondary): 全文件替换 + snapshot, 不用 unix patch
            local name path content
            name=$(echo "$args" | jq -r '.name // ""')
            path=$(echo "$args" | jq -r '.path // ""')
            content=$(echo "$args" | jq -r '.content // ""')
            [ -z "$name" ] && [ -z "$path" ] && { echo "[apply]   skill_edit: no name or path"; return; }

            local target
            if [ -n "$path" ]; then
                target="$HOME/$path"
            else
                target=$(find "$HOME/.hermes/skills" -name "SKILL.md" -path "*/$name/*" 2>/dev/null | head -1)
            fi
            [ -z "$target" ] && { echo "[apply]   skill_edit: target not found"; return; }

            echo "[apply]   skill_edit $name -> $target"
            if [ "$DRY_RUN" != "1" ] && [ -n "$content" ]; then
                # 备份原文件
                cp "$target" "$SNAPSHOT/$name.SKILL.md.bak"
                # 全文件替换
                echo "$content" > "$target"
                echo "[apply]   written $target ($(wc -c < "$target") bytes)"
            fi
            ;;

        hook_add)
            local matcher command
            matcher=$(echo "$args" | jq -r '.matcher // ""')
            command=$(echo "$args" | jq -r '.command // ""')
            echo "[apply]   hook add: $matcher -> $command"
            if [ "$DRY_RUN" != "1" ] && [ -n "$matcher" ] && [ -n "$command" ]; then
                # 追加到 config.yaml hooks
                local hook_entry="  post_tool_call:\n    - matcher: \"$matcher\"\n      command: \"$command\"\n      timeout: 5"
                # 简单追加 (更复杂的用 yq 或 python)
                python3 -c "
import yaml
with open('$HOME/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
hooks = cfg.setdefault('hooks', {})
post = hooks.setdefault('post_tool_call', [])
post.append({'matcher': '$matcher', 'command': '$command', 'timeout': 5})
with open('$HOME/.hermes/config.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False)
" 2>/dev/null || true
            fi
            ;;

        mcp_add)
            local name cmd args_str timeout
            name=$(echo "$args" | jq -r '.name // ""')
            cmd=$(echo "$args" | jq -r '.command // ""')
            args_str=$(echo "$args" | jq -r '.args // ""')
            timeout=$(echo "$args" | jq -r '.timeout // 30')
            echo "[apply]   mcp add: $name -> $cmd"
            if [ "$DRY_RUN" != "1" ] && [ -n "$name" ] && [ -n "$cmd" ]; then
                python3 -c "
import yaml
with open('$HOME/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
servers = cfg.setdefault('mcp_servers', {})
servers['$name'] = {
    'command': '$cmd',
    'args': '${args_str}'.split() if '$args_str' else [],
    'timeout': $timeout
}
with open('$HOME/.hermes/config.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False)
" 2>/dev/null || true
            fi
            ;;

        config_set)
            local key value
            key=$(echo "$args" | jq -r '.key // ""')
            value=$(echo "$args" | jq -r '.value // ""')
            echo "[apply]   hermes config set $key $value"
            if [ "$DRY_RUN" != "1" ] && [ -n "$key" ]; then
                hermes config set "$key" "$value" 2>/dev/null || true
            fi
            ;;

        *)
            echo "[apply]   WARN: unknown op '$op', skip"
            ;;
    esac
}

# ── Main ──

echo "[apply] Plan: $PLAN"
echo "[apply] DRY_RUN=${DRY_RUN}"

# 读取 plan
PLAN_JSON=$(parse_plan "$PLAN")
echo "$PLAN_JSON" | jq -e . >/dev/null 2>&1 || { echo "ERROR: invalid plan JSON"; exit 1; }

# 检查 degraded 标记
HAS_DEGRADED=false
if [ -f "$DEGRADED_FILE" ]; then
    HAS_DEGRADED=true
    echo "[apply] DEGRADED mode — local planner fallback"
fi

# 提取 steps
STEPS=$(echo "$PLAN_JSON" | jq -c '.steps[]' 2>/dev/null)
STEP_COUNT=$(echo "$PLAN_JSON" | jq '.steps | length' 2>/dev/null || echo 0)

# 检查步骤数限制
if [ "$STEP_COUNT" -gt 5 ]; then
    echo "ERROR: Plan has $STEP_COUNT steps, max 5 allowed"
    exit 1
fi

# Patch 4: drain
echo "[apply] Phase 1/4: Draining in-flight tasks..."
drain_inflight || exit 1

# Backup
echo "[apply] Phase 2/4: Taking snapshot..."
take_snapshot

# Apply
echo "[apply] Phase 3/4: Applying $STEP_COUNT step(s)..."
echo "$STEPS" | while read -r step; do
    OP=$(echo "$step" | jq -r '.op')
    ARGS=$(echo "$step" | jq -c '.args // {}')
    echo "[apply]   → $OP"
    apply_step "$OP" "$ARGS"
done

# Resume
echo "[apply] Phase 4/4: Resuming..."
if hermes config get scheduler.accept_new >/dev/null 2>&1; then
    hermes config set scheduler.accept_new true 2>/dev/null || true
fi

echo "[apply] Done. Snapshot at $SNAPSHOT"
echo "$SNAPSHOT" > /tmp/hermes-last-snapshot

# 写 evolve.log
LOG_ENTRY=$(echo "$PLAN_JSON" | jq -c "{ts: \"$(date -u +%FT%TZ)\", degraded: $HAS_DEGRADED, diagnosis: .diagnosis, steps_count: $STEP_COUNT, eval_result: \"pending\"}")
echo "$LOG_ENTRY" >> "$EVOLVE_LOG"
echo "[apply] Logged to $EVOLVE_LOG"
