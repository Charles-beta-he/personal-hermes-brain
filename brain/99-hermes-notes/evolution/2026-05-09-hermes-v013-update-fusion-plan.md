# Evolution Advisory: Hermes v0.13/update 新增功能与现有体系融合方案

Date: 2026-05-09
Type: methodology-migration | architecture-advisory | post-update-fusion
Scope: Hermes private fork / Level 0 advisory artifact
Status: truth_grounded_advisory; not_certified_for_autonomous_execution; P0 verifier drift fixes + router/quota/autonomy enforcement gates applied locally; CLI gate consistency fixed; router rebalance plan + quota observability evidence + reusable caller guard added; local task-pool autorun now calls guard_or_raise before claim/handoff; latest PUA-loop resolved live diversity dominance and DeepSeek exact-quota downgrade, remaining blocker is provider quota confidence for Claude/MiMo/openai-codex

## 1. Evidence-first self-check result

Evidence collected:
- Hermes repo: /Users/charles/.hermes/hermes-agent
- Version: Hermes Agent v0.13.0 (2026.5.7)
- Git state: main...origin/main [ahead 5], recent sync through a7e7921db and 78b0008f4
- Release evidence: /Users/charles/.hermes/hermes-agent/RELEASE_v0.13.0.md lines 1-64
- Deterministic gates:
  - self-test.py: 70/70 passed, ALL PASS after adding model-diversity/autonomy/router/quota/write-guard regression coverage; model-diversity/autonomy gate regression suite is now 10/10.
  - skill-steward graph: OK, cycles=0, depth_max=4
  - cron: gateway running, 22 enabled jobs; 20 healthy, 2 current bad, 1 first-run-pending at latest p10-health sample
  - route_store: pass_rate≈0.96, synthetic=0
  - eval-harness: 85 prompt baseline pass_rate=100%
- Initial contradictions / blockers found:
  - p10-health reported V=0.738 grade C and self_test=0.0 while live self-test was 66/66; root cause was parser/check-count drift (self_test_count=65).
  - hermes doctor previously reported xiaomi invalid API key, while model-router probe reported MiMo available; provider-health reconciliation remains needed before budget handoff.
  - model-diversity initially labeled healthy despite gpt-5.5 498x, DeepSeek 1x, MiMo 1x; dominance detection was missing.
  - Prior T3 run without claims/evidence was not complete certification.
- Local P0 verifier/enforcement fixes applied in this tick:
  - /Users/charles/.hermes/scripts/p10-health.sh now parses `Self-Test Results: N/N passed` instead of raw checkmark count and reports model_diversity/model_quota/model_router readiness separately; latest verified V=0.9738 grade A, self_test=1.0, self_test_count=70.
  - /Users/charles/.hermes/scripts/model-diversity-monitor.py now uses python3 shebang, supports --json/--gate, and fail-closes with exit 2 when one model handles >80% of tracked calls; latest real gate detects gpt-5.5 dominant_share=0.996.
  - /Users/charles/.hermes/scripts/autonomy-precondition.py adds a fail-closed readiness gate for dispatch-hint, budget-handoff, and autonomous-execution modes.
  - /Users/charles/.hermes/scripts/test_model_diversity_and_autonomy_gates.py adds fixture-based regression tests for single-model dominance, balanced usage, quota/diversity fail-close, and explicit autonomy enable-file enforcement.
  - /Users/charles/.hermes/scripts/model_quota.py now exposes `confidence-gate --json --gate`, converting unknown/unobservable/low/exhausted quota into FAIL_CLOSED for budget/autonomy readiness while keeping low-risk routing semantics separate; the gate now also emits `observability_evidence` with exact/estimated/unknown/unobservable/stale/low-confidence counts and provider-specific refresh actions.
  - /Users/charles/.hermes/scripts/model-router.py now exposes `readiness --json --gate`, consuming dominance + quota-confidence evidence and returning a rebalance_required/fail-closed promotion gate; the gate now emits a deterministic non-mutating `rebalance_plan` with required non-dominant calls and per-model targets.
  - /Users/charles/.hermes/scripts/autonomy-write-guard.py adds a reusable write-surface guard for goal, Kanban worker, watchers, Teams, Google Workspace, gateway fanout, and cron-no-agent side effects: known surface + explicit allowlist + explicit mode + autonomy-precondition PASS; callers can use `guard_or_raise(...)` to get fail-closed JSON evidence as a PermissionError before any side effect.
  - /Users/charles/.hermes/scripts/self-test.py now compiles the gate scripts and runs the 10/10 model-diversity/autonomy/write-guard regression tests, including CLI compatibility for `autonomy-precondition.py --json --gate`.
  - /Users/charles/.hermes/scripts/test_cross_patch_safety.py now isolates the explicit-producer-unavailable selector test from the live router, fixing a false negative in full self-test.
- Remaining blockers:
  - Model diversity enforcement is fail-closed for readiness/promotion consumers, and model-router readiness now emits rebalance_required plus eligible non-dominant alternates. The live route history still remains gpt-5.5-dominant until enough real non-dominant calls are routed and recorded.
  - Provider quota confidence gate now exists and reports 4/4 T3 confidence failures (Claude/DeepSeek/MiMo unknown, gpt-5.5 unobservable). budget-handoff and autonomous-execution intentionally fail closed.
  - Autonomous execution remains disabled unless p10 health, diversity, quota confidence, router readiness, explicit allowlist, and an explicit local enable file all pass; write surfaces must call autonomy-write-guard before performing side effects.

