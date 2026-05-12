---
type: review
status: active
created: 2026-05-06T09:05:08Z
review_subject: multi-model-thinking-keypoint-coverage
coverage: 22/22
concepts: [multi-model-thinking, evidence-first, minority-opinion, ratification]
---

# 多模型思考关键点覆盖复审

## 复审结论

本地大脑对“多模型思考方案”的关键点覆盖从 `21/22` 补齐到 `22/22`。

补齐前唯一缺口：

- 少数意见 / 模型名不等于权威。

补齐 artifact：

- [[minority-opinion-and-model-authority]]

## 22 个关键点状态

| # | 关键点 | 状态 |
|---|---|---|
| 1 | 四模型/互补模型组合 | covered |
| 2 | fanout/provenance 与认证分离 | covered |
| 3 | 多模型一致不是证据 | covered |
| 4 | Evidence-first / 工具证据优先 | covered |
| 5 | truth gate / unsupported claims 阻断认证 | covered |
| 6 | state/state_hash/artifact 固定输入与可复现 | covered |
| 7 | Blind seed proposals / 独立初始方案 | covered |
| 8 | disagreement / issue ledger | covered |
| 9 | cross-critique / AMEND/REJECT/APPROVE | covered |
| 10 | rebuttal / revision / discussion round | covered |
| 11 | red-team / devil advocate | covered-thin |
| 12 | ratification / stop condition | covered |
| 13 | communication budget / 索引卡+差异 | covered |
| 14 | not_certified caveat 明确记录 | covered |
| 15 | 本地大脑分类落地：reviews/tasks/evidence/evolution | covered |
| 16 | sync/reindex/search 作为落地证明 | covered |
| 17 | anti-drift 双轨：deterministic oracle + LLM critic | covered |
| 18 | 模型角色边界：orchestrator 执行工具，reviewer 提证据请求/风险 | covered |
| 19 | quorum/T2/T3/四模型不得偷省 | covered |
| 20 | consult_models.py CLI/artifact 使用方式 | covered |
| 21 | 少数意见/模型名不等于权威 | covered by [[minority-opinion-and-model-authority]] |
| 22 | final synthesis/provenance/remaining risks 记录 | covered |

## Caveat

`22/22` 表示本地大脑中已有可检索、可引用的关键点覆盖；不表示最近两次多模型运行获得完整 ratified certification。
历史 artifact 仍保持原 caveat：

- `/Users/charles/.hermes/tick-20260506-073039`：discussion/consensus 曾 timeout，`consensus_verdict: dissent`。
- `/Users/charles/.hermes/tick-20260506-083543`：PUA-loop 多模型评审为 `not_certified`。

因此当前结论是：知识覆盖已补齐；历史多模型认证状态不被篡改。

## Verification plan

完成后需运行：

```bash
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "minority opinion model authority" --limit 10
python3 ~/.hermes/scripts/brainctl.py --json search "少数意见 模型名不是证据" --limit 10
```

## Evidence Boundary

- Added by backlog-zero loop at `2026-05-06T13:32:29Z`.
- This review is provenance, not truth proof. Its claims may support promotion only when linked tool/file/search evidence is satisfied.
- Model agreement, dissent, timeout, or not_certified labels must remain visible; do not treat review consensus as deterministic evidence.
