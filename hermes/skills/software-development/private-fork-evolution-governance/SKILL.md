---
name: private-fork-evolution-governance
description: Use when governing a private Hermes fork, recording evolution events, analyzing external projects for methodology migration, or verifying that local artifacts survive upstream upgrades.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - private-fork
    - evolution-governance
    - upgrade-survival
    - compliance
    related_skills:
    - post-update-patch-healing
    - self-improvement-pipeline
    - framework-audit
    - save-workflow-as-skill
---

# Private Fork Evolution Governance

## Overview


> Govern a private fork of an open-source agent framework where:
> - External project analysis is valid evolution input (methodology migration, not code copy)
> - Remote push is not required; `ahead N, behind M` is normal
> - `git pull` from upstream is a controlled upgrade, not a sync
> - Every evolution event must leave a traceable, verifiable artifact

## When to Use

- Governing a private Hermes fork, recording evolution events, analyzing external projects for methodology migration, or verifying that local artifacts survive upstream upgrades
- Don't use for: requests that do not need governing a private Hermes fork, recording evolution events, analyzing external projects for methodology migration, or verifying that local artifacts survive upstream upgrades; choose a more specific child skill or a broader routing skill that actually matches the task.
## Core Principles

1. **This is a private fork.** No commits need to reach upstream. No PRs required. `origin/main` is a reference source, not the canonical remote.

2. **`git pull` = upgrade, not sync.** Like updating an OS — local artifacts survive via planned mechanisms, not by accident.

3. **External project analysis = valid evolution input.** Studying Warp, Claude Code, Codex, or any external agent/project and extracting mechanism → adapting to Hermes → creating Hermes-native artifact. This IS evolution, not "reading competitor code."

4. **`ahead N, behind M` is normal.** It means "N private evolutions ahead of upstream; M upstream upgrades available when ready." Not a failure state.

## Three-Tier Artifact Model (Level 0/1/2)

| Level | Location | Survival on `git pull` | Risk | Examples |
|-------|----------|----------------------|------|----------|
| **0 — User data** (prefer first) | `~/.hermes/skills/`, `~/.hermes/scripts/`, `~/.hermes/config/`, `~/.hermes/plugins/`, `~/.hermes/notes/`, `~/.hermes/cron/` | Update-safe — outside git entirely | None | Private evolution manifesto, evolution event notes, verify scripts |
| **1 — Repo-local** | `<repo>/docs/`, `<repo>/specs/`, `<repo>/tests/`, repo-untracked agent modules | Survives with local commit; possible rebase conflicts on upgrade | Low | Specs, ADRs, workflow docs, JSON schemas |
| **2 — Vendor core patch** | `<repo>/run_agent.py`, `<repo>/cli.py`, `<repo>/agent/` core files | Overwritten by git pull; protected via `~/.hermes/scripts/post-update-check.py --fix` | Medium | Runtime bug fixes, timeout guards, behavioral patches |

**Rule:** Level 0 >> Level 1 > Level 2. If a change can be a script or skill, it should be.

## Evolution Event Requirements

Every evolution event (external analysis, new workflow, config change, spec add) MUST produce:

### Artifact Requirement (at least one)

| Artifact | Location | Example |
|----------|----------|---------|
| Evolution note | `~/.hermes/notes/evolution/YYYY-MM-DD-slug.md` | Warp P0 multi-model governance |
| Skill | `~/.hermes/skills/<category>/<name>/SKILL.md` | A new workflow skill |
| Script | `~/.hermes/scripts/<name>.py` | verify-evolution-event.py |
| Spec | `<repo>/specs/<feature>/PRODUCT.md` + `TECH.md` | P0 governance spec |
| ADR | `<repo>/docs/adr/ADR-NNNN-slug.md` | ADR-0001 |
| Workflow doc | `<repo>/docs/workflows/<name>.md` | issue-taxonomy.md |
| Config/quorum change | `~/.hermes/config/<name>.yaml` | quorum.yaml tier update |

### Verification Requirement

| Change type | Minimum verification |
|-------------|---------------------|
| Spec/ADR/markdown | Review content; JSON schemas run `python3 -m json.tool` |
| Script | `python3 -m py_compile` + functional test |
| Runtime change | `pytest -q` with isolated `HERMES_HOME` (temp dir) |
| Config/quorum change | `hermes doctor` or manual syntax check |
| Local-brain category landing | Category-fill ledger under `30-tasks/` + concrete layer artifacts + `brainctl sync` + `brainctl reindex` + `brainctl search` hits for both the ledger and the mirrored evolution note |

### Upgrade Survival Clarity

The event note MUST document upgrade survival status:
- Level 0 files → "outside git, always safe"
- Level 1 files → "local commit exists; may conflict on rebase"
- Level 2 patches → "covered by post-update-check.py [check name]"

## Evolution Note Template

