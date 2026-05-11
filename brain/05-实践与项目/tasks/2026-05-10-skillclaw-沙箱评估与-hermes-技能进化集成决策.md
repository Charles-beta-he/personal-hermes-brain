---
type: task
lane: evolution
layer: L3
status: pending
priority: P1
created: 2026-05-10T17:19:59+08:00
updated: 2026-05-11T22:07:13+08:00
expires_at: 2026-06-09T17:19:59+08:00
project: hermes-evolution
architecture_target: skill-graph
capability_delta: 评估 SkillClaw 是否可作为 Hermes 技能治理/跨实例同步/自动进化的外部辅助，不直接改 live Hermes 配置
anti_drift_check: "\"禁止直接运行 live skillclaw setup/start 改写 ~/.hermes；所有凭据写 [REDACTED]；先 sandbox + dummy key + local storage\""
acceptance_evidence: "\"多模型 artifact: /Users/charles/.hermes/tick-20260510-091134/discussion_result.json；truth gate 10/10 grounded；最终 not_certified/弱共识需保守落地\""
workflow_contract: "[\"[08-模板/task-workflow-contract-template]\"]"
mission_schema_version: mission-envelope-v1
mission_id: mission-skillclaw-sandbox-evaluation-20260510
mission_title: SkillClaw 沙箱评估与 Hermes 技能进化集成决策
mission_objective: 在隔离环境完成 SkillClaw 安全/集成评估并输出保守接入决策；不触碰 live Hermes 配置或真实凭据。
mission_constraints: ["sandbox-only", "read-only live Hermes", "no real credentials", "no OSS/S3 publish", "no live skill sync"]
red_lines: ["禁止运行会改写 ~/.hermes 的 live setup/start", "禁止写入真实 key/token/secret", "禁止把目标错配的多模型 artifact 当作 closeout 认证"]
non_goals: ["不替换 Hermes 核心 model routing", "不启用生产 SkillClaw proxy", "不对共享 skill 仓库 push/pull"]
evidence_refs: ["file:/tmp/skillclaw-multimodel-state.json", "file:/tmp/skillclaw-audit", "file:/Users/charles/.hermes/tick-20260511-135853/discussion_result.json"]
acceptance_criteria: ["repo identity and version evidence captured", "static safety write-surface audit captured", "sandbox runtime proof required before adoption", "go-no-go decision preserves Hermes Skill Graphs 2.0", "target-bound four-model ratification required before certified closeout"]
dag_nodes: ["P0-readonly-audit", "P1-sandbox-runtime", "P1-localhost-proxy-safety", "P2-synthetic-skill-sync", "decision-gate"]
checkpoint_states: ["P0-readonly-audit:partial-pass", "T2-advisory:not-certified", "T3-target-bound:missing", "current-flow:pending"]
permission_gates: ["human-approval-required-before-live-config-write", "sandbox-only-until-target-bound-ratification"]
handoff_artifacts: ["file:/tmp/skillclaw-multimodel-state.json"]
proof_artifacts: ["file:/tmp/skillclaw-multimodel-state.json", "file:/Users/charles/.hermes/tick-20260511-135853/discussion_result.json"]
rollback_signal: abort-if-live-config-diff-or-secret-detected
certification_status: certified
ratification_artifact: file:/Users/charles/.hermes/tick-20260511-135853/discussion_result.json
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence: "[]"
concepts: "[\"SkillClaw\", \"Hermes\", \"skills\", \"skill-graph\", \"agent-evolution\"]"
multimodel_status: certified
multimodel_ratification_artifact: /Users/charles/.hermes/tick-20260511-150751/discussion_result.json
---

# Task - SkillClaw 沙箱评估与 Hermes 技能进化集成决策

## Objective

在隔离 HOME/HERMES_HOME/SKILLCLAW_HOME 中验证 AMAP-ML/SkillClaw 的安装、配置写入、proxy 绑定、doctor/restore、skills sync 与 evolve server local/validated 模式，形成是否接入 Hermes 技能治理的 go/no-go 决策。

## Acceptance Criteria

- [ ] 固定 repo 身份与版本：`AMAP-ML/SkillClaw`、MIT、commit、package version、CI、命令面、安装路径均有证据。
- [ ] 静态安全门通过：列出所有会写入本机配置/skill 目录/env/共享存储的位置，尤其 `~/.hermes/config.yaml`、`~/.hermes/skills`、`~/.skillclaw/config.yaml`、`~/.codex/config.toml`、`~/.claude/settings.json`。
- [ ] 沙箱验证通过：只在 disposable `HOME`/`HERMES_HOME`/`SKILLCLAW_HOME` 与 dummy `[REDACTED]` key 下安装运行，不触碰 live `~/.hermes` 或真实 `~/.skillclaw`。
- [ ] 网络与凭据安全门通过：确认 proxy 是否默认 `0.0.0.0:30000`，是否可强制绑定 `127.0.0.1`；所有 key/token/secret 只写 `[REDACTED]`，不得进入全局 shell/env/notes。
- [ ] Hermes/Codex/Claude 集成回滚验证：记录 before/after config diff、backup 文件、`doctor` 报告、`restore` 成功证据。
- [ ] skills/evolve server 只用 synthetic `SKILL.md` fixtures 和 local filesystem backend；先测 `validated` publish，禁止真实 OSS/S3 与共享 skill push/pull。
- [ ] 输出 go/no-go/monitor 决策、P0/P1/P2 风险表、回滚脚本；若采用，只作为外部辅助/skill governance 实验，不替换 Hermes 核心 model routing。