Multi-model artifacts:
- Initial grounded T3 state: /tmp/hermes-update-fusion-state-grounded.json
- Initial grounded T3 tick: /Users/charles/.hermes/tick-20260509-045608
- Post-P0 review state: /tmp/hermes-update-fusion-state-after-p0.json
- Post-P0 review tick: /Users/charles/.hermes/tick-20260509-052609
- Result: fanout_quorum_met 4/4 and truth gate grounded, but discussion_result status=not_certified.
- Initial not-certified reasons: agreement_matrix=0.65 < 0.85, approvals=0/4, reject votes present, 19 unresolved severity>=3 issues/evidence requests.
- Post-P0 not-certified reasons: agreement_matrix=0.65 < 0.85, approvals=0/4, reject votes present, 24 unresolved severity>=3 issues/evidence requests. The extra issues are mostly enforcement follow-ups: router skew cap, quota probe confidence, autonomy precondition hook, and line-level matrix verification.
- Final P0 enforcement review state: /tmp/hermes-update-fusion-p0-enforcement-review-state.json
- Final P0 enforcement T3 tick: /Users/charles/.hermes/tick-20260509-071429
- Final P0 certification manifest: /Users/charles/.hermes/tick-20260509-071429/final/certification_manifest.json
- Final P0 truth gate: grounded, can_certify_truth=true, evidence_coverage=1.0, verified_claim_count=6/6.
- Final P0 ratification result: status=not_certified, rounds_used=2, agreement_matrix=0.65/0.65/0.65, approvals=0/4, reject_count=0, unresolved severity>=3 issue count=4.
- Final P0 manifest blockers: ratification quorum not met, missing/non-true best_within_constraints, agreement below 0.85, unresolved severity>=3 issues, and empty merged patches without no_action_certification despite planner_patch_summary=implementation_required.

Interpretation:
- Truth grounding is good enough for an advisory fusion plan.
- Deterministic health is now green after local P0 verifier fixes; latest self-test remains 70/70 ALL PASS and p10-health remains grade A.
- Readiness/promotion gates now fail closed on current model-diversity, quota-confidence, router-readiness, and write-surface evidence instead of allowing nominal certification.
- This is still NOT safe to call autonomous-execution or implementation certification until the underlying router/quota issues are corrected and a fresh T3 discussion passes N-1 ratification.

## 2. Fusion principle

Do not import upstream v0.13 features as parallel mechanisms.
Map each upstream capability to the existing private architecture:

Existing spine:
trace -> bandit/router -> agent_protocol v2 -> ensemble-vote -> cross-patch/consensus -> consult_models
LX: model_health + model_quota
Control plane: Skill Graphs 2.0 + canonical brain vault + cron/taskpool safe ticks + private-fork Level 0/1/2 governance

Rule:
- Upstream capability is an interface/surface unless it provides a strictly better primitive.
- Existing private pipeline remains the source of truth for routing, certification, local brain state, and autonomous-loop safety.
- Autonomous execution requires kill switch + budget + proof + rollback + deterministic gate before multi-model ratification.

## 3. New capability -> existing mechanism integration matrix

| v0.13/update capability | Existing mechanism to bind to | Adoption mode | Verification gate | Risk |
|---|---|---|---|---|
| Durable Kanban / kanban specify | brain_task_orchestrator + brain_task_dispatch_tick + local brain task pool | Use as UI/board surface; do not create a second task truth source | brain_task_orchestrator selfcheck/proof-check; cron safe tick; no direct done without proof | duplicate task state / uncontrolled workers |
| /goal persistent target | agent_protocol v2 + router dispatch hint + task contract | Dispatch hint only at first; no autonomous execution by default | goal contract has expected_files/allowed_globs/budget; proof-gated review->done | scope creep / endless Ralph loop |
| no_agent cron | Existing local-brain-task-dispatch-safe-tick already uses no-agent | Adopt as canonical watchdog pattern | cron list/status + script stdout semantics + empty stdout silent | accidental agent recursion |
| cron deliver=all fanout | Gateway notification layer only | P1, explicit allowlist; never default for high-risk tasks | channel allowlist + dry-run delivery | message spam / cross-channel leakage |
| Checkpoints v2 | private-fork Level 0/1/2 rollback + /rollback | Treat as rollback substrate for code/file edits | checkpoints status/prune + self-test after rollback | false confidence if not scoped |
| post-write delta lint | deterministic write gate before build/test | Adopt immediately for script/config changes | write_file/patch lint + py_compile/json.tool/yaml parse | lint false positives but low risk |
| provider plugins | existing model-router + model_quota + provider probe | Extend providers as supply surface, not router replacement | model-router probe + quota confidence + diversity floor | parallel provider health model |
| model health / quota | LX model_health/model_quota | Merge signals; fail closed on low confidence for expensive T3 | quota_confidence threshold; unavailable provider transition log | budget overrun / silent fallback |
| i18n/locales | CLI/gateway UX layer | Adopt as upstream UX, no private fork needed | smoke CLI/gateway commands | low |
| gateway auto-resume | existing session durability + cron watchdog | Adopt, but ensure stale notification tombstone handling | gateway status + session resume smoke | duplicated sessions after restart |
| platform allowlists | gateway safety layer | Adopt as required default for fanout delivery | config audit allowed_* fields | leakage to wrong chat/channel |
| dashboard plugins/profiles | Agent COS/control-plane dashboard | Link as UI/control surface, not canonical source | dashboard status + local brain dashboard selfcheck | split-brain UI state |
| Curator archive/prune/list | Skill Graphs 2.0 + skill-steward | Curator as proposer, skill-steward as deterministic gate | skill-steward --graph-check --json, no bundled/hub mutation | over-pruning useful skills |
| web search split / Brave/DDGS/SearXNG | evidence-source policy under router | P1: route by evidence type and cost; keep source provenance | search backend health + evidence bundle supports claim IDs | ungrounded web claims |
| MCP SSE/OAuth/media | native-mcp + evidence request fulfillment loop | Use as tool transport; keep truth gate claim-linked | MCP test + claim/evidence supports linkage | tool output treated as truth without grounding |
| API server session memory | canonical brain vault + memory providers | Bind session-key memory to local brain policy; indexes are derived caches | brainctl sync/reindex/search + memory provider status | split-brain memory |
| ACP /steer /queue / image attachments | IDE/control-plane input surface | P2: use for steering, not bypassing task contracts | ACP smoke + command queue state | out-of-band scope drift |
| TUI model picker/status improvements | CLI UX | Adopt upstream | TUI smoke only | low |
| optional watchers skill | no_agent watchdog + feeds/blogwatcher | Opt-in only; write silent unless change detected | no-agent script pattern + watermark | noisy cron / duplicate monitors |
| Windows/native support | portability hardening | Accept upstream; no macOS action except not breaking scripts | CI/lint only when touching cross-platform code | low for current macOS |
| Teams pipeline/MSGraph | messaging/gateway optional platform | P2 deferred until needed | platform token + delivery dry-run | external side effects |
| Google Workspace write ops | productivity tool with side effects | P2, require explicit confirmation for writes | dry-run/read-only first, permission check | unintended remote write |