```markdown
# Evolution Event: <Source> → <Hermes-Outcome>

**Date:** YYYY-MM-DD
**Type:** methodology-migration | runtime-improvement | config-change | workflow-addition
**Source:** external project analysis | self-audit | user request

## Source Signal
- External repo/project analyzed (if any)
- Specific mechanisms extracted (with file paths if relevant)
- Adaptation principle: what was kept, what was discarded, why

## Hermes-Specific Output
- Local commit hash (if repo files were committed)
- Files created/modified table
- Multi-model evidence (if T3/T2 discussion was run)
- Verification results

## Level Classification
- Level 0 files: list
- Level 1 files: list
- Level 2 files: list

## Pitfalls Discovered
- What went wrong, what was learned

## Upgrade Survival
- How these artifacts survive `git pull`

## P1/P2 Candidates (from this event)
- What comes next
```

## Standard Verification Script

Every evolution event should pass this check:

```bash
python3 ~/.hermes/scripts/verify-evolution-event.py \
  ~/.hermes/notes/evolution/YYYY-MM-DD-slug.md \
  <any-other-new-artifacts> \
  --repo=/Users/charles/.hermes/hermes-agent
```

Prefer absolute/expanded paths for `--repo`; do not pass a literal `~` if the verifier does not shell-expand it. A literal `--repo=~/.hermes/hermes-agent` can still report `Final: COMPLIANT` for the note while hiding git context with `Git HEAD: N/A` and a "No such file or directory" repo error. Re-run with `--repo=$HOME/.hermes/hermes-agent` or `/Users/charles/.hermes/hermes-agent` when git ahead/behind evidence matters.

The script checks:
- Files exist and are non-empty
- Type-specific verification (json.tool, py_compile, content review)
- Git HEAD and ahead/behind
- At least one evolution note or repo artifact present
- Verification evidence in artifact content

### Self-Test Integration Pattern

After creating an evolution verifier, do not leave it as a manual-only script. Add it to `~/.hermes/scripts/self-test.py` so private-fork governance is continuously checked:

```python
verify_evo = os.path.join(HERMES_HOME, "scripts/verify-evolution-event.py")
r = subprocess.run([sys.executable, "-m", "py_compile", verify_evo], capture_output=True, text=True, timeout=10)
test("verify-evolution-event.py compiles", lambda: (r.returncode == 0, r.stderr[:200]))

p0_event = os.path.join(HERMES_HOME, "notes/evolution/2026-04-29-warp-p0-multimodel-governance.md")
p0_spec = os.path.join(HERMES_HOME, "hermes-agent/specs/p0-multimodel-governance")
p0_review_schema = os.path.join(HERMES_HOME, "hermes-agent/docs/specs/review.schema.json")
r = subprocess.run(
    [sys.executable, verify_evo, p0_event, p0_spec, p0_review_schema, "--repo=" + os.path.join(HERMES_HOME, "hermes-agent")],
    capture_output=True, text=True, timeout=30,
)
test("P0 evolution event is compliant", lambda r=r: (
    r.returncode == 0 and "Final: COMPLIANT" in r.stdout,
    r.stderr[:300] or r.stdout[-500:]
))
```

TDD evidence from 2026-04-29: first run showed `RED: self-test does not include evolution verifier yet`; after integration `self-test.py` reported `49/49 passed`. This is the preferred pattern for future evolution-governance tooling: **manual verifier → self-test coverage → evolution note → verify-evolution-event COMPLIANT**.

## Recent Evolution Log Audit Workflow

Use this when the user asks to "检查最近自进化更新日志", "check recent evolution logs", or audit whether private evolution is healthy. This is an audit/report workflow, not a new evolution event unless changes are made.

Recommended flow:

```bash
# 1. Latest evolution notes and compliance artifacts
ls -lt ~/.hermes/notes/evolution/*.md 2>/dev/null | head
python3 ~/.hermes/scripts/verify-evolution-event.py \
  ~/.hermes/notes/evolution/YYYY-MM-DD-slug.md \
  --repo="$HOME/.hermes/hermes-agent"

# 2. Current self-test gate
python3 ~/.hermes/scripts/self-test.py

# 3. Darwin/skill evolution and dashboard state
cat ~/.hermes/notes/engineering-cybernetics/autonomous-evolution-log.jsonl
cat ~/.hermes/notes/engineering-cybernetics/evolution-dashboard.md
cat ~/.hermes/logs/evolve.log

# 4. Cron state and latest failed/suspicious outputs
hermes cron list
find ~/.hermes/cron/output -type f -name '*.md' -mtime -3 | sort | tail -40

# 5. Private fork git context
cd ~/.hermes/hermes-agent
git status --short --branch
git rev-list --left-right --count HEAD...@{u} 2>/dev/null || true
git log --date=short --pretty=format:'%h%x09%ad%x09%s' -n 20
```

