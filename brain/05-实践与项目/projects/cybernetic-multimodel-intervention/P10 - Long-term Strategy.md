---
type: strategy
layer: L2
status: active
created: 2026-05-06T18:29:31+08:00
project: cybernetic-multimodel-intervention
---

# P10 - Long-term Strategy: Cybernetic Multi-model Intervention

## Strategic answer

可以介入，而且应该介入；但介入方式必须区分 first-order cybernetics 和 second-order cybernetics。

- first-order cybernetics：控制对象任务。多模型是 regulator / controller，任务、代码、本地大脑结构、外部项目是 object task。
- second-order cybernetics：控制观察者。多模型和 orchestrator 一起观察 observer/controller 本身：模型路由、skill 选择、memory 写入、验证规则、issue ledger、证据门。

## P10 principle

多模型不是“真理机器”，而是 Ashby 必要多样性的一种实现：用多个模型增加 controller variety，以覆盖复杂任务的状态空间；最终真值仍由 tool evidence、source evidence、build/test/search/sync 等 deterministic gates 决定。

model agreement is not evidence。

## Intervention boundaries

| Order | Controlled object | Multi-model role | Stop gate |
|---|---|---|---|
| First-order | 外部任务 / 项目 / 文件 / 本地脑结构 | 生成方案、风险、实验、反例 | 工具验证通过；证据链完整 |
| Second-order | Agent 自身观察与控制机制 | 审计审计器、路由、skill、memory、验证规则 | self-check、issue ledger、caveat 真实记录 |

## P10 stop gate

P10 stop gate requires:

1. First-order gate 明确要求 tool evidence，不接受模型一致替代证据。
2. Second-order gate 明确审计 observer：routing、skill trigger、memory、verification rule、timeout/not_certified。
3. Multi-model timeout/dissent 被记录为 provenance，不被伪装成 ratification。
4. 本地大脑有可检索 artifact 与 atom。
5. `cybernetic_multimodel_selfcheck.py` PASS。
6. `brainctl sync/reindex/search` 有观测输出。

## Top risks

| Risk          | Severity | Mitigation                                                       |
| ------------- | -------: | ---------------------------------------------------------------- |
| 多模型一致被误当事实    |        5 | model agreement is not evidence + first-order tool evidence gate |
| 二阶审计退化为自我赞美   |        4 | second-order gate 必须检查规则、路由、memory、验证脚本本身                        |
| 讨论超时后伪装认证     |        4 | review note 记录 not_certified / timeout / dissent                 |
| 过度调用多模型造成成本浪费 |        3 | 只在架构/高风险/跨域任务触发，普通任务用 T0/T1 或 deterministic gates                |
| 本地脑只写方案不验证    |        3 | self-check + sync/reindex/search + scoped commit                 |

## Decision

下一阶段采用“双环介入”：

- Outer loop：First-order multi-model intervention controls object task。
- Inner loop：Second-order self-observation audits the controller and verification process。

该机制进入本地大脑实践层，作为未来多模型评审、架构设计、本地大脑治理和 Hermes 自进化的默认 P10/P9 框架。

## 中文检索别名

一阶控制论 二阶控制论 多模型介入 控制论 多模型 观察者 自观察 审计规则 证据门

## Hierarchy strategy: overlay before rewrite

The Obsidian main hierarchy must remain stable until the semantic/control-plane overlay proves measurable advantage. The next-stage answer is not an immediate directory rewrite, but a keypoint-to-multimodel routing matrix.

Migration to a new main hierarchy requires G1-G7 gates: 4-week overlay run, measurable retrieval/decision improvement, zero broken wikilinks, reversible migration map, dual-write/shadow MOC, P10/P9 ratification or accepted-risk record, and explicit user approval.

Decision artifact: [[05-实践与项目/实践方案/07-关键点多模型介入路由矩阵]].
