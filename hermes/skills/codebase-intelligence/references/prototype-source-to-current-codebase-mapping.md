# Prototype-source repo to current-codebase mapping

Use this when a product has a separate prototype/demo/source repo and the active implementation lives in different frontend/backend repos.

Durable pattern
- Ground project-profile updates from two evidence sources:
  1. prior agent transcript or Claude resume JSONL for already-landed decisions and touched files
  2. cloned prototype-source repo for route/page structure, PRD anchors, and code-level prototype references
- Prefer class-level artifacts in the project profile, not session prose:
  - `prototype_source_repo`
  - `prototype_source_navigation_index`
  - `prototype_business_domain_map`
- For navigation extraction, inspect each app's `App.tsx` route declarations and key source buckets (`screens/`, `pages/`, `components/`, `layouts/`).
- If JSX route extraction undercounts because of pathless wrapper routes, fall back to extracting explicit `path="..."` strings from `App.tsx` and group by first segment.
- Record durable repo anchors:
  - remote URL
  - local clone path
  - inspected commit SHA
  - top-level README role statement
  - primary PRD / handoff / standalone HTML artifact paths

Recommended profile shape
- `prototype_source_repo`: remote/local/commit/role/subprojects/evidence
- `prototype_source_navigation_index`:
  - repo docs and top-level artifacts
  - per-app route counts, route paths, route groups, and page/screen file indexes
- `prototype_business_domain_map`:
  - prototype routes for a business domain
  - current frontend routes, screen dir, screen files, service files, store files
  - current backend controllers and service hints
  - best landing rule for FE-first vs BE-first work

UVISA-derived example domains
- remit
- exchange
- card
- topup
- payout
- me_security

Pitfalls
- Do not save session-local TODO state or raw transcript dumps into the profile.
- Do not treat hosted prototype URLs alone as sufficient when source repo code is available; add the cloned repo as a code-level reference.
- Do not rely only on naive `<Route ...>` scraping for admin apps with guarded/pathless parent routes.
- Keep sensitive runtime credentials out of the profile; save only safe anchors to where evidence can be read on demand.

Verification
- Re-open the updated project profile JSON and parse it.
- Confirm the new fields contain real paths/commits/routes from the inspected repo.
- Ensure route-group keys and current landing paths are stable business domains, not one-off task labels.