## 4. Adoption order

P0 — completed/enforced locally in this tick
1. Fix p10-health self-test parser/count drift.
   - Target: /Users/charles/.hermes/scripts/p10-health.sh.
   - Verified: bash -n passes; self-test 70/70; p10-health self_test=1.0, self_test_count=70, V=0.9738 grade A.
2. Fix model-diversity false healthy label for single-model dominance.
   - Target: /Users/charles/.hermes/scripts/model-diversity-monitor.py.
   - Verified: py_compile passes; --json reports dominant_share=0.996 and dominance_warning=true.
3. Promote model-diversity warning into a fail-closed readiness gate.
   - Target: /Users/charles/.hermes/scripts/model-diversity-monitor.py --gate.
   - Verified: live skew exits 2; fixture-balanced usage exits 0; regression tests pass.
4. Add fail-closed autonomy precondition gate.
   - Target: /Users/charles/.hermes/scripts/autonomy-precondition.py.
   - Dispatch-hint can pass with p10 health only; budget-handoff requires diversity + quota confidence + router readiness; autonomous-execution additionally requires explicit local enable file.
   - Verified: dispatch-hint PASS; `--json --gate` flags accepted for CLI consistency; budget-handoff FAIL_CLOSED on diversity/quota/router; autonomous-execution FAIL_CLOSED on diversity/quota/router/enable-file.
5. Materialize this integration matrix as Level 0 advisory artifact and keep not_certified caveat.
   - Target: this note and /tmp evidence state files.
   - Verified: file exists, claims/evidence linked, no vendor-core mutation.
6. Add quota-confidence reconciliation gate.
   - Target: /Users/charles/.hermes/scripts/model_quota.py.
   - Verified: `confidence-gate --json --gate` returns FAIL_CLOSED on current T3 low-confidence evidence; fixture exact snapshot PASS covered by tests.
7. Add router readiness/rebalance promotion gate.
   - Target: /Users/charles/.hermes/scripts/model-router.py.
   - Verified: `readiness --json --gate` returns FAIL_CLOSED with rebalance_required=true under current dominance/quota evidence; pass/fail fixtures covered by tests.
8. Add write-surface guard for side-effecting integrations.
   - Target: /Users/charles/.hermes/scripts/autonomy-write-guard.py.
   - Verified: dry-run dispatch-hint can pass; write without allowlist or failing autonomy precondition fails closed; write guard propagates the updated budget_handoff policy string.

P0 — remaining reality blockers before autonomous/budget-handoff certification
1. Turn provider quota confidence from current FAIL_CLOSED into observable PASS where genuinely available.
   - Current gate: `model_quota.py confidence-gate --json --gate` fails closed with failure_count=4.
   - Current observability evidence: exact=0, estimated=0, unknown=3, unobservable=1, low_confidence=4; refresh_actions include `manual_budget_confirmation_or_lower_risk_tier`, `probe_deepseek_balance`, and `record_provider_response_headers`.
   - Next evidence needed: real balance/header/probe snapshots or an explicitly accepted policy for subscription/unobservable providers.
2. Make route history actually recover from gpt-5.5 dominance.
   - Current gate: `model-router.py readiness --json --gate` fails closed with failures=dominance_warning,diversity_gate_failed,quota_confidence_failed and rebalance_required=true.
   - Current rebalance plan: required_non_dominant_calls=123 over window=500; per-model targets currently distribute across Claude/DeepSeek/GPT-5.4/MiMo eligible alternates; no automatic route mutation is performed.
   - Next evidence needed: bounded warm-up routing to eligible non-dominant alternates, then rerun diversity gate until dominant_share <=0.8.
3. Replace advisory wrappers with caller-level enforcement at every write-capable surface.
   - Current gate: `autonomy-write-guard.py` exists and fails closed without allowlist/precondition; `guard_or_raise` now gives callers a simple fail-closed API.
   - Next evidence needed: Kanban worker, /goal execution, watchers, Teams/Google Workspace, gateway fanout call this guard before side effects; dry-run/read-only remains default.

P1 — safe fusion after P0
1. Kanban as board/UI over local brain task pool; no second source of truth.
2. Curator as proposer; skill-steward remains deterministic graph gate.
3. Web-search split as evidence-source router; all claims require supports IDs.
4. Provider plugins merged into LX health/quota; no parallel router.
5. Dashboard/plugins/profiles bound to Agent COS dashboard.
6. Post-write lint as default deterministic write gate.

