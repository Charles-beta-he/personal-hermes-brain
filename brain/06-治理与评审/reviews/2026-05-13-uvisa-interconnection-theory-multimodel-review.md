---
title: uvisa-app-2.0 systemic interconnection theory multimodel review
created: 2026-05-13 15:57 CST
type: multimodel_advisory_review
project: uvisa-app-2.0
state: /tmp/uvisa_interconnection_theory_state.json
tick: /Users/charles/.hermes/tick-20260513-075141-150334-p515-2173ba88-77c89751
truth_status: grounded
verified_claim_count: 4/4
fanout_status: fanout_quorum_met
consensus_verdict: weak_consensus
certification_status: advisory_not_full_ratification
models:
  - claude-opus-4-7
  - gpt-5.5
  - deepseek-v4-pro
  - mimo-v2.5-pro
---

# uvisa-app-2.0 系统性“互相关联不足”理论与完善方案

## 0. 结论

多模型 fan-out 的共同结论：当前 UVISA / Hermes 项目画像控制面不是“没有关联”，而是“有骨架、缺语义控制面”。

已有事实：
- `~/.hermes/project-profiles/uvisa-app-2.0.json` 已有丰富策略字段：fullstack domain map、backend contract policy、regression policy、Lark execution/evidence policy、release branch policy、multi-model policy、local fullstack browser acceptance、private runtime evidence policy。
- Workpad 是项目工作记忆，包含 anchors、red lines、evidence ledger、known risks、next loop queue、d964/PROJECT-PROFILE profile updates。
- 先前诊断指出主缺口是 semantic control-plane linkage，而非完全没有链接。
- 本次用户要求长期项目化、灵活维护、多方向均衡，而不是一次性 patch。

Fan-out 结果：4 个模型均参与，truth gate grounded 4/4；但没有跑 full discussion/ratification，merged plan 为 weak_consensus，`patches=[]`，`minority_patches=15`，因此本文件是 truth-grounded advisory，不是最终实现认证。

## 1. 理论论点与核心著作

### 1.1 控制论 / 系统论：控制器必须拥有可执行的系统模型

核心论点：如果 profile 只是文本策略，而 dispatch/proof/ratification 不读取它，系统就没有真正的控制回路。控制面需要状态变量、误差检测、反馈、放大/衰减、递归治理。

核心著作：
- Norbert Wiener, Cybernetics (1948)
- W. Ross Ashby, An Introduction to Cybernetics (1956)
- Roger Conant & W. Ross Ashby, Every Good Regulator of a System Must Be a Model of That System (1970)
- Stafford Beer, Brain of the Firm (1972), The Heart of Enterprise (1979)
- Jay Forrester, Industrial Dynamics (1961)
- Donella Meadows, Thinking in Systems (2008); Leverage Points (1999)

落地含义：
- `profile_policy_contract` 是 Good Regulator 的“系统模型”。
- dispatch 不应只看 profile 是否存在，而应读取 task class、domain、risk、required evidence、closeout authority。
- Workpad 不只是日志，而是反馈回路仪表盘。

### 1.2 软件架构 / 模块化：稳定接口与可变 overlay 分离

核心论点：互相关联不足常来自“策略字段很多，但没有稳定模块边界”。长期维护必须把 stable invariant kernel 和 project-specific overlay 分开。

核心著作：
- David Parnas, On the Criteria To Be Used in Decomposing Systems into Modules (1972)
- Frederick Brooks, The Mythical Man-Month (1975), No Silver Bullet (1986)
- Carliss Baldwin & Kim Clark, Design Rules: The Power of Modularity (2000)
- Len Bass, Paul Clements, Rick Kazman, Software Architecture in Practice
- Eric Evans, Domain-Driven Design (2003)
- Martin Fowler, Refactoring (1999/2018), Patterns of Enterprise Application Architecture (2002)
- John Ousterhout, A Philosophy of Software Design (2018)

落地含义：
- 稳定 kernel：task taxonomy、evidence schema、handoff envelope、ratification semantics、writeback rules、rollback signal。
- 灵活 overlay：UVISA domain map、Lark evidence precedence、branch policy、prototype anchor、backend-first rule、local fullstack topology。
- 不能每次新增项目规则都直接塞进 prompt；应先归类到 kernel / overlay / evidence / runtime gate。

