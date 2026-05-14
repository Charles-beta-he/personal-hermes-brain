---
name: project-profile-maintenance
description: Maintain canonical project profiles by recovering historical context, mining prototype/source repos, and writing durable code-grounded navigation maps back into the profile. See references/prototype-source-grounded-admin-correction.md for the correction pattern when prototype source, local admin implementation, and backend truth diverge. See references/prototype-source-vs-implementation-repos.md for the base pattern when prototype source code and local implementation repos diverge (especially admin surfaces), and references/prototype-source-three-repo-domain-maps.md for the deeper three-repo/domain-map/persistence/acceptance pattern.
---

# Project Profile Maintenance

Use when you need to update a canonical project profile / project memory file after historical work, resume sessions, prototype repo discovery, or codebase archaeology.

## Triggers
- User asks to "更新项目画像", "refresh canonical profile", or restore project context from older sessions.
- You need to reconcile prototype sources, current frontend/backend code, and historical transcripts into one durable profile.
- You need a reusable landing map from product/prototype domains to current implementation files.

## Goals
1. Preserve only durable project facts.
2. Ground every profile addition in code, routes, migrations, or session evidence.
3. Separate stable profile facts from session-specific detail.
4. Produce navigation aids that future sessions can use immediately.

## Workflow
1. Locate the current canonical profile.
   - Check agent-owned profile stores first (for example Hermes project-profiles JSON).
   - Treat the profile as the write target unless the repo docs explicitly say another file is the source of truth.

2. Recover historical evidence before editing.
   - Read the referenced session transcript/log.
   - Extract durable facts only: changed modules, durable UX rules, architecture shifts, route groups, verified data flows, prototype anchors.
   - Ignore transient items: branch state, temporary TODOs, one-off failures, raw credentials, ephemeral timestamps unless they explain profile lineage.

3. Inspect current code to confirm the facts still exist.
   - Frontend: routes, screen directories, services, stores, tests.
   - Backend: controllers first, then imported services/domain/repository anchors, migrations, tests.
   - Prototype/source repos: App.tsx/router declarations, page/screen folders, README/PRD anchors.

4. Add profile data in layers.
   - Durable conventions: UX rules, versioning pipelines, architecture invariants.
   - Prototype anchors: hosted prototypes, source repos, commit/hash when relevant.
   - Navigation index: route groups and file indexes for prototype apps.
   - Domain landing maps: prototype domain -> current frontend -> backend controller anchors.
   - Deep maps for priority domains: prototype -> frontend -> backend -> test/evidence entrypoints.

5. Record lineage.
   - Append a compact profile_update_history entry with date, source repo/session, and truth status.
   - Keep history declarative; do not paste the whole task narrative.

6. Validate the profile.
   - Re-load the JSON/YAML after writing.
   - Sanity-check key sections and counts.

## What belongs in the profile
- Stable route/domain structure.
- Durable frontend/backend landing points.
- Verified integration architecture.
- Canonical prototype/source locations.
- Cross-session UX constraints that affect future implementation.

## What does NOT belong in the profile
- Temporary task progress.
- Unverified guesses.
- Secrets/tokens.
- Resolved environment hiccups.
- Large transcript dumps.

## Recommended structures
- `prototype_source_repo`: remote, local clone path, commit, scope.
- `prototype_source_navigation_index`: per app route groups, screen/page indexes, PRD anchors.
- `prototype_business_domain_map`: prototype domain -> current frontend/backend landing points.
- `prototype_business_domain_deep_map_v1`: priority-domain four-layer maps.

## Pitfalls
- Do not stop at prototype routes; always map them to current code.
- Do not stop at backend controllers; capture imported service/domain/repository anchors so later sessions know where to descend.
- Do not mix session-local details into the canonical profile; put them in a reference file instead.
- Do not treat admin prototype routes as current C-end UI features if the active product repo has no matching admin shell.
- Do not claim exhaustiveness without stating the boundary, such as "visible routes in App.tsx" versus dynamic/lazy routes.

## Verification

## Reference add-ons
- `references/uvisa-canonical-profile-mapping.md` — UVISA-derived pattern for recovering Claude resume context, extracting visible prototype routes from `App.tsx`, building domain-to-landing maps, and writing executable profile sections back to the canonical JSON.

 checklist
- Canonical profile file re-parses successfully.
- Every newly-added section points to real files/routes/controllers.
- History entry added.
- Exhaustion boundary stated when claiming broad coverage.
- Session-specific detail moved to a reference file when useful.

## References
- See `references/uvisa-project-profile-refresh.md` for a concrete example of transcript recovery + prototype repo mining + four-layer mapping.
