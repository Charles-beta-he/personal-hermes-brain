---
type: strategy
status: active
layer: P10
created: 2026-05-07T00:05:39+08:00
concepts: [p10, cognitive-operating-system, evidence-first, pua-loop]
---

# P10 - Agent COS Long-term Strategy

## Strategic Decision

把 Agent 的长期进化从“补某个 skill / 写某个 prompt”升级为“认知操作系统”：每个能力位都有主理论、互补理论、运行时机制、证据门、失效模式、降级路径和本地大脑落点。

## A+ Rubric

一项跨学科配对只有同时满足 7 个条件才可标为 A+：

| Gate | Requirement |
|---|---|
| R1 映射紧密度 | 理论概念能直接映射到 Agent 子系统，不是松散比喻 |
| R2 互补性 | 填补控制论或现有 skill 的真实盲区，不重复造轮子 |
| R3 可操作性 | 有明确 tool/script/skill/playbook/route 可执行 |
| R4 证据门 | 有本地 brain/tool/test/build/search/audit 证据，不靠模型共识 |
| R5 失效模式 | 写明何时会误用、漂移、过度推广或引入成本 |
| R6 路由等级 | 明确 T0/T1/T2/T3 何时介入多模型，不凡事四脑 |
| R7 本地落地 | 至少有 project/playbook/atom/review/task/dashboard 之一承载 |

## P10 Stop Condition

- `python3 ~/.hermes/scripts/agent_cos_selfcheck.py --json` 返回 PASS。
- 输出中 `missing_pairs=0`、`below_a_plus=0`、`required_domains_ok=true`、`a_plus_rubric_ok=true`。
- `python3 ~/.hermes/scripts/local_brain_exhaustive_audit.py` 返回 `stop_gate_pass=true`。
- `brainctl search` 对中文和英文查询均命中新矩阵/项目/原子。
- 若多模型讨论未完整 certified，只能记为 provenance，不影响工具证据的 completion。

## P9 Backlog Summary

P0 已落地：COS project、P10、P9、playbook、atom、dashboard matrix、review、task log、evolution log、self-check script。

P1 运行期增强：把 COS self-check 纳入本地大脑 sync cron 的可选验证；把矩阵统计接入 `07-仪表盘/本地大脑治理健康度`。

P2 研究增强：对每个 A+ 配对建立更细的 evidence benchmark；若 4 周 overlay 证明提升，再讨论是否重排主层级。

## Search Aliases

P10 Agent COS A+ rubric no missing pairs 本地大脑自检 多模型证据边界 PUA loop 完整认知操作系统
