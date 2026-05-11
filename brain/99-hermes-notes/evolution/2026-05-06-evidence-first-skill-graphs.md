# Evolution Event: Evidence-First Multi-Brain + Skill Graphs 2.0

**Date:** 2026-05-06
**Type:** runtime-improvement | workflow-addition | skill-governance
**Source:** user request + P10/PUA loop self-audit + Claude Code independent review

## Source Signal

User requested continued Hermes self-evolution with Claude Code review, P10/PUA-loop improvement, multi-brain comparison, and no remaining missing progress.

Extracted mechanisms:
- Multi-model consensus must not certify factual truth without orchestrator-owned evidence.
- Reviewer brains should request evidence rather than pretending they ran tools.
- Skill ecosystem growth needs a graph audit gate before any runtime skill-loader rewrite.
- Skill Graphs 2.0 should model atoms / molecules / compounds, detect cycles and excessive depth, and fail closed in strict mode.

## Multi-Brain Comparison

| Brain | Position | Adopted outcome |
|---|---|---|
| Codex / main orchestrator | Implement evidence-first truth gate and Skill Graphs 2.0 as scripts + schemas + self-test, not runtime loader mutation. | Adopted as implementation owner. |
| Claude Code independent reviewer | No blocking security/logic defects; flagged low-severity issues: YAML import safety, planner prompt truncation, quota gate ordering, self-test `ok` handling, `sys` import location, `os.system` dashboard sync. | All actionable low-severity code issues fixed before commit. |
| consult_models evidence-first gate | Prior smoke: unsupported high-severity claims fail closed; supported claims certify; final T3 audit grounded 6/6 claims. | Captured in tests and skill docs. |
| Skill graph audit | Existing ecosystem has cycles=24, depth_max=4, tiers inferred as atom/molecule/compound. | Reported as `GRAPH_VIOLATIONS` in warn-only production mode; strict mode exits 2. |

Final synthesis: audit and gate first, migrate/clean cycles later. Do not modify runtime skill loader until graph health is measurable and self-test covered.

## Hermes-Specific Output

Local code commit: `a39fcba feat(self-evolution): add evidence-first truth gate and skill graph audit`

Files created/modified:

| File | Purpose |
|---|---|
| `scripts/consult_models.py` | EvidenceBundle / TruthGate / EvidenceRequest, state owner, evidence prompts, fail-closed ratification, SPL opt-in, quota backfill before quorum trim, prompt truncation notice preserving truth fields. |
| `scripts/test_consult_models_integration.py` | 23 integration tests covering fanout certification, quota, truth gate, evidence requests, planner prompt truncation. |
| `schemas/evidence-bundle.schema.json` | Evidence bundle schema. |
| `scripts/self-test.py` | Added schema checks and Skill Graphs 2.0 smoke tests. |
| `scripts/skill-steward.py` | Added Skill Graphs 2.0 audit: nodes/edges, inferred tiers, cycles, depth, typed violations, strict/warn-only mode. |
| `schemas/skill-graph-audit.schema.json` | Skill graph audit schema. |
| `skills/steward/skill-graph-report.json` | Current ecosystem graph report. |
| `skills/software-development/*/SKILL.md` | Skill docs patched with evidence-first and graph-governance operating rules. |

## Verification Results

All verification was run after Claude Code review fixes:

```text
python3 ~/.hermes/scripts/test_consult_models_integration.py
Ran 23 tests in 0.011s — OK

python3 ~/.hermes/scripts/self-test.py
Self-Test Results: 64/64 passed
ALL PASS — system is operational

python3 ~/.hermes/scripts/skill-steward.py --graph-check --json --warn-only
status=GRAPH_VIOLATIONS, cycle_count=24, depth_max=4, max_depth_allowed=4

bash ~/.hermes/scripts/p10-health.sh --json
grade=A, V=0.9886, self_test_count=64, cron_bad=0, gateway_running=true

git diff --check -- selected files
diff_check_selected=OK

static added-line security scan
static_scan_findings=none
```

