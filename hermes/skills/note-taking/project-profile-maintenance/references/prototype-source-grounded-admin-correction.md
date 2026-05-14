# Prototype-source-first admin correction and grounded three-repo mapping

Use this when a project profile mixes up three different realities:
1. prototype source code repo (what the prototype actually is),
2. local/current implementation repo (what is currently built),
3. backend repo (what the contract and persistence actually do).

This session reinforced a repeatable correction pattern for admin surfaces.

## Canonical repo roles

For each admin/business domain, explicitly record:
- `prototype_source_repo`: usually the source-code prototype monorepo subproject (for example `uvdemo2.0/uvisa-admin`)
- `implementation_repo`: the local/current shipped admin frontend repo (for example `uvisa-admin`)
- `backend_repo`: the backend repo that owns controllers/contracts/persistence

Do not collapse these into one path even if route names or page names match.

## Correction workflow when an assumption is wrong

If the profile currently says an admin frontend does not exist, but a local admin repo is later discovered:
1. Verify the local repo with code evidence (`src/App.tsx`, page inventory, route count, key page files).
2. Patch the profile immediately:
   - add local admin repo paths under `paths`
   - add an `admin_frontend_runtime` or equivalent section
   - repair any deep-map/playbook entry that treated admin as `prototype + backend only`
3. Preserve the prototype/source-of-truth distinction:
   - prototype source still defines the intended route/page structure
   - local admin repo defines the current implementation landing point
   - backend repo defines the controller/service/domain/repository truth

## Three-repo mapping shape

For each admin domain, prefer this shape:
- `prototype_routes`
- `prototype_source_files`
- `local_impl_files`
- `backend_controller_files`
- `source_vs_impl_rule`

Then deepen into:
- local page -> local service import edges
- backend controller -> service/domain/repository anchors
- persistence hints: repository candidates, migration candidates, table/query hints
- acceptance checklist: prototype check, local FE check, backend contract check, regression focus, closeout minimum

## Grounding rule for sparse local admin implementations

Do not invent a domain-specific local service or backend controller just because the page name suggests one.

Common case:
- local admin page exists
- page imports only shared transport/helpers such as `services/http.ts`
- backend does not expose a same-name controller

In that case:
- record the shared local service (`http.ts`, `wealthAdmin.ts`, `walletsAdmin.ts`, etc.) as the real implementation anchor
- use grounded backend controller candidates discovered from repo search/content search (for example counterparty/outflow/wealth/advisor controllers)
- mark them as candidates/hints, not certain one-to-one matches

## Good profile language

Prefer statements like:
- `uvdemo2.0 is the prototype source-code source of truth`
- `uvisa-admin is the current local implementation repo`
- `backend admin controllers are the contract/persistence truth`
- `prototype source and local implementation may intentionally drift; record the drift explicitly at closeout`

Avoid statements like:
- `there is no admin frontend`
- `this domain uses X controller` unless verified in code
- `this page must map to a same-name service/controller`

## Validation checklist after profile write-back

After any correction/update, verify:
- profile JSON reloads successfully
- admin deep map entries point to the right repo roles
- admin playbook says "prototype source first, then local impl, then backend"
- any old blind-spot text that denies the local admin repo is removed/replaced

## When to reuse this pattern

Use for any project where:
- prototype/source repo differs from implementation repo,
- admin UI lives in a separate local repo from C-end,
- the profile needs domain maps that separate design truth from implementation truth from backend truth,
- some domains are richly modeled while others only expose thin local pages and shared HTTP helpers.
