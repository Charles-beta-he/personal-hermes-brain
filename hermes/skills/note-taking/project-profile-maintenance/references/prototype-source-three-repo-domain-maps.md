# Prototype source vs implementation: three-repo domain maps

Use this pattern when a product has:
- a prototype source-code repo (not just screenshots/figma/static exports),
- one or more current implementation repos, and
- backend repos that define the real contract.

## Core rule
Record these roles explicitly in the project profile:
1. prototype source of truth repo
2. current local/frontend implementation repo(s)
3. backend/controller repo

Do not collapse them into one "frontend" bucket. For admin surfaces especially, the prototype repo and the current admin implementation repo can both exist and serve different purposes.

## Recommended profile fields
At top level:
- `prototype_source_of_truth`
- `prototype_source_repo.repository_role = prototype_source_code_source_of_truth`
- `paths.admin_frontend` / `paths.admin_frontend_src` when an admin impl repo exists
- `admin_frontend_runtime.prototype_source_repo`
- `admin_frontend_runtime.implementation_repo`
- `admin_frontend_runtime.source_vs_impl_rule`

For broad domain coverage:
- `prototype_business_domain_map_exhaustive`
- `prototype_business_domain_deep_map_v2_full`
- `prototype_business_domain_executable_playbook_v1`

For admin-heavy products, add dedicated admin structures instead of forcing them into C-end maps:
- `admin_domain_three_repo_map_v1`
- `admin_domain_executable_playbook_v1`
- `admin_domain_deep_map_v2`
- `admin_domain_persistence_map_v1`
- `admin_domain_acceptance_playbook_v2`

## Escalation ladder for domain mapping
1. Route/page inventory
   - prototype routes and source files
   - current implementation pages/screens/services/stores
   - backend controllers
2. Deep map
   - local page -> service import edges
   - backend controller -> service/domain/repository import edges
3. Persistence map
   - repository candidates
   - migration candidates
   - table/query hints
4. Acceptance playbook
   - prototype checks
   - local FE checks
   - backend contract checks
   - regression focus
   - closeout minimum

## Admin-domain pattern
For each important admin domain (users, KYC, wallets, transactions, CS, cards, system, etc.), store:
- prototype routes/pages from the prototype source repo
- local admin implementation pages/services
- backend admin controllers
- source-vs-implementation rule
- minimal verification across all three repos

## Pitfalls
- Do not assume "no admin frontend exists" just because the main C-end repo lacks admin pages; search sibling repos before encoding that assumption.
- Do not treat the prototype repo as mere reference material if it contains runnable source and route structure. Mark it as prototype source of truth.
- Do not stop at controllers for high-risk domains (wallets/KYC/cards/CS). Add repository/migration/table hints when state, money, time, permissions, approval, or config persistence are involved.
- Distinguish intentional drift between prototype and implementation from accidental divergence; record the difference instead of silently flattening it.

## Example trigger
User asks to "recover/update the canonical project profile from an old session and prototype code" and the codebase has multiple repos. Apply the three-repo mapping pattern immediately and write durable, code-grounded maps back into the profile.
