---
type: review
status: draft
created: 2026-05-09T11:40:00+08:00
project: hermes-pua-loop-multimodel-round1
tags: [pua-loop, multi-model, agent-s, agent-reach, idle-runner, hermes-native]
---

# 2026-05-09 PUA-loop Round 1 — Agent-S / Agent-Reach / idle-runner 全线推进

## Scope

- Line A: `simular-ai/Agent-S` 固定 commit `5caa76cb19c6a6b947a524f74995c45848c2efbc`，做证据优先审计，提取 Hermes 技能树可借鉴能力。
- Line B: 在本地大脑任务池上新增只读 idle detector + 风险路由最小切片。
- Line C: `Panniantong/Agent-Reach` 固定 commit `17624268a059ccfb23eba8a2ba50f9f92c8dc0ca`，给出 Hermes-native 优化方案；默认不 vendor/不安装第二套栈。

## Evidence Boundary

Model agreement is provenance only. This round certifies the pinned repository audits, idle-runner read-only slice, and listed deterministic gates; it does not certify importing Agent-S/Agent-Reach runtime code, enabling GUI automation, credential/cookie automation, or automatic task execution.

## Deterministic evidence

- Repo clone/fixed commits: `~/.hermes/artifacts/pua-loop-multimodel-round1/repo_commits.txt`
- Agent-S compile gate: `python3 -m compileall -q .../Agent-S/gui_agents` → PASS
- Agent-Reach compile gate: `python3 -m compileall -q .../Agent-Reach/agent_reach .../Agent-Reach/tests` → PASS
- Hermes idle-runner implementation gate:
  - `python3 -m py_compile ~/.hermes/scripts/brain_task_idle_runner.py ~/.hermes/scripts/test_brain_task_idle_runner.py` → PASS
  - `python3 ~/.hermes/scripts/test_brain_task_idle_runner.py` → PASS
- Production idle detector dry run: `python3 ~/.hermes/scripts/brain_task_idle_runner.py --json --write-state` → PASS, `next_action=observe_only`, `active_count=3`, no task mutation.

## Line A — Agent-S audit

### Verified repo facts

- Repo: `https://github.com/simular-ai/Agent-S.git`
- Commit pinned: `5caa76cb19c6a6b947a524f74995c45848c2efbc`
- License: Apache-2.0 (`LICENSE` Apache License Version 2.0)
- Package: `setup.py` publishes `gui-agents` v0.3.2, Python `>=3.9, <=3.12`, with GUI/LLM dependencies including `openai`, `anthropic`, `pyautogui`, OCR, platform-specific pyobjc/pywinauto.
- Code shape: `gui_agents/s1`, `s2`, `s2_5`, `s3`, OSWorld setup, OpenClaw integration skill.

### Evidence-backed capabilities worth borrowing

1. **Hierarchical manager/worker split**
   - `AgentS2` wires a `Manager` planner and `Worker` executor during reset (`agent_s.py:173-190`).
   - Hermes mapping: keep P10/P9 planning separate from P7/P8 bounded execution; do not let an execution runner invent scope.

2. **DAG planning as executable control-plane object**
   - Agent-S manager has a dedicated DAG translator (`manager.py:47-50`, `manager.py:225-257`).
   - The prompt requires connected DAG, no completed subtasks, no repeated/optional steps (`procedural_memory.py:142-178`).
   - Hermes mapping: `blocked_by` should be a first-class frontmatter DAG edge for task-pool routing; idle-runner should block if `blocked_by` exists.

3. **Reflection loop for trajectory/cycle detection**
   - Worker creates a reflection agent (`worker.py:69-72`) and injects reflection into subsequent action generation (`worker.py:157-194`).
   - Reflection prompt explicitly detects repeated cycles/no progress (`procedural_memory.py:110-123`).
   - Hermes mapping: PUA-loop should treat repeated tool failures as a route-change signal, not retry same command.

