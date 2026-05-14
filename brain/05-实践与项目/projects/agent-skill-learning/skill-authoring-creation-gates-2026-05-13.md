# Skill Authoring Creation Gates（2026-05-13）

Use before creating or materially changing a Hermes skill.

## Gate 0 — Need / anti-proliferation

- Prefer patching an existing umbrella/class-level skill.
- If the knowledge is a one-off session lesson, write a concise pointer in SKILL.md and details in `references/`.
- Create a new skill only when trigger class, workflow, pitfalls, and verification are reusable.

## Gate 1 — Shape

- Frontmatter begins at byte 0 with `---`.
- Required fields: `name`, `description`.
- Description <= 1024 chars; name <= 64 chars.
- Body is non-empty and peer-shaped: Overview, When to Use, workflow, pitfalls, verification checklist.

## Gate 2 — Trigger evals

Minimum prompt set:

- 3 positive prompts: explicit, implicit, contextual.
- 2 negative prompts: adjacent and generic false-positive controls.

## Gate 3 — Deterministic/read-back verification

- `skill_view(name)` reads the main SKILL.md.
- `skill_view(name, file_path=...)` reads each linked reference/template/script.
- Deterministic artifact checks exist for skills that write files, run tests, deploy, audit, or research.

## Gate 4 — Graph/steward

- Run `~/.hermes/scripts/skill-steward.py --graph-check --json` when graph edges or skill routing changed.
- Use warn-only report for exploratory changes, strict mode for production gate.

## Gate 5 — Closeout

- Commit skill changes if they are in git-tracked Hermes config/repo.
- Record exact changed paths and validation commands.
- Do not claim the current session can load a newly created skill unless verified in a fresh loader/session.
