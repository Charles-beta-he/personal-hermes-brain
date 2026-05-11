#!/usr/bin/env bash
# consult-claude.sh — 咨询 Claude Code 出 plan (Patches 1+2)
# Patch 1: Claude Code 不可用 → 降级到 self-improvement-pipeline.py
# Patch 2: Schema 不合规 → retry-with-feedback (2次)
#
# Usage: consult-claude.sh [--dry-run]
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
STATE_FILE=$($HERE/self-describe.sh)
DEGRADED_FILE="/tmp/hermes-plan.degraded"
PLAN_FILE="/tmp/hermes-plan.json"
rm -f "$DEGRADED_FILE"

# ── Schema 校验函数 ──

validate_plan_schema() {
    local f="$1"
    jq -e '.steps' "$f" >/dev/null 2>&1 || return 1
    jq -e '.steps | length > 0' "$f" >/dev/null 2>&1 || return 1
    # 检查每一步有必需字段
    jq -e '.steps | all(
        .op and .args and has("expected_gain") and
        has("risk") and has("reversible")
    )' "$f" >/dev/null 2>&1 || return 1
    # 检查 op 合法
    jq -e '.steps | all(.op | IN(
        "cron_add","cron_remove","skill_install","skill_edit",
        "hook_add","mcp_add","config_set"
    ))' "$f" >/dev/null 2>&1 || return 1
    # 拒绝不可逆操作
    jq -e '.steps | all(.reversible == true)' "$f" >/dev/null 2>&1 || return 1
    # 检查 risk 全 ≤ med
    jq -e '.steps | all(.risk | IN("low","med"))' "$f" >/dev/null 2>&1 || return 1
    # 步骤数 ≤ 5
    jq -e '.steps | length <= 5' "$f" >/dev/null 2>&1 || return 1
    return 0
}

# 收集 schema 错误详情
schema_errors() {
    local f="$1" msgs=""
    jq -e '.steps' "$f" >/dev/null 2>&1 || msgs+="- missing 'steps' array\n"
    jq -e '.steps | length > 0' "$f" >/dev/null 2>&1 || msgs+="- empty steps\n"
    jq -e '.steps | all(.op and .args and has("expected_gain") and has("risk") and has("reversible"))' "$f" >/dev/null 2>&1 || \
        msgs+="- steps missing required fields (op/args/expected_gain/risk/reversible)\n"
    jq -e '.steps | all(.op | IN("cron_add","cron_remove","skill_install","skill_edit","hook_add","mcp_add","config_set"))' "$f" >/dev/null 2>&1 || \
        msgs+="- invalid op in one or more steps\n"
    jq -e '.steps | all(.reversible == true)' "$f" >/dev/null 2>&1 || \
        msgs+="- one or more steps has reversible!=true\n"
    jq -e '.steps | all(.risk | IN("low","med"))' "$f" >/dev/null 2>&1 || \
        msgs+="- one or more steps has risk=high\n"
    jq -e '.steps | length <= 5' "$f" >/dev/null 2>&1 || \
        msgs+="- more than 5 steps\n"
    echo -e "$msgs"
}

# ── 构建 Prompt ──

PROMPT_FILE=$(mktemp)
trap 'rm -f "$PROMPT_FILE"' EXIT

cat > "$PROMPT_FILE" << 'PROMPT_HEADER'
你是 Hermes 的架构师 (Claude Code 化身)。
读下面 state.json, 输出 JSON plan 改进 Hermes。

要求:
1. 仅输出 JSON, 不要解释, 不要 markdown 围栏, 不要前后任何文本。
2. plan schema:
{
  "diagnosis": "1-2 句最严重问题",
  "steps": [
    {
      "op": "cron_add|cron_remove|skill_install|skill_edit|hook_add|mcp_add|config_set",
      "args": {ARGS SCHEMA},
      "expected_gain": "...",
      "risk": "low|med|high",
      "reversible": true
    }
  ],
  "eval_targets": ["回归集名称"],
  "stop_if": "什么情况下放弃这次改动"
}
3. 改动总数 ≤ 5 (一次大改易回归)
4. 拒绝触动 safety-guard, auth, memory schema (锁死)
5. 倾向可回滚 (canary > rollout)
6. 所有 step.risk 必须 ≤ med
7. 所有 step.reversible 必须 = true

