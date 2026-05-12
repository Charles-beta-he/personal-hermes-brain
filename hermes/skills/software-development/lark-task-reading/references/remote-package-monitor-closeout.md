# Remote package/deploy monitor for Lark task closeout

Use this when a Lark task is implemented in a repo that deploys to Railway or another remote package/deploy pipeline.

## Rule

A Lark task is not fully closed from local tests alone. Closeout requires:

1. Local deterministic checks pass: targeted tests, full relevant test/build, and browser/UI gates when applicable.
2. Remote package/deploy monitor reaches a terminal result for the relevant service.
3. Evidence is recorded without leaking secrets.

## Status vocabulary

- `closed`: local checks pass and remote package/deploy is `success`/`healthy`.
- `closed_with_remote_blocker`: local checks pass, but remote package/deploy is `failed`, `cancelled`, `timeout`, or dashboard access is blocked. The task can be reported as implemented, but not fully deployed/healthy.
- `not_closed`: local checks fail, required browser/product evidence is missing, or remote package/deploy was not checked.

## Railway pattern

Prefer the Railway CLI when it is already authenticated and linked to the correct project/environment; it gives safe structured status without browser screenshots or cookies:

```bash
railway status
railway service status --all --json
railway deployment list --service <frontend-service-name> --limit 3 --json
railway deployment list --service <backend-service-name> --limit 3 --json
```

Interpret `service status` as the current monitor gate: record service name, deploymentId, status, and `stopped`. For example, a closeout can cite `uvisa-app-tRnN: SUCCESS stopped=false deployment <id>` and `uvisa-backend: SUCCESS stopped=false deployment <id>`. If a local commit has not been pushed/deployed, phrase this precisely as “relevant remote services are currently healthy/successful,” not “this commit is deployed.” Treat `NEEDS_APPROVAL`, `stopped=true`, `FAILED`, `CANCELLED`, and long-lived `PENDING/BUILDING/DEPLOYING` timeouts as remote blockers. A public smoke HTTP 200 from an older deployment is useful availability evidence, but it does not upgrade a current `NEEDS_APPROVAL/stopped=true` frontend package to success.

Also compare the pushed task-loop commit with the Railway deployment `meta.branch` and `meta.commitHash`. If Railway tracks a different branch (for example `feat/uvisa-2.0`) and the pushed task-loop commit is not the deployed commit, the remote service can be healthy but the task's latest code is not remotely verified. Report this as `closed_with_remote_blocker` for latest-task deployment, with wording like: “service is SUCCESS and `/login` smoke is 200, but Railway currently deploys `<branch>/<hash>`, not pushed task commit `<hash>`; merge/deploy is required for latest-code verification.”

If CLI auth/linkage is unavailable but the local browser already has a Railway login session, use it to inspect:

- project/service deployment list,
- latest build/package/deploy status,
- deploy logs only for safe summaries,
- public smoke URL/health endpoint.

Before monitoring, resolve the exact Railway scope from project-local sources (AGENTS.md, Workpad, deployment docs, user-provided screenshot), not from memory or guessed service names. Record the project name and exact service names in the project closeout contract so future Lark tasks do not monitor the wrong service. If the dashboard is already open/logged in, a screenshot + visual read of the selected project/service/status is valid evidence; preserve only the screenshot path or redacted status summary, never session material.

Example project-scoped mapping shape:

```text
Railway project: <project name>
Frontend service: <frontend service name>
Backend service: <backend service name>
Dashboard evidence: <screenshot path or redacted URL/status>
```

Record only safe evidence:

- service name,
- deployment/build id or redacted dashboard URL,
- terminal status,
- checked timestamp,
- public smoke URL or health endpoint result.

Never record:

- Railway token,
- cookies/session data,
- OTP values,
- raw logs containing credentials/account identifiers,
- screenshots containing secrets.

If Railway dashboard access is blocked by login, still run a public smoke check when possible, but classify dashboard status as `access_blocked_needs_login`; do not upgrade this to full remote package success.

## Template

```text
Task: <Lark id/title>
Commit: <hash>
Local checks:
- <command>: PASS/FAIL/SKIP_WITH_REASON
Remote package/deploy:
- Service: <name>
- Deployment/build: <safe id or redacted URL>
- Status: SUCCESS/FAILED/CANCELLED/TIMEOUT/PENDING/ACCESS_BLOCKED
- Checked at: <timestamp>
- Smoke: <safe URL/health result>
Closeout status: closed | closed_with_remote_blocker | not_closed
Secrets policy: no OTP/token/cookie/private session data recorded.
```
