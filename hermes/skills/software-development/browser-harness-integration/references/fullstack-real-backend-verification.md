# Full-stack real-backend verification pattern

Use this when a frontend UI task depends on a real local/staging backend and the project has both a frontend repo and a backend repo.

## Trigger

- Frontend mock/server behavior may drift from backend reality.
- User grants backend write access or asks for evidence-first full-stack validation.
- UI acceptance depends on backend auth, OTP, security state, platform config, FX/rates, funds movement, or PRD transparency rules.

## Procedure

1. Boot both repos before touching code:
   - Frontend: `git status --short && git log -3 --oneline`.
   - Backend: `git status --short && git log -3 --oneline`.
   - Read the project Workpad and red lines; keep test-account/OTP/PIN details in the Workpad only.
2. Confirm which environment is authoritative:
   - Prefer local frontend + local real backend when backend write/run access exists.
   - Use Railway/staging as regression/comparison evidence, not as a mock replacement.
   - Do not claim a mock-server pass as acceptance for real-backend contract behavior.
3. Start backend dependencies and verify health:
   - Check Docker first: `docker info --format '{{.ServerVersion}}'`.
   - Start compose services in the backend repo, usually in background if the agent tool treats compose as long-running: `docker compose up -d mysql redis rabbitmq && docker compose ps`.
   - Poll container health before starting the app.
4. Build and start the backend in a way that matches the repo shape:
   - In multi-module Maven repos, `mvn -pl app/uvisa-app -am spring-boot:run` can accidentally apply the Spring Boot goal to parent modules and fail with `mainClass`/parent errors.
   - Safer fallback: `mvn -pl app/uvisa-app -am -DskipTests package`, then launch the built jar.
   - If `java` is missing from the normal shell but Maven works, run `mvn -v` and use Maven's Java path directly.
5. Curl backend HTTP evidence before UI claims:
   - Health endpoint first.
   - Then the exact frontend service paths, not only controller unit tests.
   - For product transparency rules, inspect response keys/text for vendor/channel/callback/provider leakage.
   - For public config endpoints, test DB/config-store override paths as well as defaults; defaults can be safe while runtime rows still leak bank/channel/internal details.
   - For lifecycle resources such as cards, verify both the canonical/list endpoint and any legacy singleton compatibility endpoint. Empty canonical state must not be represented by an operable placeholder object in the legacy endpoint.
6. Run the frontend verification bundle:
   - Unit tests and build.
   - UI regression guard.
   - Mobile-H5/browser-harness guard with normal and short mobile viewports when applicable.
   - Record output dirs/reports in the UI ledger/Workpad.
7. Classify full-suite failures carefully:
   - A target contract test can be green while a full backend suite fails on pre-existing architecture gates.
   - Do not hide the failure; record it as baseline/pre-existing only if evidence shows the failing tests are unrelated to the slice.
8. Commit by repo scope:
   - Backend code/test changes in the backend repo.
   - Frontend docs/evidence/workflow changes in the frontend repo.
   - Brain/Workpad changes are not necessarily git-backed; check before assuming a commit is possible.

## Common pitfalls

- `docker compose up` may be blocked by agent long-running-command detection; split health checks and run compose in background.
- Killing background Java via process tools can fail if optional Python deps like `psutil` are missing; use `lsof -nP -iTCP:<port> -sTCP:LISTEN` and `kill <pid>`.
- Public/pre-login read endpoints can compile and unit-test green but return HTTP 401 until the security whitelist includes their path. Verify with curl against the running app.
- Public platform-config sanitizers must sanitize loaded runtime/config-store values, not just hardcoded defaults. Add a contract test that injects unsafe override keys/values and asserts the public response is safe.
- Legacy compatibility endpoints can manufacture false UI passes: a singleton `/api/card` placeholder may make no-card users see top-up/withdraw/CVV/freeze/limits flows. Backend should return explicit no-card semantics (`hasCard=false`, `operable=false`, neutral/empty fields); frontend should normalize that to `card=null` and block all card operation deep links with a non-operable empty state.
- Maven reactor target tests may fail in upstream modules with `No tests matching pattern`; add `-Dsurefire.failIfNoSpecifiedTests=false` when targeting a single test class through `-pl ... -am`.
- After rebasing a backend branch, any already-running Java process is still the old build. Kill/restart the backend before claiming local full-stack evidence against the rebased code.
- Very new JDKs can create false build failures in annotation processors. In `uvisa-backend`, JDK 25 can fail `adp-gsalary` compilation with Lombok/javac `TypeTag :: UNKNOWN`; use JDK 21 explicitly: `JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home PATH=$JAVA_HOME/bin:$PATH mvn ...`.
- Mockito/ByteBuddy can break on very new JDKs (for example Java 25). Prefer real small fakes/subclasses for simple contract tests when possible.
- Never copy real OTP values, payment PINs, full test account details, screenshots, or logs into repo docs or global memory. Keep them project-scoped in the Workpad and redact terminal summaries.

## Evidence checklist

- [ ] Both repo git status/log captured.
- [ ] Backend deps healthy.
- [ ] Backend app health 200.
- [ ] Exact service paths curl 200 and response shape checked.
- [ ] Target backend tests pass.
- [ ] Frontend tests/build pass.
- [ ] Browser/UI guards pass or findings classified.
- [ ] Evidence ledgers updated.
- [ ] Scoped commits made per repo.