### 1.3 组织与社会技术系统：架构会镜像沟通结构

核心论点：任务池、worker、backend/frontend、review、多模型之间如果没有显式 handoff 契约，就会形成 Conway 式漂移：每个子系统都以自己的局部语言运行。

核心著作：
- Melvin Conway, How Do Committees Invent? (1968)
- Eric Trist & Fred Emery, socio-technical systems work
- Peter Senge, The Fifth Discipline (1990)
- Matthew Skelton & Manuel Pais, Team Topologies (2019)
- Chris Argyris & Donald Schön, Organizational Learning II (1996)

落地含义：
- handoff 必须是 typed envelope，不是自由 prompt。
- 每个 task 应显式声明 owner boundary：frontend/backend/contract/product/admin/prototype/release。
- writeback 不只是记录“做了什么”，还要记录“我们的分类/规则是否需要改变”。

### 1.4 安全工程 / 证据工程：多层防线而非单一大门

核心论点：当前 proof 和 multi-model 容易成为 generic token gate。长期项目需要 layered defense：schema/grounding、policy compliance、evidence-kind sufficiency、model ratification、human/release gate。

核心著作：
- W. Edwards Deming, PDCA / Out of the Crisis (1982)
- Karl Popper, The Logic of Scientific Discovery (1934/1959)
- James Reason, Human Error (1990); Swiss cheese model
- Nancy Leveson, Engineering a Safer World (2011), STAMP/STPA
- Toyota Production System / Jidoka / Andon; Jeffrey Liker, The Toyota Way

落地含义：
- 任务 done 不能靠“测试/build 字符串出现”。
- required evidence labels 必须按 task_class + domain 派生。
- ratification gate 必须 target-bound、risk-tiered、fail-closed。

### 1.5 知识管理 / 双环学习：把经验回写成可执行规则

核心论点：如果每次多模型/任务复盘只增加自然语言经验，系统会越来越重、越来越难维护。需要区分 single-loop evidence logging 与 double-loop rule update。

核心著作：
- Chris Argyris & Donald Schön, Organizational Learning II
- Donald Schön, The Reflective Practitioner (1983)
- Ikujiro Nonaka & Hirotaka Takeuchi, The Knowledge-Creating Company (1995)
- Etienne Wenger, Communities of Practice (1998)

落地含义：
- 每个任务 closeout 可写 evidence ledger；但修改 profile policy 需要 evidence、impact map、rollback。
- 定期 profile pruning/deprecation，避免规则堆积成“政策垃圾场”。
- rejected/returned task 应生成 learning candidate，但不能自动变成全局规则。

### 1.6 复杂适应系统 / 反脆弱：不要把系统做成一个僵硬超级 gate

核心论点：长期项目既要有关联，又不能把所有任务都强行走最重 T3/全栈/全证据路径。要用分层、多臂、多方向 portfolio。

核心著作：
- Herbert Simon, The Sciences of the Artificial (1969)
- John Holland, Adaptation in Natural and Artificial Systems (1975)
- Elinor Ostrom, Governing the Commons (1990)
- Nassim Nicholas Taleb, Antifragile (2012)

落地含义：
- 用 risk-tiered routing：T0/T1/T2/T3，而不是所有任务四模型。
- 用 small-batch evolution + health metric，而不是一次性大迁移。
- 允许 project overlay 局部调整，但要保持 kernel 合同稳定。

### 1.7 语言与语义承诺：分类不是标签，而是后续义务

核心论点：`fullstack-integrated`、`backend-owned`、`prototype-dependent` 不是描述词，而是承诺了后续 proof、handoff、ratification、closeout 的义务。

核心著作：
- Ludwig Wittgenstein, Philosophical Investigations (1953)
- Robert Brandom, Making It Explicit (1994)
- Eric Evans, Domain-Driven Design (ubiquitous language)

