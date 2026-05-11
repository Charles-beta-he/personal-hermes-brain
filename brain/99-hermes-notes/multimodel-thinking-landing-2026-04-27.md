# 多模型思考落地报告 — 2026-04-27

## 结论

PASS。多模型思考已从“配置/框架层”推进到“真实 adapter fan-out 层”。

本轮把 T1 多脑从 shadow/伪多模型切到真实调用：

- gpt-5.5 → provider=openai-codex → hermes-chat adapter
- mimo-v2.5-pro → provider=xiaomi → hermes-chat adapter
- Claude 模型路径保留 claude-cli adapter
- 离线/不可用场景保留 HERMES_MULTI_BRAIN_OFFLINE=1 shadow fallback

## 改动文件

1. /Users/charles/.hermes/config/quorum.yaml
   - multi_brain.enabled=true
   - phase=1
   - shadow_mode=false
   - adapter_mode=actual
   - T1 planners=[gpt-5.5, mimo-v2.5-pro]
   - T2 planners=[gpt-5.5, mimo-v2.5-pro, claude-opus-4-7, deepseek-v4-pro]
   - T3 planners=[claude-opus-4-7, gpt-5.5, deepseek-v4-pro, mimo-v2.5-pro]

2. /Users/charles/.hermes/scripts/consult_models.py
   - 新增 provider 解析：从 config.yaml pricing.models 读取 model→provider。
   - 新增 extract_plan_json：兼容 raw JSON、Claude wrapper、fenced JSON、Hermes session_id 前缀输出。
   - 新增 call_planner_model：按模型选择真实 adapter。
   - 非 shadow 模式不再用 Claude 冒充所有 planner；改为每个 planner 真实调用自己的 provider。
   - adapter 失败时写低置信 fallback plan，并在 protocol event 中记录 ok/adapter/provider/latency/error。

3. /Users/charles/.hermes/scripts/ensemble-vote.py
   - execute=True 模式改为 provider-aware 调用。
   - 从 pricing.models 解析 provider，并传 hermes chat --provider。
   - JSON verdict 解析兼容 Hermes stdout 中的 session_id/警告前缀。
   - model_results 中记录 provider 与 adapter。

4. /Users/charles/.hermes/scripts/cross-patch.py
   - 明确标注 execution_mode=orchestration_framework。
   - 明确 actual_model_calls=false。
   - 避免把“producer/reviewer delegate_task 编排说明”误判为“脚本内已实际双模型调用”。

5. /Users/charles/.hermes/skills/software-development/multi-model-architecture/SKILL.md
   - 更新 consult_models 真多模型落地规则。
   - 更新 ensemble-vote provider-aware 调用规则。
   - 更新 cross-patch 当前真实边界。

## 验证结果

### 1. 静态验证

通过：

- py_compile:
  - consult_models.py
  - ensemble-vote.py
  - cross-patch.py
  - consensus-plans.py
  - agent_protocol.py
- YAML parse:
  - config.yaml
  - config/quorum.yaml

### 2. consult_models T1 真实多模型 fan-out

命令：

python3 /Users/charles/.hermes/scripts/consult_models.py run /tmp/hermes-mm-landing-state.json --tier T1 --keep --timeout 90

结果：

- planners=['gpt-5.5', 'mimo-v2.5-pro']
- gpt-5.5 plan:
  - provider=openai-codex
  - adapter=hermes-chat
  - latency_ms=31069
  - valid Plan Schema v1
- mimo-v2.5-pro plan:
  - provider=xiaomi
  - adapter=hermes-chat
  - latency_ms=42254
  - valid Plan Schema v1
- merged_plan:
  - planner_model=ensemble:2
  - source_plans=2
  - consensus_verdict=weak_consensus

Artifacts:

- /Users/charles/.hermes/tick-20260427-123837/plans/gpt-5.5.json
- /Users/charles/.hermes/tick-20260427-123837/plans/mimo-v2.5-pro.json
- /Users/charles/.hermes/tick-20260427-123837/merged_plan.json

### 3. ensemble-vote 真实 provider-aware 调用

命令：

python3 /Users/charles/.hermes/scripts/ensemble-vote.py vote --task 'Smoke: answer pass if multi-provider ensemble can call both models.' --models gpt-5.5,mimo-v2.5-pro --strategy majority --execute

结果：

- gpt-5.5:
  - provider=openai-codex
  - adapter=hermes-chat
  - exit_code=0
- mimo-v2.5-pro:
  - provider=xiaomi
  - adapter=hermes-chat
  - exit_code=0

说明：该 smoke 的两个模型 verdict 不一致，consensus=false；但本次验收目标是“是否真实调用多 provider”，该项已满足。

### 4. cross-patch 边界验证

命令：

python3 /Users/charles/.hermes/scripts/cross-patch.py execute --task 'Smoke: verify cross-patch honest orchestration mode' --workdir /tmp

结果：

- execution_mode=orchestration_framework
- actual_model_calls=false
- agent_protocol.task_id=cross-patch-20260427-124056

结论：cross-patch 目前是 L2 编排/协议层，不是脚本内直接执行 producer/reviewer。这个边界已显式化。

### 5. Hermes self-test

通过：24/24 passed。

### 6. P10 health

通过：

- V=0.967
- Grade=A
- warnings=2

## 当前真实状态

- consult_models.py：已真实多模型 fan-out。
- ensemble-vote.py：execute=True 已真实多 provider 调用。
- cross-patch.py：仍是 orchestration framework，但已诚实标注 actual_model_calls=false。
- DeepSeek：当前 OpenRouter API key 不可用，因此没有放在 T1 必选；保留在 T2/T3，待 provider 可用后可升回 T1 reviewer。

## 后续建议

1. 为 consult_models.py 增加单元测试，覆盖：
   - extract_plan_json(raw JSON)
   - extract_plan_json(Hermes session_id + JSON)
   - extract_plan_json(Claude wrapper + fenced JSON)
   - offline fallback

2. 为 ensemble-vote.py 增加单元测试，覆盖：
   - model_provider(gpt-5.5)=openai-codex
   - model_provider(mimo-v2.5-pro)=xiaomi
   - stdout prefix JSON extraction

3. 如果要把 cross-patch 也改成脚本内真实调用，需要新增 producer/reviewer execution adapter；否则保持目前“由 Hermes agent/delegate_task 执行”的编排边界。
