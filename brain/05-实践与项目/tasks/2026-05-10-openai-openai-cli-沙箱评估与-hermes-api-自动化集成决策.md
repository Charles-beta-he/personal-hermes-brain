---
type: task
lane: evolution
layer: L3
status: pending
priority: P1
created: 2026-05-10T16:55:28+08:00
updated: 2026-05-11T01:39:48+08:00
expires_at: 2026-06-09T16:55:28+08:00
project: hermes-evolution
architecture_target: provider-quota
capability_delta: "Potential provider/admin API automation capability: official OpenAI REST/admin CLI can improve usage/quota inspection, model/resource smoke tests, file/vector store/Responses scripting, but only after sandbox validation and PATH/secret guardrails."
anti_drift_check: Must not replace Codex CLI/Hermes provider routing; must not store OPENAI_API_KEY/OPENAI_ADMIN_KEY globally; must pin github openai/openai-cli release and record binary conflict with npm openai/@openai/codex before any integration.
acceptance_evidence: 已有 artifact 均只能作 advisory/provenance：20260510-084708 因 MiMo adapter 400 not_certified；20260511-094304 status=certified 但缺 DeepSeek 4/4 且 target binding 不足。须重新产出 target-bound Claude+GPT+DeepSeek+MiMo 四模型 ratification 后才可 closeout。
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: /tmp/openai-cli-audit
evidence: []
concepts: ["openai-cli", "openai-api", "provider-quota", "api-automation", "cli-tooling", "sandbox-eval"]
multimodel_status: not_certified
multimodel_ratification_artifact: /Users/charles/.hermes/tick-20260511-094304/discussion_result.json
certification_status: ""
---

# Task - OpenAI openai-cli 沙箱评估与 Hermes/API 自动化集成决策

## Objective

基于 openai/openai-cli v1.1.2 / commit 9eb2084 的证据与 T2 多模型分析，做一次不写全局密钥、不破坏现有 Codex/Hermes 的沙箱评估：确认它是否能补齐 OpenAI API/admin usage、项目/额度/模型/文件/Responses 自动化能力；区分它与 @openai/codex、npm openai bin、旧 openai-cli 的命名冲突；给出 adopt/selective/monitor 决策。

## Acceptance Criteria

- [ ] 固定版本与来源：GitHub `openai/openai-cli`、latest release、checksum/Homebrew/Go 安装路径、许可证、命令面清单都有证据；不使用旧 npm `openai-cli` 误包。
- [ ] 沙箱验证：不写 `~/.zshrc` 和全局 `OPENAI_*`；若需要运行，只用一次性环境变量/测试 key；验证 `openai --help`、`--version`、关键资源 help、`--format json`/`--transform`、`@file` 输入；记录 PATH/binary 冲突。
- [ ] 安全边界：debug 日志 body 泄漏风险、admin key 使用范围、`OPENAI_BASE_URL`/`--base-url`、项目/组织隔离、日志脱敏规则都有结论。
- [ ] Hermes 集成决策：明确是否仅作为外部 API/admin CLI 使用，是否需要 provider-quota/usage smoke wrapper，是否需要 skill/脚本；如不引入，记录 monitor 条件。
- [ ] 结论落地：若 adopt/selective，则给出最小 wrapper/skill/cron 变更方案和测试；若 monitor only，则给出监控 release/command surface 的条件。

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list/selfcheck/proof/boundary | PASS | 2026-05-11T22:29 +08:00 after target-bound gate repair |

## Proof Log

- 2026-05-10T16:55:28+08:00: Task created from local-brain control point.
- 2026-05-10T16:55:28+08:00: Evidence seed: repo cloned to `/tmp/openai-cli-audit` at commit `9eb208407a0477f89dc7b7a78f04cd40c5bb4d34`; GitHub latest release observed as `v1.1.2`; README/go.mod/CHANGELOG/.goreleaser/debugmiddleware/cmd registry inspected.
- 2026-05-10T16:55:28+08:00: Multi-model artifact: `/Users/charles/.hermes/tick-20260510-084708/discussion_result.json`; status `not_certified` because MiMo discussion adapter returned 400, but claims truth gate was grounded 10/10 and GPT/Claude/DeepSeek approved advisory direction.
- 2026-05-11T20:04:30+08:00: Metadata repair: blanked mission-only `certification_status` because this standalone evolution evaluation is not a full `mission-envelope`; canonical multi-model fields remain `multimodel_status: certified` and `multimodel_ratification_artifact: /Users/charles/.hermes/tick-20260511-094304/discussion_result.json`.

- 2026-05-11T22:25:07+08:00: 流转校准：多模型 artifact 重新验真，当前仅保留为 provenance/advisory；未满足 target-bound 4/4 Claude+GPT+DeepSeek+MiMo 认证，任务继续进入多模型介入/证据补齐队列。

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-11T01:15:51+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T01:39:48+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: deadlock_fix_release
