# Project Profile Injection for Task Execution

When executing work tasks in a multi-project task pool, each project has different tech stack, conventions, testing requirements, and acceptance criteria. Workers must receive this context before execution.

## Profile Schema

```json
{
  "project": "project-name",
  "display_name": "Human-readable name",
  "tech_stack": {
    "frontend": "React 18 + TypeScript",
    "backend": "Java Spring Boot",
    "test": "Jest + RTL",
    "build": "Vite"
  },
  "paths": {
    "frontend": "/path/to/frontend",
    "backend": "/path/to/backend"
  },
  "conventions": [
    "中文注释",
    "组件用 PascalCase",
    "不删功能/入口/字段"
  ],
  "test_cmd": "npm run test",
  "build_cmd": "npm run build",
  "acceptance": [
    "build 成功",
    "测试通过",
    "浏览器截图验证 UI 无破损"
  ],
  "backend_contract_policy": {
    "rationale": "Frontend regression can miss missing/incomplete/drifted backend APIs.",
    "must_scan_backend_when": [
      "Task touches auth, OTP, PIN/payment password, 2FA, device/session security, KYC, card, wallet, topup, exchange, remittance, notification, account/profile, money/status/time/order fields.",
      "Frontend uses a mock, compatibility alias, fallback, placeholder, hardcoded success, or TODO around an API.",
      "PRD/product logic depends on backend source-of-truth semantics rather than pure display text/style."
    ],
    "required_analysis": [
      "Read frontend service/store/screen path and corresponding backend controller/service/entity/repository path.",
      "Verify canonical vs legacy endpoints, auth requirements, envelope shape, fields, state transitions, and error semantics.",
      "If backend is incomplete or unsafe, implement backend TDD fix when write permission exists; otherwise record explicit backend blocker/follow-up."
    ]
  },
  "regression_coverage_policy": {
    "frontend_unit_and_build": "Covers frontend logic/types/rendering; does not certify real backend correctness.",
    "mock_contract": "Only proves the expected fixture contract; not real backend acceptance.",
    "real_backend_contract": "Requires backend source inspection and, when needed, local/live backend curl or Playwright evidence.",
    "backend_tdd": "Required when backend code changes; run targeted backend tests and compile/package evidence."
  },
  "forbidden": [
    "删除现有功能",
    "硬编码敏感信息",
    "Claiming a task done from frontend unit/build/mock regression alone when backend semantics are involved"
  ]
}
```

## Fullstack Project Identity Pattern

When a project has frontend + backend that share the same product goal, treat them as ONE project with two modules, not two separate projects. This changes how tasks are classified and verified.

### Project Identity Fields

```json
{
  "project_identity": {
    "description": "Frontend and backend are two modules of one project, not separate projects.",
    "single_project_rule": "Tasks default to fullstack-integrated; only pure UI styling or pure backend batch jobs are classified separately.",
    "frontend_repo": "/path/to/frontend",
    "backend_repo": "/path/to/backend"
  },
  "fullstack_domain_map": {
    "auth": {
      "frontend": ["src/screens/auth/", "src/services/auth.service.ts"],
      "backend": ["api/.../AuthController.java", "app/.../auth/AuthService.java"]
    },
    "wallet": {
      "frontend": ["src/screens/home/", "src/services/wallet.service.ts"],
      "backend": ["api/.../WalletController.java", "domain/wallet/.../WalletViewService.java"]
    }
  },
  "backend_complete_landing_policy": {
    "definition": "Backend changes must land full chain: Controller → Service → Domain/Repository → Test",
    "required_layers": [
      "Controller: API endpoints, request/response DTOs, auth annotations",
      "Service: Business logic, validation, state transitions, exception handling",
      "Domain/Repository: Entities, persistence, query methods",
      "Test: At least one JUnit test covering core path"
    ],
    "forbidden_patterns": [
      "Controller returns null/empty/hardcoded mock without TODO+issue tracking",
      "Service method body is empty or single-line return",
      "New Entity/DTO with no corresponding Repository or Service usage",
      "API claimed ready but returns HTTP 200 + empty body"
    ]
  }
}
```

### Task Classification for Fullstack Projects