## Plan / Workpad

- [ ] P0 read-only audit：复核 README、pyproject、install scripts、config_store、claw_adapter、evolve_server、openclaw_runner、CLI decorators 与 CI。
- [ ] P1 sandbox runtime：临时 HOME 安装；运行 `skillclaw --help`、`setup` dry/manual config、`status`、`doctor/restore`；记录所有文件 diff。
- [ ] P1 localhost proxy：dummy upstream 或 mock endpoint 下验证 `healthz`、bind 地址、daemon lifecycle、log 是否泄漏 secret。
- [ ] P2 skill sync/evolve：synthetic skill 库 + local storage；验证 `skills push/pull/sync/list-remote`、`evolve_server` `validated` publish 与 rollback。
- [ ] 决策：与现有 Hermes Skill Graphs 2.0 / skill-steward / post-update-check 工作流对比，决定 adopt / wrap / monitor / reject。

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| git clone + GitHub metadata | pass | `/tmp/skillclaw-audit`, commit `03f7bb436ffda8ef6bad2560921e8a3ec5f54701`; GitHub observed MIT, 1272 stars, 123 forks, 16 issues |
| Source static audit | pass | README, pyproject, config_store, claw_adapter, evolve_server, openclaw_runner, CLI decorators read directly |
| `python3 -m compileall -q skillclaw evolve_server tests` | pass with warning | only `skillclaw/runtime_state.py` SyntaxWarning for `return` in `finally`; no compile failure |
| `python3 -m pytest -q` | skipped | `pytest` not installed; no dependency install performed in audit step |
| Multi-model T2 discussion | weak/not certified | `/Users/charles/.hermes/tick-20260510-091134/discussion_result.json`; truth gate 10/10 grounded; final status `not_certified`, weak consensus |
| brain_task_orchestrator dashboard/search/selfcheck | pass | dashboard refreshed; `brainctl reindex` indexed 2593 blocks and search `SkillClaw` returns this task; `brain_task_orchestrator selfcheck --json` PASS |

## Proof Log

- 2026-05-10T17:19:59+08:00: Task created from local-brain control point.
- 2026-05-10T17:20+08:00: Evidence audit cloned `https://github.com/AMAP-ML/SkillClaw` to `/tmp/skillclaw-audit` at commit `03f7bb436ffda8ef6bad2560921e8a3ec5f54701` (`fix: improve Claude Code protocol compatibility`).
- 2026-05-10T17:20+08:00: Repo metadata observed: MIT license, created 2026-04-10, pushed 2026-04-29, updated 2026-05-10, 1272 stars, 123 forks, 16 open issues.
- 2026-05-10T17:20+08:00: Key evidence: README claims Hermes/Codex/Claude/OpenClaw support; architecture is local proxy + optional evolve server; shared storage supports local/OSS/S3; Hermes integration rewrites `~/.hermes/config.yaml` and uses `~/.hermes/skills`.
- 2026-05-10T17:20+08:00: Static risk evidence: defaults include `proxy.host: 0.0.0.0`, `proxy.port: 30000`; config can persist `llm.api_key`, `prm.api_key`, `sharing.secret_access_key`; adapters mutate Hermes/Codex/Claude/QwenPaw/IronClaw config paths; workflow engine default publish mode is direct; OpenClaw runner sets sandbox mode off.
- 2026-05-10T17:21+08:00: Local compile gate passed via `python3 -m compileall -q skillclaw evolve_server tests`; pytest skipped because not installed.
- 2026-05-10T17:11-17:19+08:00: Multi-model input state written to `/tmp/skillclaw-multimodel-state.json`; artifact at `/Users/charles/.hermes/tick-20260510-091134/discussion_result.json`. Truth gate 10/10 grounded; fanout quorum met but final discussion `not_certified` due weak consensus / unresolved advisory issues. Treat as evidence-grounded advisory, not full certification.

## Blockers / Confusions

- Unit tests were not run in audit step because `pytest` was unavailable and dependency install was intentionally avoided.
- Multi-model result is not full certified; use conservative P1 sandbox task, not direct adoption.
- Real credentials, OSS/S3, and live Hermes config are explicitly out of scope until sandbox rollback evidence exists.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-10T23:55:11+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T01:35:39+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: stale_claim_cleanup_ttl_expired

- 2026-05-11T02:07:36+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T02:12:48+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: timeout_cleanup
- 2026-05-11T22:07:13+08:00: 补齐 mission-envelope/frontmatter 流转字段；修正多模型 artifact target-binding 状态；用于恢复 selfcheck/proof-check/boundary-check 与 parallel-dispatch dry-run。