==== args schema (严格遵守, 不符则该 step 被 apply-plan.sh 跳过) ====

cron_add:
  {"name":"string","schedule":"0 3 * * *","prompt":"string"}
cron_remove:
  {"name":"string"}
skill_install:
  {"name":"string","url":"string(可选)"}
skill_edit:
  {"name":"string","content":"完整新内容(整段替换SKILL.md, 不是diff)"}
hook_add:
  {"trigger":"post_tool_call","command":"shell命令路径","matcher":"文件匹配正则","timeout":5}
mcp_add:
  {"name":"string","command":"python3|npx","args":"string","timeout":30}
config_set:
  {"key":"dot.path.to.key","value":"标量值"}

==== 不变量 (绝不触动) ====
- safety-guard / auth / memory schema
- self-evolve-via-claude skill 自身
- evolve.log / 任何 backup/snapshot 路径
- self-evolve cron 自身定义

State (summary mode):
PROMPT_HEADER

cat "$STATE_FILE" >> "$PROMPT_FILE"

# ── 主流程: retry-with-feedback ──

SUCCESS=false

for attempt in 1 2 3; do
    echo "[consult] Attempt $attempt/3" >&2

    # 调 Claude Code
    if claude -p \
        --dangerously-skip-permissions \
        --output-format json \
        < "$PROMPT_FILE" \
        > "$PLAN_FILE" 2>/dev/null; then

        # 提取 Claude Code output 中的 JSON plan
        EXTRACTED=$(mktemp)
        python3 "$HERE/_extract_plan_json.py" "$PLAN_FILE" "$EXTRACTED" 2>/dev/null || true

        if [ -s "$EXTRACTED" ]; then
            mv "$EXTRACTED" "$PLAN_FILE"
        else
            rm -f "$EXTRACTED"
        fi

        # 校验 schema
        if validate_plan_schema "$PLAN_FILE"; then
            SUCCESS=true
            break
        fi

        # Schema 失败 — 收集错误注入 feedback
        ERRORS=$(schema_errors "$PLAN_FILE")
        echo "[consult] Attempt $attempt schema errors:" >&2
        echo "$ERRORS" >&2

        if [ $attempt -lt 3 ]; then
            # 注入 feedback 到 prompt 尾部
            echo "" >> "$PROMPT_FILE"
            echo "---" >> "$PROMPT_FILE"
            echo "FEEDBACK from previous attempt $attempt:" >> "$PROMPT_FILE"
            echo "$ERRORS" >> "$PROMPT_FILE"
            echo "Re-output JSON plan. Fix ALL of the above errors." >> "$PROMPT_FILE"
        fi
    else
        echo "[consult] claude -p failed (attempt $attempt)" >&2
    fi
done

# ── Patch 1: 降级路径 ──

if [ "$SUCCESS" != "true" ]; then
    echo "[consult] All 3 attempts failed. Falling back to local planner." >&2
    echo '{"degraded": true}' > "$DEGRADED_FILE"

    # 调用本地 self-improvement-pipeline.py
    python3 "$HERE/self-improvement-pipeline.py" --write --auto-exec > /tmp/plan_local.txt 2>&1 || true

    # 从 action plan 转成统一 plan schema
    PLAN_FILE="/tmp/hermes-plan.json"
    cat > "$PLAN_FILE" << PLANFALLBACK
{
  "diagnosis": "Claude Code unavailable — using local planner (degraded mode)",
  "degraded": true,
  "steps": [
    {
      "op": "cron_add",
      "args": {},
      "expected_gain": "Local planner fallback — see self-improvement-pipeline.py output",
      "risk": "low",
      "reversible": true
    }
  ],
  "eval_targets": ["auto"],
  "stop_if": "No local plan available"
}
PLANFALLBACK
fi

echo "$PLAN_FILE"