Default classification: `fullstack-integrated` (frontend + backend modified together).

| Classification | When | Verification |
|---|---|---|
| fullstack-integrated | Default for most product tasks | Frontend tests + backend tests + browser acceptance |
| frontend-only | Pure UI styling, copy, i18n | Frontend tests + build |
| backend-only | Batch jobs, cron, infrastructure | Backend tests + compile |
| cross-cutting | Shared utils, validators, i18n | Both sides tested |

### Domain Map Usage

When a task touches a domain (e.g., "auth"), the domain map shows exactly which files to check on both sides. This prevents the common failure mode of modifying frontend service without checking if the backend controller actually implements the endpoint.

Worker context injection should include the relevant domain mapping:

```python
def get_domain_context(task, profile):
    domains = identify_domains(task)  # e.g., ["auth", "kyc"]
    ctx = ""
    for d in domains:
        mapping = profile.get("fullstack_domain_map", {}).get(d, {})
        if mapping:
            ctx += f"\nDomain '{d}':\n  Frontend: {mapping.get('frontend', [])}\n  Backend: {mapping.get('backend', [])}\n"
    return ctx
```

### Backend Complete Landing Gate

For fullstack-integrated tasks, backend changes must pass the complete landing gate:

1. **Controller layer exists** — endpoint defined, DTOs, auth annotations
2. **Service layer has real logic** — not empty body or single return
3. **Domain/Repository layer used** — entity persisted/queried
4. **At least one test passes** — `mvn test -Dtest=XxxTest`

Forbidden: claiming backend is "done" with only a Controller stub. The Service must contain actual business logic.

## Backend-Aware Regression Gate

For product delivery projects with an associated backend, the project profile should explicitly distinguish regression evidence levels. Frontend unit/build tests and mock-server fixtures are necessary but insufficient when the task touches backend-owned semantics. Add `backend_contract_policy` and `regression_coverage_policy` to the profile and inject them before the worker starts.

Worker closeout should label evidence separately:
- `frontend_unit_build`: component/store/service tests, type/build checks.
- `mock_contract`: expected frontend fixture/API shape only.
- `real_backend_contract`: backend source inspection plus curl/Playwright/local-live evidence when semantics matter.
- `backend_tdd`: targeted backend test + compile/package evidence when backend code changes.
- `remote_frontend_build`: deploy/package monitor evidence when user workflow requires push/build validation.

Trigger backend inspection when the task touches auth, OTP, PIN/payment password, 2FA, device/session security, KYC, card, wallet, topup, exchange, remittance, notification, account/profile, money/status/time/order fields, or PRD source-of-truth semantics. Do not close with a frontend shim if the backend endpoint is missing, unsafe, or semantically wrong.

## Injection Point

In any worker launch path, load the project profile and append it to worker context BEFORE the worker can start. This applies to normal dispatch, claim/handoff, autorun handoff, and parallel handoff paths.

```python
profile = load_project_profile(task.get('project', ''))
context = build_worker_context(task, group)
if profile:
    context += f'''
PROJECT PROFILE:
Name: {profile['display_name']}
Tech: {json.dumps(profile['tech_stack'])}
Conventions: {chr(10).join('- ' + c for c in profile['conventions'])}
Test: {profile.get('test_cmd', 'N/A')}
Acceptance: {chr(10).join('- ' + a for a in profile['acceptance'])}
Forbidden: {chr(10).join('- ' + f for f in profile.get('forbidden', []))}
'''
```

## Profile Directory

`~/.hermes/project-profiles/{project}.json`

Fallback: `~/.hermes/project-profiles/hermes.json` (default). The fallback is still a real required profile: if both project-specific profile and fallback are missing or invalid, dispatch must fail closed.

## Local Brain Taskpool Implementation Pattern

For `~/.hermes/scripts/brain_task_orchestrator.py`, implement profile injection as a deterministic gate, not just prompt decoration:

