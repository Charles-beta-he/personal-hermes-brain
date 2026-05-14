# Project profile refresh from transcript + prototype repo

Use when a user asks to read a prior Claude/agent session, resume transcript, or external prototype/source repo and update a durable project profile.

## Durable facts worth landing
- Canonical local paths for the project and related source-of-truth repos.
- Stable UX conventions repeatedly enforced across screens (example: auth/OTP/password submit should preserve typed input and keep loading on the CTA).
- Stable architecture facts confirmed by code, migrations, route tables, or controller/domain structure.
- Prototype-source anchors: remote URL, local clone path, commit, app folders, PRD/handoff file locations.
- Navigation indexes that help future agents quickly map business domains to source folders/routes.

## Do not land
- Temporary task state, TODOs, rollout status, one-off bug narratives, or session-local blockers.
- Secrets/OTP/runtime credentials.
- Claims inferred only from prompts when code/repo evidence is available.

## Workflow
1. Find the transcript/session artifact.
   - Claude resume sessions often live under `~/.claude/projects/.../<session-id>.jsonl`.
2. Extract durable signals.
   - User prompts reveal requested domains and acceptance focus.
   - Edited-file lists reveal which areas actually changed.
   - Route tables, package manifests, migrations, and controllers confirm architectural facts.
3. Verify against current code.
   - Re-open the current project profile first so new fields fit the existing schema.
   - Confirm important claims in live files before writing them into the profile.
4. If the user provides a prototype/source repo, clone it and record:
   - remote URL
   - local path
   - pinned commit
   - app folders and stacks
   - PRD/handoff/HTML artifact locations
5. Build compact navigation artifacts.
   - For app prototypes, extract route paths from `App.tsx` or equivalent.
   - Group routes by first path segment (`card`, `remit`, `exchange`, `system`, etc.).
   - Record screen/page file indexes only when they help future task routing.
6. Update profile with durable sections only.
   - Good examples: `prototype_source_repo`, `prototype_source_navigation_index`, `frontend_runtime_conventions`, domain-architecture notes, `profile_update_history`.
7. Validate JSON after write.

## Example durable additions from UVISA-style work
- `prototype_source_repo`: source monorepo for app/admin/pad prototypes.
- `prototype_source_navigation_index`: route groups + file indexes for quick domain lookup.
- `frontend_runtime_conventions`: version pipeline, auth-loading UX invariants.
- Domain architecture sections such as FX multi-source quote aggregation.

## Pitfalls
- Don’t dump the full transcript into the profile; compress into stable facts.
- Don’t trust route extraction equally across apps; some apps use pathless layout routes, so extract explicit `path="..."` strings instead of naïve JSX nesting assumptions.
- Don’t record hosted prototype URLs as proof of backend semantics; source repo and live app code serve different evidentiary roles.
