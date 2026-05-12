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

## Key Pitfalls

- Profile must be loaded BEFORE worker starts, not after
- Acceptance criteria must be machine-checkable where possible
- Forbidden list prevents common mistakes (deleting features, breaking H5, etc.)
- Default to hermes.json if project-specific profile missing
- Verification is a GATE, not a suggestion — reject if criteria not met