1. Add `PROJECT_PROFILES_DIR = $HERMES_PROJECT_PROFILES_DIR || $HERMES_HOME/project-profiles`.
2. Resolve candidates in order: safe exact project filename, slugified project filename, then `hermes.json` fallback.
3. `load_project_profile(project)` returns structured status: `project`, `fallback`, `missing`, or `invalid`, plus path/error/candidates.
4. Add row fields: `project_profile_status`, `project_profile_missing`, `project_profile_path`, `project_profile_error`.
5. Gate `Task.is_dispatchable()` and claim-bound lifecycle transitions (`claimed`, `running`, `review`, `done`) with `project_profile_failures()`.
6. Include profile context in every worker-start artifact: `dispatch_prompt_for_row`, `render_autorun_handoff`, and `render_parallel_handoff`.
7. Include missing/invalid profile in `selfcheck`/boundary invalid lists so the pool becomes visibly unhealthy rather than silently dispatching under-scoped workers.
8. Add TDD fixtures with temporary `$HERMES_HOME/project-profiles/hermes.json`; verify fallback injection, project-specific override, and full-missing fail-closed claim behavior.

Verification bundle for this pattern:

```bash
python3 ~/.hermes/scripts/test_brain_task_orchestrator.py
python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_orchestrator.py
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json  # execution_prompt contains PROJECT PROFILE
~/.hermes/scripts/p10-health.sh
```

If `brain_task_orchestrator.py list --json` is not parseable due legacy task-note control characters or unescaped text, import the module and call `sorted_tasks()`/`dispatchable_tasks()` directly for diagnostic scanning rather than weakening production gates.

## Multi-Model Verification After Completion (4 Models)

After worker outputs, verify with all 4 authenticated models. For this user's certification workflows, 4/4 authenticated agreement is required for certification; 2/4 or 3/4 is advisory only unless the active task explicitly relaxes the gate.

```python
def verify_with_models(task_title, worker_output, profile):
    prompt = f"""Verify task completion.
Task: {task_title}
Acceptance: {profile.get('acceptance')}
Worker output: {worker_output[-500:]}
JSON: {{"verified":true|false,"issues":[],"reasoning":"..."}}"""
    # Phase 1: Claude + GPT + DeepSeek concurrent
    # Phase 2: MiMo sequential (5 retries for empty response)
    # Need 3/4 verified=True to pass
```

Only mark DONE if verification passes. Otherwise enter self-optimizing loop.

## Self-Optimizing Loop (Rejection → Improve → Retry)

When verification rejects:
1. `save_rejection()` — record issues
2. `analyze_rejection()` — detect patterns (missing_build/test/screenshot/evidence)
3. `generate_enhanced_criteria()` — expand acceptance 4→8
4. `update_project_profile()` — auto-learn rules
5. Retry max 3 times, then FAILED + human escalation

Full details: multi-model-thinking skill `references/self-optimizing-verification-loop.md`.

## Session-derived project profile updates

When updating a project profile from prior agent session logs or resumed Claude Code sessions, use an evidence-first, caveated update path:

1. Parse logs into compact redacted evidence; do not paste or persist raw private transcripts.
2. Cross-check session-derived claims against repo files, Workpad/local-brain notes, docs, git status/log, and existing profile fields.
3. Build explicit claim-linked multi-model state for any requested multi-model review. Put claims in the top-level `claims` field and link evidence with exact claim ids in `evidence[].supports`.
4. Interpret multi-model artifacts conservatively:
   - `truth_status=grounded` + high evidence coverage proves the facts are supported.
   - It does **not** equal full profile-change certification if `discussion_result.status` is `not_certified`, approval count is low, agreement matrix is below threshold, or unresolved severity>=3 issues remain.
   - In that case, only apply low-risk durable profile clarifications that are directly grounded, and record `advisory_not_full_certification` or equivalent provenance in `profile_update_history` / Workpad.
5. Machine profile and human handoff must stay in sync: patch `~/.hermes/project-profiles/<project>.json`, append a concise Workpad section with source session/evidence/tick/caveat, then validate JSON, run any project-specific selfcheck, `brainctl sync`, `brainctl reindex`, and search for the new anchors.

### Evidence-source precedence for Lark/project profiles

For Lark/product project profiles, encode evidence precedence explicitly when the session reveals ambiguity:

- Current Lark task body/comments, PM/user screenshots, and explicit user instruction are authoritative for the current delivery.
- Prototype URLs are comparison anchors unless labeled as real integration environments. Store them with `role` and `not_for` fields so future agents do not treat prototype behavior as backend/API proof.
- Agent-generated taskpool `description` fields, old closeout summaries, and assistant commit-message interpretations are evidence pointers/placeholders, not standalone requirements. Trace them back to real task/comment/screenshot/prototype evidence before closeout.
- If task/comment/prototype/PRD conflict, record the conflict, chosen source for current delivery, and follow-up/product-doc update needed. Do not silently choose one source.

## Rich external project-profile import pattern

When the user provides a rich PROJECT-PROFILE / team profile file and says it contains useful task-execution knowledge, do not stop at an advisory review. Convert it into a safe, injectable execution aid while preserving the canonical operational profile.

Sequence:

1. Read the candidate profile and compute basic provenance: absolute path, line/byte count, sha256.
2. Build a redacted evidence pack for multi-model review. Never send or persist raw credentials, OTP/PIN values, cookies, tokens, API keys, account passwords, private emails, or `.env` values in the state.
3. Run multi-model review if requested/high-risk. Interpret results conservatively: `truth_status=grounded` means the reviewed claims are supported; it does not authorize wholesale profile replacement if discussion is `not_certified`, agreement is low, or severity>=3 issues remain.
4. Keep `~/.hermes/project-profiles/<project>.json` as the canonical operational profile. Do not overwrite canonical local paths, release branch policy, Lark evidence precedence, or verification gates with a team/profile document.
5. Create a sanitized reference artifact under `~/.hermes/project-profiles/evidence/` and, when useful for retrieval, a mirrored brain note under the project Workpad folder. The reference should preserve useful business/navigation/checklist content and explicitly remove/redact secrets and environment-specific paths.
6. Add compact structured fields to the canonical project profile so task execution can use the content without reading a huge Markdown file every time. Typical fields:
   - `sanitized_business_reference`: source path/hash, sanitized reference path, status/caveat, allowed use, not-for list.
   - `profile_import_preflight`: reject-if-contains secret classes, required evidence-tier labels, authority rule.
   - `<project>_business_navigation` or similar: domain/module map, cross-terminal impact checklist, shared invariants, known gaps.
7. Append a concise Workpad section with source, hash, multi-model tick, sanitized reference paths, and caveat (`truth_grounded_advisory_not_full_certification` when applicable).
8. Verify: JSON parse of the profile, redaction scan against known sensitive patterns and foreign absolute paths, project-specific selfcheck, `brainctl sync`, `brainctl reindex`, and `brainctl search` for the new reference.

Authority/evidence-tier rule for imported profile facts:

- `verified_prd`, `verified_code`, `lark_primary`, or explicit current user instruction can become authoritative for the current delivery.
- `secondary_source`, `team_claim`, `tbd`, and `advisory` are navigation only. They can point the agent to what to inspect, but cannot close a task or override current Lark task body/comments/PM screenshots/prototype anchors.

Practical lesson: if a file is unsafe to merge wholesale but valuable for execution, extract the value into a sanitized reference plus compact task-injection fields. Do not choose between “ignore it” and “import it raw.”

## Project-profile enforcement pitfall: documentation is not a gate

A project profile can exist, alias correctly, and contain the right human-readable policy while still failing operationally if the taskpool only checks “profile present.” For work/Lark projects, treat profile content as enforceable control-plane data:

