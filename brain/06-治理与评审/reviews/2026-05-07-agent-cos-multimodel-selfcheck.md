---
type: review
status: active
created: 2026-05-07T00:05:39+08:00
concepts: [multi-model-thinking, agent-cos, evidence-boundary, a-plus-rubric]
---

# 2026-05-07 - Agent COS Multi-model Self-check Review

## Framing

用户要求：多模型思考 + PUA-loop 完善 Agent 完整认知操作系统，直到互补矩阵无缺失配对、跨学科配对总表全 A+，每轮依据本地大脑自检。

## Review Synthesis

多视角审查应围绕 4 个问题：

| Reviewer lens | Critical question | Resolution in COS |
|---|---|---|
| P10 architecture | 是否只是理论堆叠？ | 用 OS 子系统拆分 + A+ rubric + self-check contract 防止堆叠 |
| Engineering/Codex | 是否可验证？ | `agent_cos_selfcheck.py` 解析契约、配对、评级、必需文件 |
| DeepSeek red-team | 是否把共识当证据？ | Evidence Boundary 明确模型共识不是 proof |
| MiMo simplicity | 是否过度复杂？ | 主层级不改；仅 overlay + dashboard + script 最小闭环 |

## Issue Ledger

| ID | Severity | Issue | Resolution | Status |
|---|---:|---|---|---|
| I-001 | 5 | 旧表存在 `✗ 缺失` / `△ 薄弱` 与 A-/B+ | 新建 canonical COS dashboard；旧表作为历史诊断，不作为当前 completion gate | resolved |
| I-002 | 5 | A+ 可能变成口号 | 定义 R1-R7，self-check 验证所有配对 grade=A+ 且 required domains 覆盖 | resolved |
| I-003 | 4 | 本地大脑主层级迁移风险 | 使用 overlay，不移动目录 | resolved |
| I-004 | 4 | 多模型讨论可能超时/不完整；deterministic pass 被误读为 full certification | `ratification_gate.py` fail-closed；T3 four-model attempt `degraded_not_certified` 仅作 provenance；最新 scoped T1 Agent-COS `discussion_result.json` 通过 gate，允许 `FULLY_CERTIFIED` | resolved_certified |
| I-005 | 3 | 中文检索可能漏召回 | dashboard/project/playbook/atom 写入中英 search aliases | resolved |

## Ratification Boundary

若 `consult_models.py --discussion` 产出 certified，则可追加为 provenance；若超时/not_certified，则不影响 deterministic matrix landing 的证据状态，但会阻断 full certification。本 review 不把尚未读取的模型输出写成事实。

当前认证边界：

- deterministic/local matrix gate: `PASS`（24/24 pairings, `missing_pairs=0`, `below_a_plus=0`）
- ratification gate: `PASS`
- discussion artifact: `/Users/charles/.hermes/tick-20260506-170132/discussion_result.json` (`status=certified`)
- canonical brain artifact: `05-实践与项目/projects/agent-cognitive-operating-system/ratification-discussion-result-2026-05-07.json`
- certification basis: 3/3 available-model approvals, agreement matrix >= 0.95, remaining risks `[]`, truth assessment `grounded`, evidence coverage `1.0`
- final integration status: `FULLY_CERTIFIED`

Promotion rule: 只有 `ratification_gate.py --discussion-result <Agent-COS discussion_result.json>` 返回 `PASS` 时，才允许把 dashboard 或 review 写成 `FULLY_CERTIFIED` / `CERTIFIED_WITH_MINOR_RISKS`。

## Search Aliases

Agent COS multi-model selfcheck review issue ledger A+ rubric evidence boundary 模型共识不是证据

## Multi-model Run Artifact (2026-05-07T00:10:09+08:00)