P2 — deferred / opt-in side-effect surfaces
1. /goal autonomous handoff: only after task contract + budget + kill switch + rollback.
2. watchers skill: only no-agent, watermark, silent-on-empty.
3. Teams/MSGraph/Google Workspace writes: dry-run/read-only first, explicit approval for writes.
4. ACP /steer /queue and image attachments: useful, but must not bypass task contracts.
5. Windows-native support: accept upstream, only test when touching cross-platform paths.

## 5. Multi-model dissent ledger

Unresolved blockers from T3 discussion and current deterministic gates:
- p10-health false-negative verifier gap — resolved locally; self-test summary parser now covered by self-test.
- model diversity monitor under-detects gpt-heavy skew — resolved locally at monitor/readiness-gate layer; router readiness now blocks promotion and emits rebalance_required plus a non-mutating rebalance_plan, but live dominance remains unresolved until routing history is balanced.
- provider health contradiction / quota confidence — enforcement gate resolved locally and now exposes observability_evidence; evidence remains failing because model_quota reports exact=0/estimated=0/unknown=3/unobservable=1 with low confidence for all four T3 models, so budget-handoff/autonomous modes fail closed.
- autonomy execution preconditions — precondition + write-surface guard exist and fail closed; `guard_or_raise` gives caller integrations a direct API, but write-capable callers still need explicit guard invocation before any side effects.
- current advisory patches are now concrete Level 0 verifier/gate scripts, but they are not a full implementation certification of upstream v0.13 adoption.
- more evidence requested for exact model-router balancing policy, quota probes, brain task kill-switch implementation, and fresh post-gate T3 artifact internals.

Decision:
- Do not claim `certified`.
- Use `not_certified_advisory` until live router/quota/readiness gates pass and a fresh T3 discussion returns agreement >=0.85 with no severity>=3 unresolved blockers.

## 6. Verification commands for next implementation tick

```bash
python3 ~/.hermes/scripts/self-test.py
bash ~/.hermes/scripts/p10-health.sh --json
python3 ~/.hermes/scripts/model-diversity-monitor.py --json --gate
python3 ~/.hermes/scripts/autonomy-precondition.py --mode dispatch-hint --json --gate
python3 ~/.hermes/scripts/autonomy-precondition.py --mode budget-handoff --json --gate
python3 ~/.hermes/scripts/model_quota.py confidence-gate --json --gate
python3 ~/.hermes/scripts/model-router.py readiness --json --gate
python3 ~/.hermes/scripts/autonomy-write-guard.py --surface google-workspace --operation write --mode budget-handoff --json --gate
python3 ~/.hermes/scripts/test_model_diversity_and_autonomy_gates.py
python3 ~/.hermes/scripts/test_model_quota.py
python3 ~/.hermes/scripts/test_model_router_quota.py
python3 ~/.hermes/scripts/skill-steward.py --graph-check --json
python3 ~/.hermes/scripts/model-router.py probe
python3 ~/.hermes/scripts/model_quota.py status --json
hermes cron status
hermes cron list
```

Fresh T3 certification command after P0 fixes:

```bash
python3 ~/.hermes/scripts/consult_models.py run /tmp/hermes-update-fusion-p0-enforcement-review-state.json \
  --tier T3 --quorum 4 --discussion --max-rounds 2 --keep
```

Acceptance for certification:
- truth_status=grounded, evidence_coverage=1.0
- discussion_result.status in certified/certified_with_minor_risks
- agreement_matrix min >=0.85
- approvals >= N-1, reject_count=0
- unresolved severity>=3 issue count = 0
- can_claim_complete_certification=true


## 6.1 Latest resume verification evidence

Resume tick evidence after CLI gate consistency fix:
- `python3 -m py_compile ~/.hermes/scripts/autonomy-precondition.py ~/.hermes/scripts/autonomy-write-guard.py ~/.hermes/scripts/test_model_diversity_and_autonomy_gates.py`: exit 0.
- `python3 ~/.hermes/scripts/test_model_diversity_and_autonomy_gates.py`: 9/9 OK.
- `python3 ~/.hermes/scripts/autonomy-precondition.py --mode budget-handoff --json --gate`: exit 2, status=FAIL_CLOSED, failed_required_checks include model_diversity_gate, quota_confidence, router_readiness.
- `python3 ~/.hermes/scripts/self-test.py`: 70/70 passed, ALL PASS.
- `bash ~/.hermes/scripts/p10-health.sh --json`: exit 0, V=0.9738, grade=A, self_test=1.0, self_test_count=70; autonomy certification blockers remain surfaced as model_diversity_gate=false, model_quota_confidence_gate=false, model_router_readiness_gate=false, model_router_rebalance_required=true.

Interpretation: the resume work fixed an actual CLI consistency gap (`--json --gate` rejected by autonomy-precondition), but did not and should not weaken the fail-closed status. This remains a truth-grounded advisory / not-certified autonomy state.

## 6.2 Latest P0 fusion slice verification evidence

Verification timestamp: 2026-05-09T15:43:00Z.

Additional local slice landed after the resume tick:
- Router readiness now includes a deterministic, non-mutating `rebalance_plan` rather than only `rebalance_required=true`.
  - Current live evidence: dominant_model=gpt-5.5, dominant_share=1.0, current_dominant_calls=500/500.
  - Current plan: `required_non_dominant_calls=125`; per-model targets are distributed across eligible non-dominant alternates; `automatic_rebalance_performed=false` and `route_mutation_allowed=false` remain explicit.
  - Regression added: parseable non-zero model-diversity gate output is no longer collapsed to `diversity_report_unavailable`; router readiness now preserves `dominance_warning` + `diversity_gate_failed` + `diversity_monitor_nonzero_exit` as actionable recovery evidence, and accepts the documented `route_diversity_signals` list/dict shape drift.
