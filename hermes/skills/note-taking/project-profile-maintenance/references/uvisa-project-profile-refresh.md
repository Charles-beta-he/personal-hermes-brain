# UVISA project profile refresh pattern

Use this as a concrete example of project-profile maintenance driven by historical session recovery and prototype-source mining.

## Inputs that proved useful
- Claude local session JSONL from a specific resume session.
- Existing Hermes project profile JSON.
- Current frontend repo.
- Current backend repo.
- Newly-cloned prototype/source repo with app/admin/pad code.

## Durable facts extracted
- Frontend UX conventions:
  - auth/otp/password flows should preserve entered values during loading
  - loading should bind to CTA/button before resetting full-form state
- Version pipeline:
  - package.json.version -> vite define / app version constant
  - git short SHA + UTC date -> build number
  - About page surfaces current + remote version info
- Backend FX architecture:
  - multi-source aggregation
  - pair / source / pair-source structure
  - snapshot repository + retention job
  - admin FX management entrypoint
- Prototype source truth anchors:
  - source repo remote/local/commit
  - three prototype apps: C-end, admin, pad

## High-value profile structures added
1. `prototype_source_repo`
   - remote, local_path, commit, scope

2. `prototype_source_navigation_index`
   - per-app route paths
   - route groups
   - screen/page file indexes
   - PRD / handoff document anchors

3. `prototype_business_domain_map`
   - prototype domain -> current frontend routes/screens/services/stores -> backend controllers
   - best landing rules for where to start investigation

4. `prototype_business_domain_map_exhaustive`
   - exhaustive pass bounded by visible route strings in prototype App.tsx files
   - separate C-end extra domains, admin domains, pad domains
   - explicit exhaustion boundaries

5. `prototype_business_domain_deep_map_v1`
   - four-layer map for priority domains:
     - prototype
     - current frontend
     - backend controller + imported anchors
     - test/evidence entrypoints

## Practical extraction sequence
1. Read the historical transcript/log and list modules/files mentioned.
2. Confirm the canonical profile write target.
3. Clone prototype/source repo if code-level prototype evidence is missing.
4. Extract route strings from prototype App.tsx files.
5. Group routes by first segment to create stable domain buckets.
6. Map each bucket to current frontend screens/services/stores.
7. Map each bucket to backend controllers.
8. For priority domains, inspect controller imports to capture service/domain/repository anchors.
9. Add test/evidence entrypoints so future work can verify changes quickly.
10. Append a compact profile history entry and validate JSON.

## Exhaustiveness language that worked well
Say the pass is exhaustive against:
- visible route strings in prototype App.tsx files
- controller-entry-level landing points in the current backend

Then explicitly say what is NOT yet exhaustive:
- dynamic/lazy routes not visible in App.tsx
- full service-to-repository call graphs
- task-specific assertions inside tests

## Pitfalls surfaced by this session
- A transcript-only update is not enough; current code and prototype source must confirm the facts.
- Backend mapping that stops at controller filenames is too shallow for future reuse; capture imported service/domain anchors too.
- Admin prototype routes can falsely look like current user-facing routes unless the profile states there is no current admin shell in the active frontend repo.
