# Evolution Event: Warp → Hermes P0 Multi-Model Governance

**Date:** 2026-04-29
**Type:** methodology-migration
**Source:** external project analysis (`warpdotdev/warp`)
**Status:** committed

## Source Signal

- **External repo:** `https://github.com/warpdotdev/warp`
- **Analysed mechanisms:**
  - `.agents/skills/spec-driven-implementation/SKILL.md` — spec-first development
  - `.agents/skills/review-pr/SKILL.md` — structured PR review artifacts
  - `.agents/skills/triage-issue-local/SKILL.md` — repo-local issue triage
  - `.agents/skills/warp-integration-test/SKILL.md` — integration test skill
  - `.github/workflows/create-spec-from-issue-local.yml` — issue → spec workflow
  - `.github/workflows/create-implementation-from-issue-local.yml` — spec → implementation
  - `.github/workflows/review-pull-request.yml` — structured review publication
  - `.github/issue-triage/config.json` — issue taxonomy
- **Adaptation principle:** extract governance mechanisms (process, structure, workflow), NOT code (AGPL risk + Rust/Python architecture difference)

## Hermes-Specific Output

### Local commit
```
132093a53 docs: add p0 multimodel governance artifacts
```

### Files created (all additive, no existing file modified)

| Path | Purpose |
|------|---------|
| `specs/p0-multimodel-governance/PRODUCT.md` | Product-level spec for P0 |
| `specs/p0-multimodel-governance/TECH.md` | Technical spec with evidence, verification, risks |
| `docs/specs/review.schema.json` | Structured review artifact schema (JSON) |
| `docs/workflows/issue-taxonomy.md` | Issue labels / taxonomy / routing |
| `docs/workflows/repo-local-skill-specialization.md` | Core skill + repo-local overlay |
| `docs/workflows/multi-model-architecture-optimization.md` | Multi-model architecture analysis |
| `docs/adr/ADR-0001-agentic-governance-artifacts.md` | Architecture Decision Record |

### Multi-model evidence
- Real T3 seed fan-out with 4 planners: Claude Opus, gpt-5.5, DeepSeek V4, MiMo
- Four independent plans produced; discussion/consensus phase timed out at 600s
- `merged_plan.json` at `~/.hermes/tick-20260429-110802/`
- Planners converged on "governance before runtime" — consistent across all outputs

### Verification
- JSON schema: `python3 -m json.tool docs/specs/review.schema.json >/dev/null` — passed
- Isolated tests: `HERMES_HOME=<tmp> python -m pytest tests/test_model_health.py tests/test_task_classifier.py -q -o addopts=` — 24/24 passed
- Real home model_health tests fail: persisted state pollutes circuit breaker assertions

## PUA Loop Score
N/A (no PUA scoring this round)

## Pitfalls Discovered
- `agent/model_health.py` persists state to `$HERMES_HOME/rate_limits/model_health_state.json`; running tests with real `~/.hermes` causes `HALF_OPEN` state mismatch
- Already patched into `multi-model-architecture` skill Pitfalls section
- Documented in `specs/p0-multimodel-governance/TECH.md` and `docs/workflows/multi-model-architecture-optimization.md`

## Upgrade Survival
- All artifacts are in repo `docs/` and `specs/` — additive only, no vendor code changes
- Remote push not applicable (private fork of upstream, no push permission needed)
- Next controlled upgrade: normal `git pull --ff-only` + `post-update-check.py --fix`

## P1 Candidates (from TECH.md)
- O1: T1 `min_quorum=1` → raise to 2 or degrade explicitly
- O2: T0 fallback → explicit degraded path for MiMo-unavailable
- O3: Quota observability → dedicated probe command
- O4: review.json → multi-model output connection
- O5: `~/.hermes/scripts/` → repo vs local ADR decision

## Related Files
- `/Users/charles/.hermes/hermes-agent/specs/p0-multimodel-governance/`
- `/Users/charles/.hermes/hermes-agent/docs/workflows/`
- `/Users/charles/.hermes/hermes-agent/docs/adr/ADR-0001-agentic-governance-artifacts.md`
- `/Users/charles/.hermes/hermes-agent/docs/specs/review.schema.json`
- `/Users/charles/.hermes/tick-20260429-110802/`