- Quota confidence now includes `observability_evidence` so budget/autonomy reviewers can distinguish unknown, unobservable, stale, malformed, and low-confidence states.
  - Current live evidence: exact=0, estimated=0, unknown=3, unobservable=1, stale=4, low_confidence=4.
  - Current refresh actions: `manual_budget_confirmation_or_lower_risk_tier`, `probe_deepseek_balance`, `record_provider_response_headers`.
- Write-surface guard now exposes `guard_or_raise(surface, operation, mode, allowlist_path=None)` for caller-level integration. It returns the evidence object on PASS and raises PermissionError with the same FAIL_CLOSED JSON on failure.

Commands run in this slice:
- `python3 -m py_compile ~/.hermes/scripts/model_quota.py ~/.hermes/scripts/model-router.py ~/.hermes/scripts/autonomy-precondition.py ~/.hermes/scripts/autonomy-write-guard.py ~/.hermes/scripts/model-diversity-monitor.py ~/.hermes/scripts/brain_task_multimodel_loop_runner.py ~/.hermes/scripts/test_model_quota.py ~/.hermes/scripts/test_model_router_quota.py ~/.hermes/scripts/test_model_diversity_and_autonomy_gates.py ~/.hermes/scripts/test_brain_task_multimodel_loop_runner.py`: exit 0.
- `python3 ~/.hermes/scripts/test_model_quota.py`: 26/26 OK.
- `python3 ~/.hermes/scripts/test_model_router_quota.py`: 27/27 OK.
- `python3 ~/.hermes/scripts/test_model_diversity_and_autonomy_gates.py`: 10/10 OK.
- `python3 ~/.hermes/scripts/test_brain_task_multimodel_loop_runner.py`: PASS.
- `python3 ~/.hermes/scripts/self-test.py`: 70/70 passed, ALL PASS.
- `bash ~/.hermes/scripts/p10-health.sh --json`: exit 0, V=0.9803, grade=A; still surfaces model_diversity_gate=false, model_quota_confidence_gate=false, model_router_readiness_gate=false, model_router_rebalance_required=true, with model_router_failures=dominance_warning,diversity_gate_failed,quota_confidence_failed.
- `python3 ~/.hermes/scripts/model_quota.py confidence-gate --json --gate`: exit 2 by design; status=FAIL_CLOSED with failure_count=4 and observability evidence above.
- `python3 ~/.hermes/scripts/model-router.py readiness --json --gate`: exit 2 by design; status=FAIL_CLOSED with failures=dominance_warning,diversity_gate_failed,quota_confidence_failed and rebalance_plan above.
- `python3 ~/.hermes/scripts/autonomy-precondition.py --mode budget-handoff --json --gate`: exit 2 by design; failed_required_checks=model_diversity_gate,quota_confidence,router_readiness.
- `python3 ~/.hermes/scripts/autonomy-write-guard.py --surface google-workspace --operation write --mode budget-handoff --json --gate`: exit 2 by design; failed_required_checks=surface_allowlisted,autonomy_precondition.
- `python3 ~/.hermes/scripts/ratification_gate.py --json`: exit 2; deterministic_gate_status=PASS, but ratification_status=NOT_CERTIFIED due to agreement below 0.85, insufficient approvals, prior reject votes, and unresolved severity>=3 issues.

Interpretation: this slice improves fusion safety by making the recovery plan and quota evidence auditable, and by giving real callers a guard API. It does not certify autonomous execution. The correct status remains `truth_grounded_advisory` and `not_certified_for_autonomous_execution` until live route/quota evidence passes and a fresh scoped ratification gate certifies the final state.

## 6.3 Caller-level write guard integration evidence

Verification timestamp: 2026-05-09T08:32:40Z.

Additional local slice landed after 6.2:
- `brain_task_orchestrator.py auto-claim-and-handoff` now calls `autonomy-write-guard.py` through `guard_or_raise("kanban-worker", "claim-and-handoff", "dispatch-hint", allowlist)` before it mutates task state, creates a handoff, or appends proof.
- Missing `HERMES_AUTONOMY_WRITE_ALLOWLIST` / missing `kanban-worker` surface now returns `status=FAIL_CLOSED`, `claimed=false`, reason `autonomy_write_guard_failed`, and preserves the guard evidence JSON under `write_guard`; no task claim/handoff/proof is written.
- Positive path remains bounded: even when both autorun task allowlist and autonomy write-surface allowlist pass, the action is still only claim + handoff + proof, with `write_guard` evidence attached; it still does not execute Markdown, arbitrary hooks, or mark done.
- `autonomy-write-guard.py` now supports the bounded control-plane operation `claim-and-handoff`, separated from external writes. External writes still require `budget-handoff` / `autonomous-execution` and remain blocked by router/quota/autonomy precondition failures.

Commands run in this slice:
- `python3 -m py_compile ~/.hermes/scripts/autonomy-write-guard.py ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_dispatch_tick.py`: exit 0.
- `python3 ~/.hermes/scripts/test_model_diversity_and_autonomy_gates.py`: 10/10 OK.
- `python3 ~/.hermes/scripts/test_brain_task_orchestrator.py`: PASS, including regression that missing write-surface allowlist blocks `auto-claim-and-handoff` before task mutation.
- `python3 ~/.hermes/scripts/test_brain_task_dispatch_tick.py`: PASS, including the optional `--autorun` bridge with explicit central write-surface allowlist.