4. **Episodic + narrative memory split**
   - Knowledge base persists `episodic_memory.json`, `narrative_memory.json`, `embeddings.pkl` (`knowledge.py:35-44`).
   - It retrieves narrative task experience and episodic subtask experience via embeddings (`knowledge.py:161-233`).
   - Hermes mapping: user profile/memory should remain compact; detailed procedures belong to skills; task-specific proof belongs to task notes/reviews.

5. **Action grounding with strict single-action output**
   - Worker prompt requires exactly one grounded action and disallows invented methods (`procedural_memory.py:47-60`).
   - Actual parsing sanitizes and extracts the first agent function, falling back to `agent.wait(1.0)` on parsing errors (`worker.py:220-230`).
   - Hermes mapping: autonomous runners should emit one bounded action envelope per tick, with safe fallback to handoff rather than broad shell execution.

### Not adopted / risks

- Do not import Agent-S runtime into Hermes: GUI automation + pyautogui/OCR/desktop control has a much larger blast radius than Hermes local task pool.
- Do not copy prompt line `My computer's password is 'password'` (`procedural_memory.py:61`) into Hermes; treat it as a benchmark/runtime artifact and a red-line for real agents.
- Do not use `eval(plan_code)` style execution (`worker.py:226-230`) in Hermes runners. Hermes should keep explicit allowlists and proof-gated transitions.

### Hermes skill-tree proposal

- Add/maintain a conceptual route under existing skills rather than vendor code:
  - `multi-model-thinking`: keep evidence-first certification.
  - `hermes-workflow-orchestrator`: claim/handoff/proof state machine.
  - `loop`/`pua`: repeated-failure route switching.
  - `browser-harness-integration` + UI skills: GUI/browser validation.
- New skill is not mandatory this round; the reusable Agent-S patterns are captured here and in the idle-runner implementation.

## Line B — idle-runner implementation

### Landed P1 slice

Created:

- `~/.hermes/scripts/brain_task_idle_runner.py`
- `~/.hermes/scripts/test_brain_task_idle_runner.py`

Behavior:

- Read-only detector; never executes Markdown, never claims, never marks done.
- Kill switch: `HERMES_LOCAL_BRAIN_IDLE_RUNNER`; default disabled.
- Routes each active/pending task by `risk`, `execution_mode`, and `blocked_by`.
- Blocks idle handoff when active `claimed/running` leases exist.
- High risk or manual mode routes to manual gate.
- `blocked_by` frontmatter routes to DAG blocker.
- Optional `--write-state` writes detector snapshot only, no task mutation.

Production observation on this round:

- `active_count=3` because all three PUA-loop tasks were claimed/running by `hermes-pua-loop`.
- `idle_decision=busy_or_disabled` because kill switch is off and active work exists.
- `next_action=observe_only`; no claim/execute/done.

### Route results for current task pool

- Agent-S task: `risk=medium`, `execution_mode=read_only_review`, eligible in principle, blocked now by active running state.
- idle-runner task: `risk=medium`, `execution_mode=handoff_only`, eligible in principle, blocked now by active running state.
- Agent-Reach task: `risk=medium`, `execution_mode=read_only_review`, eligible in principle, blocked now by active running state.

## Line C — Agent-Reach audit

### Verified repo facts

- Repo: `https://github.com/Panniantong/Agent-Reach.git`
- Commit pinned: `17624268a059ccfb23eba8a2ba50f9f92c8dc0ca`
- License: MIT.
- Package: `agent-reach` v1.4.0 in `pyproject.toml`, Python `>=3.10`, dependencies include `requests`, `feedparser`, `python-dotenv`, `pyyaml`, `rich`, `yt-dlp`; optional browser/cookie/MCP extras.
- Structure: `agent_reach/channels/*`, `doctor.py`, `config.py`, `cli.py`, `integrations/mcp_server.py`, packaged skill files and guides.

### Evidence-backed capabilities worth borrowing

