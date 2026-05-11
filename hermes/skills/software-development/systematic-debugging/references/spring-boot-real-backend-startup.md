# Spring Boot real-backend startup debugging notes

Use this when a Java/Spring multi-module backend must be started for real integration verification instead of relying on mocks.

## Lessons from uvisa backend session (2026-05)

### 1. `spring-boot:run -pl <app>` may fail before source changes are wrong
Symptom:

```text
Could not find artifact com.<project>:<module>:jar:... (compile)
```

Cause: app module depends on sibling reactor modules that are not installed in the local Maven repository when running only the app module.

Fix:

```bash
mvn -pl app/<app-module> -am -DskipTests install
mvn -pl app/<app-module> spring-boot:run
```

### 2. Do not exclude infrastructure auto-config if application beans hard-require it
Symptom:

```text
required a bean of type 'org.apache.rocketmq.spring.core.RocketMQTemplate' that could not be found
```

Cause: using `--spring.autoconfigure.exclude=...RocketMQAutoConfiguration` while a controller/service constructor requires `RocketMQTemplate`.

Concrete uvisa example (2026-05):

```text
APPLICATION FAILED TO START
Parameter 0 of constructor in com.uvisa.integration.cobo.CoboWebhookController
required a bean of type 'org.apache.rocketmq.spring.core.RocketMQTemplate' that could not be found.
```

In that case, the failure was caused by a local smoke command that excluded RocketMQ auto-config while `CoboWebhookController` was still a production bean. Treat that command as an invalid partial harness, not as evidence that the product slice failed. Check `docker compose ps` too: an unhealthy `rocketmq-namesrv` means the real fix is infra/profile wiring, not suppressing the dependency.

Action: either keep the auto-config and start/point the real dependency, or make the dependent bean conditional/mockable in a deliberately named test profile. Do not claim real-backend verification if a required production bean is silently excluded.

### 3. Ambiguous mappings are startup-contract bugs, not frontend bugs
Symptom:

```text
Ambiguous mapping. Cannot map 'legacyApiController' method ...
to {GET [/api/fx/rates/{from}/{to}]}: There is already 'fxRateController' bean method ... mapped.
```

Root cause class: compatibility/legacy controller duplicated a canonical controller endpoint.

Preferred fix:
- Keep the canonical controller endpoint.
- Keep only non-conflicting legacy compatibility endpoints.
- Add a contract test or startup smoke to catch duplicate mappings.
- Run real Spring startup after the source-level test passes.

### 4. Real-backend verification order
1. Inspect exact startup error and stack trace.
2. Verify infra containers/ports without printing secrets.
3. Install reactor dependencies if using `-pl` app-only commands.
4. Start with production-like dependencies; avoid excluding required beans.
5. Treat Spring startup failures as backend P0 until resolved.
6. Only after backend starts, run frontend/browser integration verification.