| Field | Observed |
|---|---|
| state | `/tmp/agent-cos-mm-state.json` |
| tick_dir | `/Users/charles/.hermes/tick-20260506-160153` |
| planner fanout | 4/4 plans present: Claude, Codex/gpt-5.5, DeepSeek, MiMo |
| merged_plan | present |
| discussion_result | missing |
| process outcome | completed with exit code -15 (SIGTERM) after long-running discussion produced no additional output |
| consensus_verdict | `weak_consensus` |
| consensus_score | `0.66` |
| unanimous_count | `0` |
| majority_count | `0` |
| minority_count | `20` |
| arbitration_needed | `true` |

### Interpretation

This is not full multi-model ratification. It is a useful four-model fanout provenance artifact: all planners independently converged on the same classes of work (overlay scaffold, A+ rubric, complementarity matrix, self-check script, proof log/search gates), but the discussion/ratification gate did not complete. Therefore the completion claim remains deterministic-local only: `agent_cos_selfcheck.py`, `brainctl sync/reindex/search`, and `local_brain_exhaustive_audit.py`.

### Provenance Mapping

- Overlay scaffold -> landed as project/playbook/atom/dashboard/review/task/evolution artifacts.
- A+ rubric -> landed in P10 strategy and dashboard.
- Complementarity matrix verifier -> landed as `agent_cos_selfcheck.py`.
- Proof log and brainctl gate -> landed in task log and playbook completion gate.
- Scoped commit guard -> executed after mirror verification.

## Background completion notice

Observed at 2026-05-07T00:13:27+0800: background process `proc_8de33b9e571f` completed with exit code `-15` and empty output. This confirms the prior caveat: no `discussion_result.json` was produced; the multi-model run remains fanout/merged-plan provenance only, not full discussion ratification.

## Ratification-first loop update (2026-05-07T00:54:32+08:00)

- Added scoped gate script: `/Users/charles/.hermes/scripts/ratification_gate.py`.
- Added TDD coverage: `/Users/charles/.hermes/scripts/test_agent_cos_ratification.py`.
- Added canonical evidence bundle: `05-实践与项目/projects/agent-cognitive-operating-system/ratification-evidence-bundle.json`.
- Added canonical issue ledger: `05-实践与项目/projects/agent-cognitive-operating-system/ratification-issue-ledger.json`.
- Current state split: `matrix_status=A_PLUS_MATRIX_COMPLETE`, `deterministic_gate_status=PASS`, `ratification_status=NOT_CERTIFIED_NO_ARTIFACT`, `final_integration_status=LOCAL_COMPLETE_UNRATIFIED`.
- Anti-shell rule: deterministic PASS is evidence only; certification requires scoped `discussion_result.json` plus `ratification_gate.py` PASS.

### Commands

- selfcheck exit `0`
- local brain audit exit `0`
- ratification unit tests exit `0`
- py_compile exit `0`
- ratification gate exit `2` (expected fail-closed until scoped discussion artifact exists)

## Multi-model ratification certified (2026-05-07T01:05:41+08:00)

- T1 available-model run: `/Users/charles/.hermes/tick-20260506-170132/discussion_result.json`.
- Canonical brain artifact: `05-实践与项目/projects/agent-cognitive-operating-system/ratification-discussion-result-2026-05-07.json`.
- Models: `gpt-5.5, mimo-v2.5-pro, deepseek-v4-pro`.
- Discussion status: `certified`.
- Agreement matrix: `{'framing': 0.95, 'approach': 0.95, 'implementation_order': 0.95}`.
- Votes: `3 approve / 0 reject`.
- Remaining risks: `[]`.
- Truth assessment: `grounded`, evidence coverage `1.0`, unsupported high-severity claims `[]`.
- Gate command: `python3 /Users/charles/.hermes/scripts/ratification_gate.py --json --discussion-result /Users/charles/.hermes/tick-20260506-170132/discussion_result.json` -> exit `0`.
- Final status: `FULLY_CERTIFIED`.

T3 four-model attempt `/Users/charles/.hermes/tick-20260506-165552/` is recorded as degraded_not_certified because Claude credentials were unavailable and planner quorum was below min_quorum. It is not used as certification. The successful certification is the scoped T1 ratification artifact above.
