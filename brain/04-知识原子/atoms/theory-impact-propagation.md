---
type: atom
layer: L1
status: active
created: 2026-05-12T01:14:00+08:00
concepts: [theory-impact-propagation, same-theory-propagation, layer-impact-map, impact-smoothing, fail-closed]
---

# Theory Impact Propagation

## Principle

单点优化不是完成态，只是一个 candidate perturbation。它必须先绑定 Theory Point ID，再生成 Layer Impact Map，扫描 Same-theory propagation targets，最后通过 Impact Smoothing 和 fail-closed verification，才能成为全架构规则。

局部优化不能直接升级为全局规则；local patch is only a candidate until evidence, impact, and smoothing gates pass.

## Required object

TheoryPropagationRecord:

- Theory Point ID: canonical theory/principle identifier, e.g. evidence-first, ashby-variety, feedback-stability.
- Source event: user correction, failed gate, taskpool proof, review dissent, timeout, regression.
- Target-bound slice: what is allowed to change and what is forbidden.
- Same-theory propagation: at least two equivalent locations or explicit none-rationale.
- Layer Impact Map: impacted L0, L1, L2, L3, L4, L5, LX and auxiliary surfaces.
- Evidence links: proof/selfcheck/lifecycle/evidence-spine/ratchet artifacts.
- Impact Smoothing: health variance, regression diff, rollback boundary, compatibility gate.
- Closeout verdict: stable_committed, observe_only, fail_closed_quarantine, rollback.

## Architecture mapping

- L0 trace: sensor. Records Theory Point ID, source event, before/after evidence.
- L1 router: controller. Routes same-theory optimizations to T0/T1/T2/T3 by complexity, uncertainty, reflexivity, blast radius.
- L2 protocol: reference behavior. Converts the theory point into envelope/protocol/closeout constraints.
- L3 ensemble: estimator. Uses cross-critique/cross-patch to find disagreement and impacted diffs.
- L4 taskpool-brain: integrator. Creates tasks, proof logs, lifecycle entries, reviews, and searchable brain artifacts.
- L5 consult-models: reference committee. Performs target-bound T3 only when the blast radius requires it.
- LX health-quota: governor. Stops propagation when health, quota, or stability margins degrade.

## Same-theory propagation

Same-theory propagation asks: “If this theory fixed one slice, where else does the same theory apply?”

Examples:

- evidence-first in ratification gate also applies to Lark closeout, proof-check, task done transition, and skill references.
- feedback-stability in dispatch tick also applies to cron heartbeat, gateway watchdog, and V(x) monitor.
- near-decomposability in task boundary also applies to project workspaces, conflict groups, and auto-run allowlists.

## Impact Smoothing

Impact Smoothing does not erase differences. It dampens unsafe layer skew.

Required smoothing tools:

- two-phase prepare/apply: impacted layers prepare before commit.
- regression diff: changed behavior must have a before/after artifact.
- health variance: layer deltas must not diverge sharply.
- rollback boundary: every propagation has a reversible stop point.
- compatibility gate: old and new contracts stay aligned during transition.
- fail-closed quarantine: if evidence is missing, stop propagation and do not claim architecture coverage.

## Stop rule

- H_total up and V_bad down: stable commit.
- H_total flat and V_bad flat: observe only.
- H_total down or V_bad up: fail-closed quarantine.
- ImpactVariance high: smoothing before closeout.
- not_certified, dissent, or timeout: provenance only, not certification.

## Links

- [[05-实践与项目/实践方案/08-理论到影响全架构传播矩阵]]
- [[05-实践与项目/实践方案/07-关键点多模型介入路由矩阵]]
- [[04-知识原子/atoms/keypoint-to-multimodel-routing]]

## 中文检索别名

理论到影响 单点优化 全架构传播 同理论扫描 同理论优化 影响平滑 差异抚平 Theory Point ID Layer Impact Map Same-theory propagation Impact Smoothing fail-closed