Full verification after this slice:
- `python3 -m py_compile ~/.hermes/scripts/model_quota.py ~/.hermes/scripts/model-router.py ~/.hermes/scripts/autonomy-precondition.py ~/.hermes/scripts/autonomy-write-guard.py ~/.hermes/scripts/model-diversity-monitor.py ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/brain_task_dispatch_tick.py ~/.hermes/scripts/test_model_quota.py ~/.hermes/scripts/test_model_router_quota.py ~/.hermes/scripts/test_model_diversity_and_autonomy_gates.py ~/.hermes/scripts/test_brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_dispatch_tick.py`: exit 0.
- `python3 ~/.hermes/scripts/test_model_quota.py`: 26/26 OK.
- `python3 ~/.hermes/scripts/test_model_router_quota.py`: 30/30 OK.
- `python3 ~/.hermes/scripts/test_model_diversity_and_autonomy_gates.py`: 10/10 OK.
- `python3 ~/.hermes/scripts/test_brain_task_orchestrator.py`: PASS.
- `python3 ~/.hermes/scripts/test_brain_task_dispatch_tick.py`: PASS.
- `python3 ~/.hermes/scripts/self-test.py`: 70/70 passed, ALL PASS.
- `bash ~/.hermes/scripts/p10-health.sh --json`: exit 0, grade=A, V=0.9871, self_test=1.0, self_test_count=70.
- `python3 ~/.hermes/scripts/model_quota.py confidence-gate --json --gate`: exit 2 by design; status=FAIL_CLOSED, failure_count=4, counts exact=0/estimated=0/unknown=3/unobservable=1/stale=4/low_confidence=4.
- `python3 ~/.hermes/scripts/model-router.py readiness --json --gate`: exit 2 by design; status=FAIL_CLOSED, failed_checks=dominance_warning,diversity_gate_failed,quota_confidence_failed; dominant_model=gpt-5.5, dominant_share=1.0, rebalance_required=true, required_non_dominant_calls=125.
- `python3 ~/.hermes/scripts/autonomy-precondition.py --mode budget-handoff --json --gate`: exit 2 by design; failed_required_checks=model_diversity_gate,quota_confidence,router_readiness.
- `python3 ~/.hermes/scripts/autonomy-write-guard.py --surface google-workspace --operation write --mode budget-handoff --json --gate`: exit 2 by design; failed_required_checks=surface_allowlisted,autonomy_precondition.
- `python3 ~/.hermes/scripts/ratification_gate.py --json`: exit 2; deterministic_gate_status=PASS, ratification_status=NOT_CERTIFIED, final_integration_status=LOCAL_COMPLETE_UNRATIFIED.

Interpretation: this closes the previous gap between “guard API exists” and “a real caller uses it”. It still intentionally does not certify broader autonomous execution: live router diversity remains dominated by gpt-5.5, quota evidence remains stale/unknown/unobservable, and budget-handoff/external-write gates continue to fail closed by design.

## 6.4 PUA-loop blocker recovery evidence

Verification timestamp: 2026-05-09T08:58:30Z.

Additional local slice landed after 6.3:
- `multi-model-smoke.py` was restored as a real-call, bounded actual-usage smoke/warm-up runner used by the existing `multi-model-smoke-safe.py` cron wrappers.
  - It records only real calls into `route_outcomes.db` with `is_synthetic=0`.
  - It supports targeted warm-up via `--model`, bounded repeat via `--repeat`, route tagging via `--route`, and DeepSeek exact balance refresh via `--probe-deepseek-balance`.
  - A bounded DeepSeek warm-up ran successfully: 125 real DeepSeek calls total in this tick (1 initial + 124 rebalance calls), followed by a post-fix smoke call. This reduced live model dominance from gpt-5.5 1.0 to 0.748/0.75 in the 500-call diversity window.
- `model_quota.py` now preserves a fresh higher-confidence exact quota snapshot when a later successful provider call exposes no quota headers.
  - Root cause found: DeepSeek balance probe produced exact `billing_balance` evidence, but subsequent DeepSeek response headers lacked quota counters; the old `record_call()` path converted those empty headers into a low-confidence `unknown` snapshot and overwrote exact balance evidence.
  - Fix: `record_snapshot()` now compares evidence quality and refuses to downgrade fresh exact/estimated quota evidence with lower-confidence empty-header evidence, while still allowing safety blockers such as 429/rate-limit/exhausted evidence to overwrite prior OK snapshots.
  - `multi-model-smoke.py` also records response headers into quota state only when recognizable quota/rate-limit headers are present; exact DeepSeek balance remains handled by the balance probe.
- Quota observability refresh actions no longer ask for `probe_deepseek_balance` after DeepSeek already has fresh usable exact balance evidence.
- `self-test.py` now compiles `multi-model-smoke.py`, so cron wrappers no longer point at an untracked/unverified raw script.