Claude Code independent review after initial implementation:
- `passed=true`
- `security_concerns=[]`
- No blocking logic errors.
- Low-severity issues were fixed before commit: YAML import guard, planner prompt truncation preserving claims/evidence/truth_gate, quota gate before quorum trim, self-test `ok` initialization, `sys` import at module top, dashboard sync via `subprocess.run`.

## Level Classification

- Level 0 files: `~/.hermes/scripts/*`, `~/.hermes/schemas/*`, `~/.hermes/skills/*`, `~/.hermes/notes/evolution/*`.
- Level 1 files: none.
- Level 2 files: none. No vendor-core runtime loader patch was made.

## Pitfalls Discovered

- `git diff --check` over all `~/.hermes` is noisy because logs/checkpoints contain pre-existing trailing whitespace; use path-limited checks for selected evolution files.
- Large diffs can time out or overload reviewer agents; Claude Code review should be scoped to explicit files and verified outputs.
- Planner prompt truncation can silently drop evidence fields; prompts now mark truncation and preserve claims/evidence/truth_gate.
- Quorum trimming before quota gating can lose healthy later planners; selection now gates first then trims.
- Existing skill graph cycles are real ecosystem debt, not a script failure. Production audit remains warn-only until a dedicated cycle-cleanup migration runs.

## Upgrade Survival

All changed artifacts are Level 0 under `~/.hermes`; they survive upstream `hermes update` as user/private evolution artifacts. No remote push or upstream PR is required.

## P1/P2 Candidates

1. P1: Clean the 24 known Skill Graph cycles, starting with autonomous-ai-agents and software-development review-loop cycles.
2. P1: Add cron job for nightly graph report with strict mode disabled but alerting on new cycles/depth regressions.
3. P2: Add explicit `tier:` metadata migration to high-traffic skills instead of relying only on inference.
4. P2: Add direct unit coverage for `_find_cycles` and `_depths_and_chains` beyond fixture smoke tests.
5. P2: Extend consult_models artifacts with `state_truncated=true` metadata in merged outputs, not only planner prompts.

## Decision Record

| Decision | Rationale |
|---|---|
| No runtime skill loader rewrite | Audit evidence first; avoid breaking tool invocation. |
| Strict graph check exists but production uses warn-only | Current ecosystem has known cycles; strict mode proves fail-closed behavior for CI/fixtures. |
| Evidence-first truth gate blocks unsupported high-severity claims | Multi-model agreement is not factual verification. |
| No push to upstream | Private fork/local Hermes evolution; local commit is sufficient. |

## Follow-up: Skill Graph Cycle Cleanup

After the initial audit gate landed, PUA-loop continued from observation to remediation:

- Initial production graph after audit gate: `GRAPH_VIOLATIONS`, `cycles=24`, `depth_max=4`.
- Collapsed cycle paths into SCCs instead of treating 24 paths as 24 independent problems.
- Rewrote `related_skills` as a one-way DAG across the major SCCs:
  - autonomous AI agents: preserve discovery as `claude-code -> codex -> opencode`, avoid peer-to-peer cycles.
  - GitHub workflow skills: make `github-auth` a primitive prerequisite, downstream skills point toward it instead of back-linking.
  - software-development workflow skills: keep planning/review/TDD/debug discoverability without mutual cycles.
  - sketch/spike, kanban orchestrator/worker, and debugger helper cycles were reduced to directional edges.
- Claude Code reviewed the cleanup diff and returned `passed=true`, `blocking=[]`; non-blocking suggestions about discoverability and user-specific Codex text were applied.
- Removed user/account-specific Codex model/economics text from the generic `codex` skill; provider/model mapping belongs in `~/.hermes/config.yaml` or memory, not shared SKILL.md.

Final strict graph gate:

```text
python3 ~/.hermes/scripts/skill-steward.py --graph-check --json
status=OK
edges=87
depth_max=4
cycles=0
typed_violations=[]
excessive_depth=[]
```

This completes the Skill Graphs 2.0 closure condition: the production graph is now strict-gate clean while runtime skill loading remains unchanged.
