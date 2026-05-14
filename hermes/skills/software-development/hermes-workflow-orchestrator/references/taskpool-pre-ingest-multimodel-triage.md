# Taskpool pre-ingest multimodel triage

Use this when the user asks to add external repos, articles, or research items into the taskpool.

Key lesson from session:
- Do not treat taskpool add as raw capture followed by later reprioritization.
- Before formal task creation, run a fixed multimodel triage pass and assign P1/P2/P3 at creation time.
- Goal: keep taskpool independent; the pool should store already-governed tasks, not untriaged raw material.

Recommended flow:
1. Raw capture: collect the link/title/summary.
2. Pre-ingest triage: compare strategic leverage, relevance to Hermes core architecture, implementation tractability, urgency, overlap/duplication, and evidence quality.
3. Decide lane + architecture target + P1/P2/P3 before calling the taskpool add command.
4. Persist a short priority rationale inside the created task so downstream dispatch/autorun does not need to rediscover priority semantics.
5. If the user asks for batch ingest, triage the whole batch before any individual add calls so relative ordering and P1/P2/P3 semantics stay coherent across the batch.

Priority guidance:
- P1: directly changes Hermes control-plane, taskpool, permissions/safety, loop engine, prompt/context assembly, recovery, or other high-leverage architecture.
- P2: clearly valuable but not first-wave leverage.
- P3: watchlist/research backlog; interesting but lower urgency or less direct applicability.

Operational note:
- If the add command returns event-hook noise but the task file, sorted pool, and dashboard all refresh successfully, treat the lesson as verification discipline, not as a durable claim that hooks are broken.