Commands run in this slice:
- `python3 -m py_compile ~/.hermes/scripts/model_quota.py ~/.hermes/scripts/multi-model-smoke.py ~/.hermes/scripts/test_model_quota.py ~/.hermes/scripts/self-test.py`: exit 0.
- `python3 ~/.hermes/scripts/test_model_quota.py`: 28/28 OK, including regressions for preserving exact balance against empty response headers and still replacing with safety blockers.
- `python3 ~/.hermes/scripts/multi-model-smoke.py --model deepseek-v4-pro --repeat 124 --route 'probe:warmup:{model}' --probe-deepseek-balance --timeout 20`: exit 0, 124/124 real DeepSeek smoke calls passed.
- `python3 ~/.hermes/scripts/multi-model-smoke.py --model deepseek-v4-pro --repeat 1 --route 'probe:post-fix:{model}' --probe-deepseek-balance --timeout 20`: exit 0.
- `python3 ~/.hermes/scripts/model-diversity-monitor.py --json --gate`: exit 0; dominant_model=gpt-5.5, dominant_share=0.75/0.748, dominance_warning=false.
- `python3 ~/.hermes/scripts/model_quota.py confidence-gate --json --gate`: exit 2 by design; status=FAIL_CLOSED, pass_count=1, failure_count=3, exact=1, unknown=2, unobservable=1, stale=3, low_confidence=3; refresh_actions=`manual_budget_confirmation_or_lower_risk_tier`,`record_provider_response_headers`.
- `python3 ~/.hermes/scripts/model-router.py readiness --json --gate`: exit 2 by design; status=FAIL_CLOSED, failed_checks=`quota_confidence_failed`, rebalance_required=false, rebalance_plan.action=`no_rebalance_needed`.
- `python3 ~/.hermes/scripts/autonomy-precondition.py --mode budget-handoff --json --gate`: exit 2 by design; failed_required_checks=`quota_confidence`,`router_readiness`.
- `python3 ~/.hermes/scripts/test_model_router_quota.py`: 31/31 OK.
- `python3 ~/.hermes/scripts/test_model_diversity_and_autonomy_gates.py`: 10/10 OK.
- `python3 ~/.hermes/scripts/test_brain_task_orchestrator.py`: PASS.
- `python3 ~/.hermes/scripts/test_brain_task_dispatch_tick.py`: PASS.
- `python3 ~/.hermes/scripts/self-test.py`: 71/71 passed, ALL PASS.
- `bash ~/.hermes/scripts/p10-health.sh --json`: exit 0, grade=A, V=0.9868, self_test=1.0, self_test_count=71, cron_bad=0, model_diversity_gate=true, model_quota_confidence_gate=false, model_router_readiness_gate=false.
- `python3 ~/.hermes/scripts/ratification_gate.py --json`: exit 2; deterministic_gate_status=PASS and truth_status=grounded/can_certify_truth=true, but ratification_status=NOT_CERTIFIED and final_integration_status=LOCAL_COMPLETE_UNRATIFIED.

Current blocker status after this loop:
- RESOLVED: live model diversity dominance blocker. Router readiness no longer requires rebalance; `rebalance_required=false`.
- RESOLVED: quota exact-evidence downgrade bug. DeepSeek exact balance evidence now persists across smoke calls without being overwritten by empty response headers.
- STILL BLOCKING: quota confidence for Claude, MiMo, and openai-codex/gpt-5.5 remains unproven/unobservable/stale. This cannot be truthfully converted to PASS without either real provider quota/rate-limit headers, official balance endpoints, or an explicit accepted policy for subscription/unobservable providers.
- STILL BLOCKING: budget-handoff / broad autonomous execution remains fail-closed because router readiness consumes quota confidence. This is correct; do not bypass it.

Next round entrypoint:
1. Prefer low-risk observable providers for budget-handoff certification until subscription/unobservable providers have accepted policy: run targeted provider smoke/probes and inspect whether Claude/MiMo expose rate-limit headers.
2. If a provider is inherently unobservable (for example subscription cap), add a reviewed policy object that explicitly scopes acceptable risk by tier and never silently promotes to full autonomous certification.
3. Rerun: `python3 ~/.hermes/scripts/model_quota.py confidence-gate --json --gate && python3 ~/.hermes/scripts/model-router.py readiness --json --gate && python3 ~/.hermes/scripts/autonomy-precondition.py --mode budget-handoff --json --gate`.
4. Only after those pass, run fresh scoped T3 ratification; until then status remains `not_certified_for_autonomous_execution`.

Interpretation: PUA-loop closed the recoverable local blockers without falsifying provider facts. The system is locally green and safer, but full autonomy/budget-handoff certification is intentionally still blocked by provider quota observability.

## 6.5 Provider quota unobservability policy evidence

Verification timestamp: 2026-05-09T09:15:19Z.

Additional local slice landed after 6.4:
- `multi-model-smoke.py` now probes Xiaomi MiMo through the direct OpenAI-compatible API route instead of only through the Hermes subprocess route, so Hermes can inspect real response headers when the provider exposes them.
- Bounded live smoke was rerun for MiMo, OpenAI-Codex/gpt-5.5, and Claude Opus:
  - `python3 ~/.hermes/scripts/multi-model-smoke.py --model mimo-v2.5-pro --model gpt-5.5 --model claude-opus-4-7 --repeat 1 --route 'probe:quota-policy-r2:{model}' --timeout 90 --probe-deepseek-balance`: exit 0, 3/3 passed, run_id=d47fb613.
  - MiMo direct API succeeded but returned no quota/rate-limit/balance headers; quota state records `source=direct_api_no_quota_headers`, `quota_type=provider_api_no_quota_headers`, `confidence=0.35`, and `status=unobservable`.
  - OpenAI-Codex/gpt-5.5 and Claude CLI routes succeeded, but both are subprocess/OAuth routes that expose no response headers to Hermes; quota state records `source=subprocess_success_no_quota_headers`, `status=unobservable`, `confidence=0.3`.
  - DeepSeek balance probe remained exact and fresh: `remaining_usd=34.98`, `observability=exact`, `confidence=0.85`.