Report separately:
- **Formal evolution events**: latest notes, whether `verify-evolution-event.py` says `Final: COMPLIANT`, and any verification evidence.
- **Runtime health**: current `self-test.py` pass count; do not reuse stale pass counts from old notes.
- **Skill/Darwin health**: recent `skill_improved` / `skill_unchanged` records and dashboard score/trend.
- **Cron health**: distinguish script/pre-run errors, LLM summary idle timeouts, and genuine script failures.
- **Usage/telemetry health**: if `usage-score.py` or cron output shows low model breadth / real-call integrity, call that out separately from core self-test health.
- **Git state**: `ahead N, behind M` is normal for this private fork; only flag dirty tracked/untracked changes as upgrade-prep risk, not as a push requirement.

Common findings to recognize:
- Cron `script` fields that include arguments may be interpreted as a single file path by the pre-run script injector; prefer a no-argument wrapper script or verify that the cron runner parses args correctly.
- A cron job can have valid script output but still fail later from agent idle timeout while summarizing; classify this as cron-agent/wrapper reliability, not necessarily script logic failure.
- Evolution notes can be compliant while actual usage score is low; treat governance compliance and real multi-model utilization as separate dimensions.

## Controlled Upgrade Workflow (from `post-update-patch-healing`)

When upgrading (`git pull --ff-only origin main`):

```
Phase 0: Pre-flight — count ahead/behind, identify overlap, backup
Phase 1: Stash all tracked + untracked changes
Phase 2: git pull --ff-only → auto-triggers post-update-check.py --fix
Phase 3: Restore checker-modified files to HEAD, then stash pop
Phase 4: Verify — post-update-check dry-run + isolated pytest + hermes doctor
Phase 5: Cleanup — stash drop after verification passes
```

Full detail in `post-update-patch-healing` skill.

## Decision Record: No Remote Push

Every evolution governance event should record:

```markdown
| Decision | Rationale |
|----------|-----------|
| No push to upstream | Private fork; remote is read-only reference |
| No PR needed | Private evolution, not open-source contribution |
| Evolution notes outside git | Survives upgrades, no commit noise |
| Scripts in ~/.hermes/scripts/ | Update-safe; plugin migration possible later |
```

## Common Pitfalls

1. **Thinking `ahead N, behind M` is a failure.** It's normal for a private fork. Document this so future agents don't flag it as blocked.

2. **Committing `~/.hermes/` files to the agent repo.** Don't. These are Level 0 (update-safe outside the upstream source tree). If the user's `~/.hermes` directory itself is a local git repository, commit Level 0 evolution artifacts there (scripts, cron jobs, notes) as local version management; do not force them into `~/.hermes/hermes-agent`. If the user explicitly authorizes remote backup for Hermes itself / the personal assistant, push only a sanitized backup/export with secret/raw-memory guards; this does not change the no-push default for ordinary project repos and does not mean pushing the upstream-tracking `~/.hermes/hermes-agent` private fork. Commit only repo-level artifacts (Level 1) inside the Hermes agent source repo.

3. **Creating evolution events without verification.** An event without a passed verification check is just a draft. Always run at least py_compile or json.tool.

4. **Treating external analysis as "not real work."** Methodology migration from a different codebase is a legitimate evolution input — the value is in the adaptation and Hermes-native implementation, not the source code.

5. **Stopping at a local-brain design note.** When the event changes memory hierarchy, Obsidian/local-brain routing, or category taxonomy, create a category-fill ledger and concrete layer artifacts. A proper landing has evidence/review/evolution/task/project/skill/preference notes as appropriate, then `brainctl sync`, `reindex`, and `search` proof. If sync pulls mirrors into `~/.hermes/notes/brain/...`, include those scoped artifacts in the local `~/.hermes` commit when they are part of the record.

6. **Storing upgrade-dependent artifacts without a survival plan.** If an artifact is Level 1 or 2, the evolution note MUST document what happens on `git pull`. Otherwise it will be silently lost.

7. **Letting noisy `~/.hermes` runtime state pollute evolution commits.** The private Hermes home can have hundreds of modified logs, sessions, caches, pid/lock files, screenshots, checkpoints, and generated state files. For an evolution event, use scoped `git status --short -- <artifact list>`, scoped `git diff --check -- <artifact list>`, and scoped `git add -- <artifact list>`. Do not attempt to clean or commit unrelated runtime noise just to make global `git status` quiet.

8. **Recording deterministic green checks as if multi-model ratification passed.** Evolution notes may contain self-test/p10-health/verifier success and still need to say `not_certified` when T3 discussion has unresolved severity>=3 risks, agreement below threshold, or an implementation-required/empty-patches mismatch. Record both statuses separately: deterministic enforcement landed/tested, but certification blocked until ratification artifacts pass.

## Verification Checklist

- [ ] Artifact exists (at least one from the requirements table)
- [ ] Verification passes (py_compile / json.tool / pytest / hermes doctor)
- [ ] Upgrade survival path is clear and documented in the evolution note
- [ ] Evolution note includes: source signal, Hermes output, pitfalls, P1 candidates
- [ ] Local commit exists for repo artifacts (not pushed unless explicitly requested)
- [ ] `verify-evolution-event.py` run and reports COMPLIANT
