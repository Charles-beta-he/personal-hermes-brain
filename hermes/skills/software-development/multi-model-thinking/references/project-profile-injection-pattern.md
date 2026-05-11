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

In `delegate_to_worker()`, load profile and append to worker context:

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

Fallback: `~/.hermes/project-profiles/hermes.json` (default)

## Multi-Model Verification After Completion (4 Models)

After worker outputs, verify with all 4 models (3/4 must pass):

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
