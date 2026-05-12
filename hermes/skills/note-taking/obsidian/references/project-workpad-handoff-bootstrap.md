# Project Workpad handoff bootstrap

Use this when the user asks whether a project is understandable in a fresh session, asks to preserve session/project memory, or when a repo needs durable cross-session agent context.

## Pattern

Maintain three layers, with different sensitivity boundaries:

1. Global memory: only stable pointers and routing facts.
   - Good: repo path, canonical Workpad path, key doc names, non-sensitive baseline rule.
   - Avoid: current TODO status, one-time OTPs, transient progress, secrets, full test credentials.
2. Project Workpad in the canonical brain vault: full project context and semi-sensitive local QA workflow.
   - Store product anchors, red lines, evidence ledger, boot capsule, test-environment method, and credential rules.
   - Keep disposable project test credentials here only when user explicitly provided them and they are needed for local QA.
   - Store OTP retrieval method, not OTP values.
3. Repo-local bootstrap file: short `AGENTS.md` or equivalent.
   - Points future agents to the Workpad and key docs.
   - Contains red lines and boot sequence.
   - Does not duplicate sensitive test credentials.

## Recommended boot capsule contents

Add a `New Session Handoff / Boot Capsule` section to the Workpad:

- Minimum commands: `git status --short && git log -3 --oneline`.
- Absolute Workpad path.
- Repo-local bootstrap path (`AGENTS.md`) if present.
- Key docs to read, with purpose for each.
- Product/PRD evidence paths; warn not to infer PRD semantics from memory.
- Current stable baseline and latest relevant commit.
- Verification status and known non-blocking warnings.
- Red lines and evidence-first rules.
- Sensitive-data rule: credentials/project QA methods stay project-scoped; one-time codes are never persisted.

## Repo `AGENTS.md` template

```md
# <project> agent bootstrap

Before making product, UI, architecture, or test claims, load the project Workpad:

`<absolute path to Workpad>`

Minimum boot sequence for a new session:

1. Run `git status --short && git log -3 --oneline` in this repo.
2. Read Workpad section `<handoff section>`.
3. Read these project docs as needed:
   - `<doc>` for <purpose>.
4. If a task depends on product/PRD semantics, use evidence paths recorded in the Workpad; do not infer from memory alone.

Red lines:

- Do not delete features/routes/buttons/fields to hide dead UI.
- Do not use mock success to hide real-backend drift.
- Do not claim UI/product completion without browser/test evidence.
- Keep test-environment credentials and OTP workflow project-scoped in the Workpad only.
- After code changes, run relevant tests/build and update evidence ledgers.
```

## Verification

After writing or updating the Workpad/bootstrap:

```bash
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "<project Workpad title>" --limit 5
python3 ~/.hermes/scripts/brainctl.py --json search "New Session Handoff" --limit 5
```

If the project has a Workpad self-check script, run it. If the repo bootstrap is committed, update the Workpad HEAD/latest-commit fields afterwards and re-run sync/reindex/search.

## Pitfalls

- Do not rely on compressed chat as the only handoff. It may be missing earlier turns.
- Do not put semi-sensitive QA data in global memory or public repo docs.
- If adding `AGENTS.md` creates a repo change, commit it locally when the user's workflow expects per-round local commits, then update the Workpad to point at the new commit.
- `brainctl.py --json search` can over-constrain mixed queries; verify with exact Workpad title and exact handoff heading separately.
