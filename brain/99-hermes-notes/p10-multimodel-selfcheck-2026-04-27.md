P10 Multi-Model Architecture Self-Check
Timestamp: 2026-04-27T12:17:14Z
Scope: Hermes L0-L5 多模型架构，重点检查 OpenAI Codex/gpt-5.5 接入后的路由、定价、验证、多脑 quorum 与健康度。

1. Executive Summary

结论: PASS，当前多模型架构健康等级 A。
V(t): 0.9651  V_dot: 0.0005  Grade: A
main_pass_rate_7d: 0.958
real_ratio: 0.939
cron_health: 0.933 (14/15)
gateway: 1.0
self_test: 1.0 (24 checks)

关键判断:
- Codex/gpt-5.5 已作为 openai-codex provider 纳入 pricing、router、cross-patch producer 与 quorum。
- L1 router 的 exploit 路径会优先选择 gpt-5.5；select_pair 已保证 reviewer 与 producer 不同 provider。
- L2-L5 关键脚本 py_compile 通过；consensus exact/dissent 已在本轮命令验证。
- self-test 24/24 通过，route main 口径无 synthetic 污染。

2. L0-L5 Check Matrix

- [PASS] L0 trace real/main clean: main=903 synth=0 pass=0.958
- [PASS] L1 router enabled: {'enabled': True, 'candidate_models': ['gpt-5.5', 'gpt-5.4', 'claude-sonnet-4-6', 'claude-opus-4-7'], 'epsilon': 0.1, 'min_traces_per_model': 10}
- [PASS] Codex pricing registered: {'tier': 'reasoning', 'provider': 'openai-codex', 'input': 0.0, 'output': 0.0, 'access_plan': 'chatgpt_plus', 'monthly_subscription_usd': 20.0, 'quota_policy': 'unlimited_subject_to_abuse_protection', 'note': 'Codex / ChatGPT Plus 已接入；边际 token 成本按 0 计，但受 Plus/Codex 滥用防护与任务额度约束。', 'candidate_groups': ['chat', 'codegen', 'reviewer', 'hard_reasoning']}
- [PASS] Cross-patch producer Codex: {'enabled': True, 'min_patch_conf': 0.7, 'producer_model': 'gpt-5.5', 'reviewer_model': 'deepseek-v4-pro', 'max_patches': 20}
- [PASS] Quorum T1/T2 contains Codex+DeepSeek: {'T0': {'quorum': 1, 'min_quorum': 1, 'planners': ['mimo-v2.5-pro'], 'diversity': 'none', 'arbiter': None}, 'T1': {'quorum': 2, 'min_quorum': 1, 'planners': ['gpt-5.5', 'deepseek-v4-pro'], 'diversity': 'provider', 'arbiter': None}, 'T2': {'quorum': 3, 'min_quorum': 2, 'planners': ['gpt-5.5', 'deepseek-v4-pro', 'claude-opus-4-7'], 'diversity': 'provider', 'arbiter': 'claude-opus-4-7'}, 'T3': {'quorum': 3, 'min_quorum': 2, 'planners': ['claude-opus-4-7', 'gpt-5.5', 'deepseek-v4-pro', 'mimo-v2.5-pro'], 'diversity': 'provider', 'arbiter': 'claude-opus-4-7'}}
- [PASS] Router pair provider diversity: producer=gpt-5.5 reviewer=mimo-v2.5-pro same_provider=False
- [PASS] L2-L5 scripts compile: py_compile ok
- [PASS] Self-test all pass: 24/24
- [PASS] Health grade A: V=0.9651 grade=A warnings=['memory file > 2.2KB, may have ghosts', 'skill count > 80, consider reduction']

3. Current Model Economics / Routing

Default model: openai-codex / gpt-5.5
Codex pricing entry: provider=openai-codex, access_plan=chatgpt_plus, monthly_subscription_usd=20.0, marginal_rate=$0.0/$0.0 per 1M.
Cross-patch: producer=gpt-5.5, reviewer=deepseek-v4-pro, min_conf=0.7.
Quorum:
- T1: ['gpt-5.5', 'deepseek-v4-pro']
- T2: ['gpt-5.5', 'deepseek-v4-pro', 'claude-opus-4-7']
- T3: ['claude-opus-4-7', 'gpt-5.5', 'deepseek-v4-pro', 'mimo-v2.5-pro']

Router selected pair sample:
producer=gpt-5.5  reviewer=mimo-v2.5-pro  same_provider=False

4. Health Warnings / Risks

- P1: Memory 超 2.2KB，JSON 健康报告已正确暴露 warning；后续需做 ghost 清理，但不影响多模型运行。
- P1: Skill raw count=200，生态膨胀；应以 skill-steward effective count 做治理，避免加载噪声。
- P1: model-diversity-monitor 报低多样性：当前主要只跟踪 gpt-5.5 与 MiMo，DeepSeek/Claude 在真实 trace 中样本不足。
- P2: Codex Plus 是订阅/滥用防护模型，不是无约束 API；长循环需保留 MiMo/DeepSeek 降级。
- P2: Cron recent=14/15，整体正常但仍有日/周任务未在24h内运行。

5. Fixes Applied During This Self-Check

- Fixed p10-health.sh JSON mode: Python dict boolean now uses True/False, not JSON true/false.
- Fixed p10-health.sh JSON warnings: warnings are now serialized through WARNINGS_JSON, so memory/skill-count warnings no longer disappear.
- Fixed consensus-check.py bare except in detect_type: now catches json.JSONDecodeError and SyntaxError explicitly.
- Updated p10-architecture-self-check skill with the p10-health JSON pitfall.
- Renumbered multi-model-architecture pitfall list after previous Codex/router additions.

6. P9 Follow-Up Backlog

P0: None.
P1: Improve diversity sampling: ensure DeepSeek reviewer and Claude arbiter produce enough real traces for diversity monitor; avoid only Codex/MiMo being visible.
P1: Skill ecosystem governance: raw SKILL.md count=200; run skill-steward effective-count cleanup separately.
P1: Memory cleanup: memory_bytes=2790 > 2200, do ghost cleanup separately.
P2: Add Codex quota guard: subscription marginal cost is zero, but quota_policy=unlimited_subject_to_abuse_protection; router should retain fallback if Codex throttles.

7. Raw Evidence Pointers

- p10-health.sh --json: V=0.9651, warnings=['memory file > 2.2KB, may have ghosts', 'skill count > 80, consider reduction']
- self-test.py: 24/24 passed
- model-router.py status: pricing-aware candidates include gpt-5.5 in codegen/reviewer/chat; pricing entry also includes hard_reasoning.
- cross-patch.py status: producer=gpt-5.5, reviewer=deepseek-v4-pro.
- eval-harness.py status: baseline 85 prompts, staging pending router/proposals.