落地含义：
- task classification 必须带 consequences：inspect paths、required assets、evidence labels、blocked conditions。
- 任务语言要进入机器合约，不能只留在 prompt 里。

## 2. 综合诊断

最准确的根因句：

UVISA 画像已有大量高价值策略原子，但缺少一个稳定、可执行、可审计的 semantic control-plane contract，把“任务语义分类”转换成“调度路线、worker 合同、证据链、ratification 权限、失败学习回写”。

当前风险：
- profile 字段变多，但 runtime 不一定消费。
- Workpad 证据丰富，但多为自由文本，不便程序化检查。
- 多模型能指出问题，但如果没有 issue→contract→gate 的落地路径，会重复给 advisory。
- 过度修复风险：一上来把所有任务都要求 T3/fullstack，会拖慢低风险任务并制造维护成本。

## 3. 完善方案：稳定内核 + 灵活 overlay + 证据链闭环

### 3.1 P0：定义 `semantic_control_plane_contract_v1`

目标：不是重写 profile，而是在 profile 之上加一层可执行合同。

字段建议：

```json
{
  "schema": "semantic_control_plane_contract_v1",
  "stable_kernel": {
    "task_taxonomy": [],
    "evidence_kinds": [],
    "handoff_envelope_required_fields": [],
    "ratification_semantics": {},
    "writeback_policy": {},
    "rollback_signal": {}
  },
  "project_overlay": {
    "domain_map": "fullstack_domain_map",
    "source_precedence": "lark_evidence_policy",
    "release_policy": "release_branch_policy",
    "local_acceptance": "local_fullstack_browser_acceptance"
  },
  "policy_dependency_graph": {},
  "runtime_consumers": ["classifier", "dispatch", "handoff", "proof", "ratification", "writeback"]
}
```

### 3.2 P1：task_classification 必须有 consequence

推荐分类：
- `frontend-only`
- `backend-owned`
- `fullstack-integrated`
- `cross-cutting-infrastructure`
- `prototype-asset-dependent`
- `release-sync`
- `evidence-only / regression-proof-already-satisfied`
- `admin/out-of-scope`

每个分类输出：
- impacted domains
- required source assets
- required repos/files to inspect
- required evidence labels
- ratification tier
- allowed closeout authority
- blockers
- writeback candidate type

### 3.3 P2：dispatch/handoff/proof 统一消费同一个 contract

- dispatch：不能只检查 profile exists；要检查 `classification.blockers == []`。
- worker handoff：必须包含 contract JSON，而不是只塞 profile 摘要。
- proof：按 evidence labels 检查，不按泛 token。
- closeout：按 task_class/risk 决定 T0/T1/T2/T3，不把 advisory 当 certification。

### 3.4 P3：Workpad 增加结构化 control-plane health，而不是继续堆 prose

新增轻量表：

| Loop | task_class | activated_policy_chain | evidence_labels | gate_result | writeback_candidate | next check |

用途：
- 让长期项目可回看哪些 policy 真被执行过。
- 找出“写了但从未被触发”的死规则。
- 避免自由文本证据无法进入 proof/routing。

### 3.5 P4：学习回写分两层

Single-loop：
- 任务证据、测试结果、build、browser 证据写 Evidence Ledger。

Double-loop：
- 只有当同类失败重复出现、或多模型/用户纠偏证明分类/策略错误时，才更新 profile policy / skill / selfcheck。
- 每次 policy 更新必须有：source evidence、impact map、rollback boundary、expiry/review date。

### 3.6 P5：风险分层多模型策略

- T0：确定性工具检查，低风险文档/字段存在性。
- T1：单 reviewer，用于小范围实现方向 sanity。
- T2：三模型 advisory，用于分类、路线、scope/risk 分歧。
- T3：四模型 discussion/ratification，用于高风险 money/security/backend-contract/release closeout。

硬规则：T2/T3 advisory 可指导实现，但 Lark/taskpool final certification 仍按用户策略需要 canonical 4 模型完整 closeout。

## 4. 多方向均衡 portfolio

1. Architecture direction
   - 建 semantic contract kernel。
   - 分清 stable invariant 与 UVISA overlay。