1. Do not only inject a small hardcoded subset such as `tech_stack`, `paths`, `conventions`, `acceptance`, `forbidden`, `backend_contract_policy`, `regression_coverage_policy`. Include policy-bearing fields such as `lark_task_execution_policy`, `lark_evidence_policy`, `prototype_anchors`, `fullstack_domain_map`, `release_branch_policy`, `admin_scope_policy` / `scope_exclusions`, `design_asset_policy`, `closeout_policy`, and backend-owner routing policy.
2. Do not truncate critical policy lists/dicts with a generic `max_items=8`; late list items often contain the highest-value caveats (prototype precedence, generated-description caveats, no-closeout rules). Either mark policy keys as no-truncate or emit a structured compact summary with required fields preserved.
3. `project_profile_failures()` / dispatch gates must validate more than missing/invalid profile. They should classify the task before claim/handoff: admin/out-of-scope, prototype-asset-dependent, backend-owned-contract/security/money, frontend-only UI, or fullstack-integrated.
4. Completion gates must be lane/project aware. Generic token checks for “test/build/curl/backend” are not enough for Lark closeout. For target-bound closeout, require the profile’s explicit evidence labels (Final Handoff, task-specific proof, real/backend contract as applicable, remote build when required, 4/4 ratification or explicit human code-review/override depending on policy).
5. If a multi-model profile update is `truth_status=grounded` but `discussion_result.status=not_certified`, only apply low-risk text/profile clarifications. Do not assume runtime enforcement exists; create a separate hardening task or patch for gates/tests.

## Key Pitfalls

- Profile must be loaded BEFORE worker starts, not after
- Acceptance criteria must be machine-checkable where possible
- Forbidden list prevents common mistakes (deleting features, breaking H5, etc.)
- Default to hermes.json if project-specific profile missing
- Verification is a GATE, not a suggestion — reject if criteria not met
- Do not upgrade a grounded-but-`not_certified` multi-model discussion into full project-profile certification; use it only for directly supported low-risk clarifications and keep the caveat visible.
- Do not leave a rich user-provided profile as “analyzed only” when the user needs it to improve future task execution. Safely operationalize it through sanitized reference artifacts and compact structured navigation fields.

## Architecture linkage pitfall: skeleton links are not semantic control-plane links

When a project profile incident asks whether “the whole architecture lacks mutual linkage,” audit the full edge graph instead of only checking whether individual features exist.

Classify links into two kinds:

1. Structural/skeleton links: profile resolves by alias, dispatcher calls `project_profile_failures()`, handoff text contains a `PROJECT PROFILE` block, lifecycle has a done gate, proof-check exists, ratification gate exists.
2. Semantic/control-plane links: profile policy fields are consumed by typed classifiers and gates, task classification flows into worker contract and evidence labels, proof/review closeout is target-bound to those labels, multi-model intervention is triggered by work-task closeout semantics, and rejection/learning writes back to the same canonical profile/gate schema.

If skeleton links exist but semantic links are missing, report the diagnosis precisely: not “zero linkage,” but “profile policy is not an executable control plane.” Typical evidence:

- `project_profile_failures()` only checks missing/invalid profile and returns `[]` otherwise.
- `format_project_profile_context()` injects a hardcoded subset and truncates policy lists/dicts.
- policy-bearing fields such as `lark_task_execution_policy`, `lark_evidence_policy`, `prototype_anchors`, `fullstack_domain_map`, `release_branch_policy`, `admin_scope_policy`, `design_asset_policy`, `closeout_policy`, and backend-owner routing fields have no runtime references.
- `completion_gate_failures()` token-matches generic evidence instead of reading profile closeout/evidence labels.
- default `proof-check` skips non-done review backlog; `--include-active` warnings are not closeout blockers.
- automatic multi-model intervention may target generic PUA-loop/evolution triggers while ignoring work/Lark closeout semantics.
- parallel controllers such as `agent_team_controller.py` may duplicate profile loading/verification/self-optimization with weaker or inconsistent certification thresholds; demote these paths to advisory until they delegate to the canonical lifecycle gates.

Minimum repair order:

1. Add a typed `profile_policy_contract(profile, task)` that returns classification, required assets, backend/fullstack routing, required evidence labels, and closeout authority.
2. Make `project_profile_failures()` / dispatch / claim / lifecycle consume that contract fail-closed.
3. Make handoff emit the same contract without truncation; prompt text is secondary to machine fields.
4. Make `completion_gate_failures()` and `proof-check --include-active` enforce profile-derived closeout labels for review→done.
5. Link `task_multimodel_intervention_reasons()` to work-task closeout/profile-policy gaps, while keeping T2 advisory separate from T3 4/4 certification.
6. Consolidate or demote duplicated controller paths so there is one authority for profile resolution, proof gates, and certification thresholds.