- `model_quota.py` now has `snapshot_unobservable_success()` to distinguish real runtime availability evidence from budget evidence. A successful call with no quota headers is recorded as `unobservable`, never as budget-ready `ok`.
- `quota_observability_evidence()` now emits explicit `counts.total` and `counts.usable`, so router readiness can require a positive strict schema instead of inferring pass from truthiness.
- `model-router.py` strict quota gate now requires explicit `passes`, matching snapshots, sufficient confidence, timestamp evidence including `last_updated`, and `observability_evidence.counts.usable/total`; hollow `{"ok": true}` shells remain fail-closed.
- New policy artifact: `/Users/charles/.hermes/config/model_quota_observability_policy.json` documents provider-specific allowed scope. Current unobservable providers are allowed only for `low_risk_routing` / `actual_usage_smoke`; they are forbidden for `budget_handoff_certification`, `broad_autonomous_execution`, and `external_write_certification`.
- Skill reference updated: `multi-model-thinking/references/provider-quota-observability-and-rebalance.md` now documents `direct_api_no_quota_headers` / `subprocess_success_no_quota_headers` actions and the rule that unobservable success must not become budget evidence.

Commands run in this slice:
- `python3 -m py_compile ~/.hermes/scripts/model_quota.py ~/.hermes/scripts/model-router.py ~/.hermes/scripts/multi-model-smoke.py ~/.hermes/scripts/test_model_quota.py ~/.hermes/scripts/test_model_router_quota.py`: exit 0.
- `python3 ~/.hermes/scripts/test_model_quota.py`: 30/30 OK.
- `python3 ~/.hermes/scripts/test_model_router_quota.py`: 32/32 OK.
- `python3 -m json.tool ~/.hermes/config/model_quota_observability_policy.json >/dev/null`: exit 0.
- `python3 ~/.hermes/scripts/model_quota.py confidence-gate --json --gate`: exit 2 by design; status=FAIL_CLOSED, pass_count=1, failure_count=3, counts total=4 usable=1 exact=1 unobservable=3 stale=0; refresh_actions=`provider_unobservable_lower_risk_tier_or_documented_policy`,`use_api_route_for_headers_or_lower_risk_tier`.
- `python3 ~/.hermes/scripts/model-router.py readiness --json --gate`: exit 2 by design; failed_checks=`quota_confidence_failed`, rebalance_required=false, dominant_share=0.736.
- `python3 ~/.hermes/scripts/autonomy-precondition.py --mode budget-handoff --json --gate`: exit 2 by design; failed_required_checks=`quota_confidence`,`router_readiness`.
- `python3 ~/.hermes/scripts/model-diversity-monitor.py --json --gate`: exit 0; dominance_warning=false, dominant_share=0.736.
- `python3 ~/.hermes/scripts/self-test.py`: exit 0; 71/71 passed, ALL PASS.
- `bash ~/.hermes/scripts/p10-health.sh --json`: exit 0; grade=A, V=0.9862, self_test=1.0, model_diversity_gate=true, model_quota_confidence_gate=false, model_router_readiness_gate=false.
- `python3 ~/.hermes/scripts/verify-evolution-event.py ~/.hermes/notes/evolution/2026-05-09-hermes-v013-update-fusion-plan.md ~/.hermes/config/model_quota_observability_policy.json --repo=/Users/charles/.hermes/hermes-agent`: exit 0; Final: COMPLIANT.
- `python3 ~/.hermes/scripts/ratification_gate.py --json`: exit 2 by design; deterministic_gate_status=PASS, truth_status=grounded/can_certify_truth=true, ratification_status=NOT_CERTIFIED, final_integration_status=LOCAL_COMPLETE_UNRATIFIED.

Current blocker status after this loop:
- RESOLVED: the previous unknown/stale quota ambiguity has been converted into explicit, fresh, provider-scoped evidence: 3 providers are intentionally `unobservable`, not unchecked.
- RESOLVED: router quota gate no longer accepts hollow success shells and can consume the stricter positive schema from `model_quota.py`.
- STILL BLOCKING BY DESIGN: Claude, OpenAI-Codex/gpt-5.5, and MiMo do not provide usable quota/budget evidence through the available routes. They remain valid for low-risk real smoke/routing evidence but not for budget handoff or broad autonomous execution.
- STILL BLOCKING BY DESIGN: budget-handoff and autonomous execution remain fail-closed until exact/estimated quota evidence or a separately reviewed risk acceptance policy exists.

Interpretation: this loop intentionally improves truthfulness rather than making gates green. The correct certification status remains `truth_grounded_advisory` / `not_certified_for_autonomous_execution`; no full certification is claimed.

## 7. Upgrade survival

Level 0 artifacts under ~/.hermes/ survive upstream git pull:
- /Users/charles/.hermes/notes/evolution/2026-05-09-hermes-v013-update-fusion-plan.md
- /Users/charles/.hermes/scripts/model-diversity-monitor.py
- /Users/charles/.hermes/scripts/autonomy-precondition.py
- /Users/charles/.hermes/scripts/autonomy-write-guard.py
- /Users/charles/.hermes/scripts/model_quota.py
- /Users/charles/.hermes/scripts/model-router.py
- /Users/charles/.hermes/scripts/test_model_quota.py
- /Users/charles/.hermes/scripts/test_model_router_quota.py
- /Users/charles/.hermes/scripts/test_model_diversity_and_autonomy_gates.py
- /Users/charles/.hermes/scripts/self-test.py
- /Users/charles/.hermes/scripts/p10-health.sh
- /Users/charles/.hermes/config/model_quota_observability_policy.json
- /Users/charles/.hermes/skills/software-development/multi-model-thinking/references/provider-quota-observability-and-rebalance.md
- /Users/charles/.hermes/scripts/test_cross_patch_safety.py
No vendor-core patch has been applied in this advisory tick.
No remote push required.
