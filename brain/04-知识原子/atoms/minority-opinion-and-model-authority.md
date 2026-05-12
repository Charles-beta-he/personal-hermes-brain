---
type: atom
layer: L1
status: active
created: 2026-05-06T09:05:08Z
concepts: [multi-model-thinking, minority-opinion, model-authority, issue-ledger, evidence-first]
evidence:
  - ../04-知识原子/atoms/model-agreement-is-not-evidence.md
  - ../03-理论与元认知/元认知/01-置信度校准与证据等级.md
  - ../06-治理与评审/reviews/2026-05-06-multimodel-thinking-keypoint-coverage-review.md
---

# 少数意见：模型名不是证据，模型名不等于权威

## 核心原则

模型名不是证据，模型名不等于权威，模型数量也不是证据。多模型评审中，任何结论都必须回到 issue ledger、severity、evidence quality 与可复现实验，而不是回到“哪个模型更强”或“多少模型同意”。

## 规则

1. 少数意见不能被默认压制。
   - DeepSeek、MiMo 或任何低成本 reviewer 的 dissent，不能因为模型便宜、速度快、名气小而直接忽略。
   - 少数意见必须进入 issue ledger，至少记录 claim、severity、evidence、correction 或 experiment。

2. 强模型不能自动仲裁。
   - Claude、Codex/gpt-5.5 的意见不能因为模型名更强而自动胜出。
   - 强模型可以提供更完整的 synthesis，但不能跳过 evidence-first 和 truth gate。

3. 多数同意不等于认证。
   - `approval_count >= N-1` 只是 ratification 条件之一。
   - 若存在 severity>=4 的 unresolved dissent，或者 severity>=3 的 unsupported factual claim，状态必须降级为 `not_certified` 或 `certified_with_minor_risks`。

4. 最终处理口径按证据，而不是按身份。
   - 采纳：有工具证据、源码证据、测试结果或可复现实验支撑。
   - 暂存：合理但缺 evidence，需要 evidence_request。
   - 驳回：被更强证据反驳，或 experiment 不成立。
   - 接受风险：风险真实但在当前约束内显式接受，并写入 remaining_risks。

## 操作化 schema

每条少数意见至少写成：

```json
{
  "issue_id": "I-minority-001",
  "source_model": "deepseek-v4-pro|mimo-v2.5-pro|claude|gpt-5.5|other",
  "claim": "少数意见主张",
  "severity": 1,
  "evidence_quality": "E0|E1|E2|E3|E4",
  "requested_evidence": "需要 orchestrator 执行的只读验证",
  "resolution": "accepted|rejected|accepted_risk|deferred",
  "resolution_basis": "证据或实验结果，而不是模型名"
}
```

## 与已有原则的关系

- [[model-agreement-is-not-evidence]]：解决“多数一致不是证据”。
- 本卡：解决“少数意见不能因模型身份被丢弃；强模型也不能因身份自动胜出”。
- [[03-理论与元认知/元认知/01-置信度校准与证据等级|置信度校准与证据等级]]：提供 evidence quality 的判断尺度。
- [[2026-05-06-multimodel-thinking-keypoint-coverage-review]]：记录本次从 21/22 补到 22/22 的覆盖证明。

## 反模式

- “Claude 说可以，所以通过。”
- “三个模型同意，一个便宜模型反对，忽略。”
- “DeepSeek 反对，所以必须停。”
- “模型都觉得没问题，所以无需 test/build/search。”

正确口径：模型输出是候选判断；证据、实验、issue resolution 才是认证依据。
