# Fullstack Verification Workflow

When a project has frontend + backend as one integrated unit (not two separate projects), task completion must verify both sides work together locally.

## Pattern: Staged Verification Pipeline

Create `scripts/verify-fullstack.sh` with these stages:

```
1. be_compile   - Backend compile (mvn compile / gradle build)
2. be_test      - Backend tests (mvn test / gradle test)
3. be_boot      - Backend startup + health check (/actuator/health)
4. fe_test      - Frontend tests (pnpm test / npm test)
5. fe_build     - Frontend build (pnpm run build / npm run build)
6. fe_dev       - Frontend dev server startup
7. api_proxy    - API proxy verification (frontend → backend)
8. browser_e2e  - Browser end-to-end verification (optional)
```

## State Schema

Output verification results as JSON for audit:

```json
{
  "schema": "fullstack_verify_v1",
  "task_id": "...",
  "timestamp": "...",
  "final_status": "passed|failed",
  "blocking_stage": "be_boot|null",
  "blocking_layer": "backend|frontend|contract|null",
  "stages": [
    {
      "name": "be_compile",
      "layer": "backend",
      "status": "passed|failed",
      "exit_code": 0,
      "duration_ms": 1234,
      "log_tail": "...",
      "log_file": "/tmp/..."
    }
  ],
  "failure_taxonomy": {
    "backend_startup": "be_boot",
    "backend_health": "be_boot",
    "backend_compile": "be_compile",
    "backend_test": "be_test",
    "frontend_startup": "fe_dev",
    "frontend_test": "fe_test",
    "frontend_build": "fe_build",
    "api_contract": "api_proxy",
    "browser_e2e": "browser_e2e",
    "proxy_routing": "api_proxy"
  }
}
```

## Failure Taxonomy

| Failure Type | Stage | Layer | Meaning |
|-------------|-------|-------|---------|
| backend_startup | be_boot | backend | Backend failed to start |
| backend_health | be_boot | backend | /actuator/health not returning 200 |
| backend_compile | be_compile | backend | Compilation errors |
| backend_test | be_test | backend | Test failures |
| frontend_startup | fe_dev | frontend | Dev server failed to start |
| frontend_test | fe_test | frontend | Test failures |
| frontend_build | fe_build | frontend | Build errors |
| api_contract | api_proxy | contract | Proxy/CORS/auth mismatch |
| browser_e2e | browser_e2e | frontend | UI rendering/interaction failures |
| proxy_routing | api_proxy | contract | Frontend→backend routing broken |

## Integration with Taskpool

Add to project profile:

```json
{
  "fullstack_verification": {
    "script": "scripts/verify-fullstack.sh",
    "state_schema": "fullstack_verify_v1",
    "stages": [...],
    "failure_taxonomy": {...},
    "trigger_condition": "task_type == fullstack-integrated AND (backend_changed OR frontend_changed)",
    "skip_condition": "task_type == frontend-only OR task_type == backend-only"
  }
}
```

## AGENTS.md Red Line

```markdown
- **本地全栈验证**: fullstack-integrated 任务完成前必须运行 `scripts/verify-fullstack.sh`，
  验证后端编译→测试→启动→前端测试→构建→API代理→浏览器。失败阻断任务完成。
```

## Project Identity

Update project profile to declare fullstack identity:

```json
{
  "project_identity": {
    "description": "前后端一体化项目，不是两个独立项目",
    "single_project_rule": "前后端是同一项目的两个模块，不是独立项目"
  }
}
```

## Domain Map

Create `fullstack_domain_map` in project profile showing frontend↔backend mapping:

```json
{
  "fullstack_domain_map": {
    "auth": {
      "frontend": ["src/screens/auth/", "src/services/auth.service.ts"],
      "backend": ["api/.../AuthController.java", "app/.../auth/AuthService.java"]
    }
  }
}
```

## Multi-Model Design

When designing a verification workflow for a new project:
1. Use multi-model fanout to get 4 independent proposals
2. Synthesize from the intersection (3+ models agree on structure)
3. Implement as a script with clear stages, failure taxonomy, and state JSON
4. Integrate with project profile and AGENTS.md

## Pitfalls

1. **Don't block frontend-only tasks**: Only trigger fullstack verification for `fullstack-integrated` tasks
2. **Backend must be running**: Health check must pass before API proxy verification
3. **Use venv python, not system python**: System python may have different build flags
4. **Browser verification is optional**: Some tasks don't need browser smoke tests
5. **Failure taxonomy must be precise**: Distinguish backend/frontend/contract layers for actionable errors
