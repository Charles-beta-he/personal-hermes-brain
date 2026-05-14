# Prototype source vs implementation repos in canonical project profiles

Use this when a project has both:
- a prototype/source-design codebase (for example a monorepo with app/admin/pad prototype source), and
- one or more current implementation repos.

Key rule
- Record the prototype source repo as the code-level source of truth for prototype intent, route/page structure, and product surface area.
- Record implementation repos separately as delivery landings. Do not let implementation repos overwrite the prototype-source role in the profile.

Required profile fields / patterns
- `prototype_source_of_truth`
  - `canonical_local_path`
  - `canonical_remote_url`
  - `canonical_commit`
  - explicit `truth_statement`
  - `subprojects` split by surface (for example c_end/admin/pad)
- `prototype_source_repo`
  - mark `repository_role=prototype_source_code_source_of_truth`
  - add a short `source_of_truth_statement`
- `prototype_anchors`
  - add `source_of_truth_local_path`
  - add a rule stating prototype tasks should resolve against the prototype source repo first
- For each implementation repo, store separate paths such as `admin_frontend`, `frontend`, `backend`, etc.

Admin-specific pattern
- If a local admin frontend exists separately from the prototype monorepo:
  - keep `uvdemo2.0/uvisa-admin` (or equivalent) as the prototype source repo
  - record the local admin repo as the current implementation repo
  - update admin-domain maps/playbooks so tasks follow a three-repo flow:
    1. prototype source repo
    2. local implementation repo
    3. backend controller repo
- Remove stale assumptions like 'no admin frontend exists' once local inspection proves otherwise.

Three-repo flow to encode into profiles/playbooks
1. Prototype source repo defines what the product surface should be.
2. Local implementation repo defines where the current FE work lands.
3. Backend repo defines real contracts, permissions, statuses, and data semantics.

What to patch when corrected by the user
- `paths`
- runtime/admin runtime sections
- exhaustive domain maps
- deep maps
- executable playbooks
- blind spots and redlines that were based on the old assumption
- profile update history with the corrected fact source

Verification checklist
- Confirm route/page counts from the local implementation repo before claiming it exists.
- Confirm the prototype repo still contains source pages/routes, not just static assets.
- After updating the profile, re-read the affected admin/domain entries and ensure they distinguish:
  - prototype source repo
  - implementation repo
  - backend repo