1. **Channel capability doctor**
   - Doctor iterates all channels and emits `status`, `message`, `tier`, `backends` (`doctor.py:12-24`).
   - Report groups zero-config, configured optional, and inactive optional channels (`doctor.py:41-88`).
   - Hermes mapping: build/extend Hermes capability doctor around available tools, credentials present/absent, channel health, and fallback route.

2. **Config secrecy / permissions**
   - Config writes credentials with restricted `0o600` permissions (`config.py:48-66`).
   - Config display masks keys/tokens/password/proxy (`config.py:101-109`).
   - Doctor warns if config is group/world readable (`doctor.py:90-106`).
   - Hermes mapping: existing Gateway/config pitfalls should grow a `secret/permission doctor`, but never print raw values.

3. **Safe/dry-run UX for installers**
   - CLI has `install --safe` and `install --dry-run` (`cli.py:61-70`).
   - Install handler branches dry-run/safe-mode before system changes (`cli.py:173-236`).
   - Hermes mapping: any Hermes setup/update helper should include dry-run by default for risky changes.

4. **Intent-to-channel matrix**
   - README exposes platform support by install/config boundary.
   - Code enforces per-channel modules (`channels/base.py` and `channels/*.py`).
   - Hermes mapping: `chinese-platforms` skill is the right native route; patch added Agent-Reach borrowing boundary and doctor/secret rules.

### Not adopted / risks

- Do not install Agent-Reach globally or vendor it into Hermes by default.
- Do not copy Cookie ingestion flows as automatic behavior; user-provided cookies are sensitive and should remain explicit/manual.
- Do not add paid/free platform tooling without command presence checks and permission doctors.

### Hermes optimization roadmap

- P0: Keep `chinese-platforms` skill as native route matrix; patch with Agent-Reach boundary/doctor/secret rules. **Done this round.**
- P1: Add Hermes capability doctor script that reports installed platform CLIs/MCP servers, missing optional tools, and redacted credential presence.
- P1: Add docs/capability drift lint: skill route mentions `xhs`, `bili`, `rdt`, etc. must match actual command availability or explicit setup note.
- P2: Add optional safe-mode setup helpers for selected platform tools, but require explicit user confirmation before credential/cookie operations.

## Round 1 issue ledger

- I-001: Agent-S GUI runtime is high-blast-radius. Resolution: borrow control-plane patterns only; do not import runtime.
- I-002: Agent-S prompt contains benchmark password artifact. Resolution: explicitly not adopted; Hermes secrets policy forbids such prompt content.
- I-003: Agent-Reach cookie/proxy handling is sensitive. Resolution: native route matrix only; doctor redacts values and does not auto-login.
- I-004: idle-runner could become an executor by accident. Resolution: implementation is read-only, kill-switch-gated, and tests prove no task mutation.

## Certification status

Formal T3 four-model ratification: **CERTIFIED**.

- State file: `/Users/charles/.hermes/artifacts/pua-loop-multimodel-round1/round1-cert-state.json`
- Discussion result: `/Users/charles/.hermes/tick-20260509-033926/discussion_result.json`
- Certification manifest: `/Users/charles/.hermes/tick-20260509-033926/final/certification_manifest.json`
- Models: Claude Opus 4.7 / GPT-5.5 / DeepSeek v4 Pro / MiMo v2.5 Pro
- Rounds used: 1
- Truth gate: `evidence_coverage=1.0`, `verified_claim_count=8/8`, `unsupported_high_severity_claim_ids=[]`, `contradicted_high_severity_claim_ids=[]`
- Discussion status: `certified`, `can_claim_complete_certification=true`

Post-review hardening after independent reviewer suggestions:

- Added subprocess diagnostic redaction for `api_key/token/secret/password/passwd/proxy/auth_token/ct0` in idle-runner error payloads.
- Added regression tests for `--write-state` no task mutation, scalar `blocked_by`, multiline `blocked_by`, and redaction.
- Added skill guidance: never paste raw Cookie/API key/token into prompts/logs/shell history/task notes; prefer permission-restricted config files.
