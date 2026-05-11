# Post-update fusion verifier gates

Use this reference when a Hermes update introduces many new surfaces and the user asks for multi-model self-check, fusion with existing architecture, or an execution roadmap.

## Session pattern captured

A post-update fusion review can be truth-grounded but still not implementation-certified. Treat these as separate statuses:

- `truth_grounded_advisory`: claims are backed by evidence and a matrix/roadmap is useful.
- `not_certified_for_autonomous_execution`: unsafe autonomy, external writes, or budget handoff are blocked until deterministic enforcement exists.
- `implementation_certified`: only after ratification gates pass with no unresolved severity>=3 issues.

Do not upgrade a T3 fanout to certification merely because 4 models answered or truth coverage is 1.0. If discussion has agreement <0.85, approvals below N-1, reject votes, or unresolved severity>=3 issues, final status remains `not_certified`.

## Required evidence before T3 review

Collect and link claims to evidence for:

1. Release/update feature inventory.
2. Local repo/version/git state.
3. Deterministic health: self-test, p10-health, skill graph, cron, route/eval status.
4. Model/provider state: router probe, quota confidence, diversity distribution.
5. Existing private architecture surfaces: router, protocol, ensemble, cross-patch, local brain, taskpool, governance.
6. Prior failed/not-certified T3 artifacts as negative evidence, not certification.

## Verifier gaps found in practice

### p10-health self-test parser drift

Pitfall: counting raw checkmarks can produce false negatives when `self-test.py` summary says `Self-Test Results: 66/66 passed` but only 65 checkmarks are counted from streamed output/truncated subtests.

Preferred parser:

- Run self-test as a bounded subprocess.
- Parse `Self-Test Results: N/N passed` with regex.
- Mark ok only if returncode is 0, `passed == total`, and `ALL PASS` appears.
- Keep raw log for audit.

Verification:

```bash
bash -n ~/.hermes/scripts/p10-health.sh
python3 ~/.hermes/scripts/self-test.py
bash ~/.hermes/scripts/p10-health.sh --json
```

Expected: `components.self_test=1.0`, `details.self_test_count` equals the summary count, and grade is not depressed by parser drift.

### model-diversity false healthy label

Pitfall: route-level pass-rate variance can say “healthy” even if one model handles nearly all calls (e.g. gpt-5.5 498/500, DeepSeek 1/500, MiMo 1/500).

Add a dominance check:

- Compute per-model call share over the tracked window.
- If sample size is sufficient and max share >80%, emit `dominance_warning=true` and identify `dominant_model`/`dominant_share`.
- Text output must not say “All routes show healthy model diversity” when dominance warning is true.
- JSON output should expose `model_stats`, `model_shares`, `dominance_warning`.

Verification:

```bash
python3 -m py_compile ~/.hermes/scripts/model-diversity-monitor.py
python3 ~/.hermes/scripts/model-diversity-monitor.py
python3 ~/.hermes/scripts/model-diversity-monitor.py --json
```

Important: warning is not enforcement. Before certification, add a router/tier-promotion gate that consumes the warning or otherwise proves balanced planner selection.

### P0 fail-closed enforcement pattern

When the fusion review finds that new upstream autonomy/provider/router surfaces could bypass existing L0-L5+LX controls, land small deterministic gates before any certification claim:

1. Quota confidence gate: add a machine-readable `confidence-gate --json --gate` command to the quota layer. Low-risk routing may tolerate `unknown`/`unobservable`, but `budget-handoff` and `autonomous-execution` must fail closed on unknown, unobservable, exhausted, rate-limited, malformed, or unavailable quota evidence.
2. Router readiness gate: add `readiness --json --gate` to the router. It must consume model-diversity dominance evidence and quota confidence output, expose `rebalance_required`, list eligible non-dominant alternates, and fail closed on `dominance_warning` or quota-confidence failure.
3. Autonomy precondition gate: split modes explicitly. `dispatch-hint` is local health only and cannot execute tasks or external writes; `budget-handoff` requires diversity + quota confidence + router readiness; `autonomous-execution` additionally requires an explicit local enable file/kill switch. For CLI consistency with other fail-closed gates, accept `--json --gate` even if output is always JSON; add a regression test so verification commands do not fail on argument parsing instead of gate semantics.
4. Write-surface guard: put a wrapper in front of goal/kanban-worker/watcher/teams/google-workspace/gateway-fanout/cron-no-agent writes. Require known surface, allowlist, explicit mode, and passing autonomy precondition. Unknown surfaces and unallowlisted writes fail closed.
5. Health surfacing: p10-health should report these gates as blocker fields, not bury them in logs. A high grade can coexist with `not_certified_for_autonomous_execution` when autonomy gates fail closed.

