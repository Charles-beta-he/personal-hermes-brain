# UVISA canonical profile mapping patterns

Use this when refreshing `uvisa-app-2.0` canonical profile from historical chat logs, Claude resume sessions, or prototype/source repositories.

## Durable lessons from this session

1. Treat the Hermes project profile as the single source of truth; append durable architecture and navigation facts, not one-off task logs.
2. When direct writes to `~/.hermes/project-profiles/*.json` are awkward from the active tool sandbox, use a short Python script to read/modify/write the JSON atomically.
3. For Claude resume recovery, parse the JSONL transcript to extract:
   - user-message summaries
   - edited file paths
   - stable architecture/UX facts worth preserving
4. For prototype repos, prefer code-grounded route extraction over screenshots/docs alone:
   - mine `src/App.tsx` for visible `path="..."` strings
   - inventory route groups by first segment
   - list screen/page files for each app (`uvisa-app`, `uvisa-admin`, `uvisa-pad`)
5. Record exhaustion boundaries explicitly: profile maps derived from visible `App.tsx` routes are exhaustive only for visible route strings, not hidden lazy routes or runtime-injected menus.

## Recommended profile sections

For source/prototype-backed refreshes, useful sections include:

- `prototype_source_repo`
  - remote URL
  - local clone path
  - pinned commit
  - role/scope of the repo
- `prototype_source_navigation_index`
  - repo docs / PRD anchors
  - app-by-app route counts
  - route groups
  - screen/page file hints
- `prototype_business_domain_map`
  - prototype domain -> current FE/BE landing points
- `prototype_business_domain_map_exhaustive`
  - all visible high-level route groups across app/admin/pad
  - exhaustion boundaries
- `prototype_business_domain_deep_map_v1/v2`
  - prototype -> current frontend -> backend controller/service/domain/repository -> evidence
- `prototype_business_domain_executable_playbook_v1`
  - preferred execution mode
  - pre-change must-check files
  - minimal verification set
  - shared-risk anchors

## UVISA-specific stable facts captured

- `uvdemo2.0` is a meaningful prototype/source repo, not just a static mock dump; it contains `uvisa-app`, `uvisa-admin`, and `uvisa-pad` source trees.
- Frontend version truth comes from `version.ts` logic (`package.json` version + build identifier display), so profile notes should point to code, not documentation only.
- Auth/OTP/payment-verify loading UX must preserve already-entered password/code during loading; this belongs in profile conventions because it is a stable UX redline.
- FX work evolved from single-source assumptions to multi-source aggregation; the profile should preserve source/aggregator/controller anchors rather than a temporary task narrative.

## Practical workflow

1. Recover transcript facts and edited files.
2. Verify every durable claim against current code.
3. Clone/open prototype/source repo and extract route inventory from code.
4. Build domain-to-landing maps:
   - prototype route group
   - current frontend routes/screens/services/stores
   - backend controllers and one-hop service/domain/repository anchors
   - evidence/test entrypoints
5. Write back only durable facts and explicit boundaries.
6. Validate JSON reload after every write.