2. Runtime/tooling direction
   - classifier/dispatch/proof/ratification 逐步接入 contract。
   - 增 selfcheck：未被 runtime 消费的 profile policy 字段要 WARN。

3. Evidence direction
   - evidence labels 结构化。
   - Workpad task outcomes 半结构化表。

4. Process direction
   - Lark 任务先分类，再执行。
   - scope_control 防止 backend-aware 变成无边界审计。

5. Governance direction
   - profile policy 更新需要 impact map + review cadence。
   - stale/dead rules 定期 prune。

6. Learning direction
   - returned task / model dissent 先进入 learning candidates。
   - 重复出现才升级到 profile/skill。

7. Cost/speed direction
   - 不所有任务 T3；risk-tiered routing。
   - deterministic gate 优先，multi-model 用在语义/高风险分歧。

## 5. 建议实施顺序

### Slice 1：文档与 schema，不动 runtime
- 在 profile 加 `semantic_control_plane_strategy` advisory 字段。
- 在 Workpad 登记本 review 与 control-plane plan。
- 不改变 dispatch/proof 行为。

### Slice 2：只读自检
- 新增/扩展 selfcheck，检查 profile policy 字段是否有 runtime consumer 映射。
- 输出 WARN，不 fail closeout。

### Slice 3：分类器 dry-run
- 对最近 UVISA Lark tasks 运行 task_classification dry-run。
- 只报告分类、required evidence labels、blocked reasons，不自动改任务状态。

### Slice 4：handoff envelope typed JSON
- worker handoff 附带 `profile_policy_contract` JSON。
- proof 仍保持旧 gate，但记录 contract/evidence label coverage。

### Slice 5：profile-aware proof gate soft launch
- 对 `review` 任务跑 include-active audit。
- 新规则先 WARN，连续稳定后逐步 fail-closed。

### Slice 6：risk-tiered ratification
- 低风险任务不强制 T3。
- 高风险 closeout 继续 canonical 4/4 target-bound。

## 6. 反模式

- 把所有 profile 字段复制进 prompt，以为这就是关联。
- 一次性大改 dispatch/proof/ratification 三层，导致难回滚。
- 用关键词触发所有多模型，导致触发率爆炸。
- 把 weak consensus / planner fanout 当 full certification。
- 把一次任务失败直接升级成全局规则。
- 把 Workpad 当 status dump，而不是 feedback/control dashboard。

## 7. 本次 provenance

- State: `/tmp/uvisa_interconnection_theory_state.json`
- Tick: `/Users/charles/.hermes/tick-20260513-075141-150334-p515-2173ba88-77c89751`
- Models: Claude Opus 4.7, GPT-5.5, DeepSeek V4 Pro, MiMo V2.5 Pro
- Truth: grounded 4/4
- Fanout: quorum met 4/4
- Consensus: weak consensus, not full ratification

## 8. Runtime soft-launch landing (2026-05-13)

Follow-up implementation landed the safe subset of this advisory plan as deterministic taskpool runtime support:

- `profile_policy_contract_v1` is generated from the project profile and injected into dispatch prompts as WARN-only JSON.
- `semantic-control-plane-dry-run` emits read-only task classifications, risk tier, required evidence labels, runtime consumers, and certification-authority boundary.
- `selfcheck` reports `semantic_control_plane_selfcheck_v1`; profile-control warnings remain warnings, not fail-closed blockers.
- UVISA project profile now records `runtime_landing` with code paths, commands, evidence paths, non-goals, and rollback boundary.

Verification evidence:
- `/Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/taskpool/semantic-control-plane-dry-run-2026-05-13.json`
- `/Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/taskpool/semantic-control-plane-selfcheck-2026-05-13.json`
- `python3 ~/.hermes/scripts/test_brain_task_orchestrator.py` PASS
- `python3 -m json.tool ~/.hermes/project-profiles/uvisa-app-2.0.json` PASS

Closeout classification: deterministic slice landed; certification remains `advisory_not_full_ratification`. This update does not authorize fail-closed proof gates or automatic closeout. Any promotion beyond WARN-only needs a fresh target-bound T3 ratification and rollout/rollback plan.