Verification bundle after these changes:

```bash
python3 -m py_compile ~/.hermes/scripts/model_quota.py ~/.hermes/scripts/model-router.py ~/.hermes/scripts/autonomy-precondition.py ~/.hermes/scripts/autonomy-write-guard.py ~/.hermes/scripts/model-diversity-monitor.py
python3 ~/.hermes/scripts/test_model_quota.py
python3 ~/.hermes/scripts/test_model_router_quota.py
python3 ~/.hermes/scripts/test_model_diversity_and_autonomy_gates.py
python3 ~/.hermes/scripts/self-test.py
bash ~/.hermes/scripts/p10-health.sh --json
python3 ~/.hermes/scripts/model_quota.py confidence-gate --json --gate
python3 ~/.hermes/scripts/model-router.py readiness --json --gate
python3 ~/.hermes/scripts/autonomy-precondition.py --mode budget-handoff --json --gate
python3 ~/.hermes/scripts/autonomy-write-guard.py --surface google-workspace --operation write --mode budget-handoff --json --gate
```

Expected current-state interpretation is often intentionally failing: if real quota is unobservable and route history is dominated by one model, the gate commands should return non-zero and the final status remains `truth_grounded_advisory` / `not_certified_for_autonomous_execution`. Do not weaken the gates just to make a post-update fusion review green.

### Ratification mismatch pitfall: implementation required but no patches

If T3 discussion says `implementation_required` or reviewers propose P1/P0 follow-up work, but `merged_plan.patches=[]`, do not interpret the empty patch list as approval/no-op. Treat this as an adjudication gap: either produce the concrete patch/rationale and rerun ratification, or explicitly downgrade to a no-action advisory with the follow-up risks logged. Until then, keep `discussion_result.status=not_certified` when severity>=3 risks remain, even if deterministic self-tests and truth coverage are 100%.

## Fusion mapping rule

Map new upstream surfaces onto existing mechanisms instead of duplicating them:

- Kanban/specify -> local brain taskpool board/UI, not second task source.
- `/goal` -> dispatch hint until budget/proof/rollback gates exist.
- no_agent cron/watchers -> existing safe tick/no-agent watchdog pattern.
- provider plugins -> existing model-router/model_quota/model_health LX layer.
- Curator -> proposer; skill-steward remains deterministic graph gate.
- API/session memory -> canonical brain vault policy; runtime indexes are derived caches.
- Gateway/platform/Teams/Google Workspace writes -> allowlisted, dry-run/read-only first, explicit approval for writes.

## Certification blockers to preserve

Keep the result advisory/not-certified if any remain:

- provider health contradiction (e.g. doctor says invalid while router probe says available),
- quota confidence unknown/unobservable for T3 models,
- router diversity only warns but does not enforce,
- autonomous surfaces lack kill switch + budget + proof + rollback + allowlist + deterministic gate,
- merged patches empty while planner_patch_summary says implementation is required,
- unresolved severity>=3 issues or reject votes in `discussion_result.json`.

## Suggested final wording

Use precise status language:

- “truth-grounded advisory plan”
- “deterministic verifier gaps fixed”
- “not certified for autonomous execution”
- “fresh T3 certification required after enforcement gates land”

Avoid saying “certified” unless the certification manifest independently passes fanout, truth, votes, agreement, and unresolved-issue gates.
