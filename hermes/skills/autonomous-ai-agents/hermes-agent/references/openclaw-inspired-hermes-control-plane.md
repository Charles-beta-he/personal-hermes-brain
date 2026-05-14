# OpenClaw-informed Hermes control-plane evolution

Use this reference when the user asks to improve Hermes by studying OpenClaw or another agent framework without connecting to the live external system.

## Core boundary

- Treat OpenClaw as a reference architecture / evidence source, not a runtime dependency.
- Do not connect to live OpenClaw.
- Do not import OpenClaw runtime code into Hermes runtime.
- Do not modify the external OpenClaw repo as the main deliverable.
- Keep Hermes as the subject: local scripts, helpers, hooks, config, benchmarks, and post-update checks.
- Default behavior must remain compatible: new control-plane features should be opt-in and fail-soft.

## Pattern to apply

1. Analyze the external repo for reusable control-plane patterns.
   - manifest-first capability catalog
   - activation planning
   - scoped repository policies such as AGENTS.md
   - typed gateway / trace protocols
   - memory-host style contracts
   - plugin / extension boundaries
2. Convert patterns into Hermes-local artifacts under `~/.hermes/openclaw-gap/` or an equivalent evidence directory.
3. Implement reusable Hermes helpers rather than one-off reports.
4. Add behavior-level regression checks.
5. Wire those checks into Hermes' existing update/check workflow so future upstream updates cannot silently erase or weaken the local hardening.

## Known-good Hermes implementation shape

Current proven files from the OpenClaw-informed hardening effort:

- `~/.hermes/scripts/openclaw_to_hermes_gap.py`
  - Generates gap/control-plane artifacts from the OpenClaw OSS repo.
  - Produces manifest index, activation plan, scoped rules, protocol inventory, memory contract, gap matrix, dashboard.
- `~/.hermes/hermes-agent/agent/openclaw_control_plane.py`
  - Runtime-light helper module.
  - Provides activation hints, strict JSONL/schema validation, scoped policy context rendering, memory write-gate checks, benchmark, and config helpers.
- `~/.hermes/scripts/hermes_openclaw_control_plane.py`
  - CLI wrapper for helper commands.
- `~/.hermes/hermes-agent/agent/task_router.py`
  - Optional/fail-soft activation hints only when config enables them.
  - Must not change default provider/model/tier routing.
- `~/.hermes/hermes-agent/tests/agent/test_openclaw_control_plane.py`
  - Behavior tests for activation hints, default-off config, strict validator, policy context, memory gate, and TaskRouter opt-in behavior.
- `~/.hermes/scripts/post-update-check.py`
  - Productized regression home. Add/update a check like `openclaw_productization_regression` rather than creating a parallel update mechanism.

## Productization lesson

When the user says this should be part of their existing update/check/merge logic, extend `post-update-check.py` instead of proposing a separate flow.

The productized check should:

1. Verify the critical files exist.
2. Compile helper/router/tests with `python3 -m py_compile`.
3. Run `hermes_openclaw_control_plane.py benchmark`.
4. Use pytest if installed.
5. Fall back to direct test-function invocation when pytest is absent.
6. Confirm experimental flags remain default-off.

Important: pytest is an optional runner inside post-update regression, not a runtime dependency and not a replacement for post-update-check.

## Default-off config shape

Keep this block explicit and false by default in `~/.hermes/config.yaml`:

```yaml
openclaw_control_plane:
  activation_hints: false
  scoped_policy_context: false
  memory_write_gate: false
```

`load_experimental_config()` should prefer Hermes-compatible YAML loading when available, then fall back to a tiny parser so post-update checks remain dependency-light.

## Strict validation rules

For JSONL / trace / case / review / final-gate validators, protect against quiet schema drift:

- required fields must exist
- basic types should match
- enum values should be checked
- unknown/extra fields should be rejected against a kind-specific allowlist
- unredacted tokens/secrets/cookies/bearer strings must fail
- `final_gate` with verdict `pass` must not have blocked items or failed checks
- review verdict entries must be valid

The important lesson: “strict validator” means unknown fields fail-closed. A future reviewer should not have to rediscover this.

## Scoped policy and memory-gate safety

- `policy-context` should render root-to-leaf policy context, but should not automatically inject into prompts until a separate safety review enables it behind config.
- `memory_write_gate` should evaluate proposed writes, but should not automatically write durable memory until separately wired behind config.
- Semantic memory must be durable and non-WIP.
- Procedural skill promotion requires verification evidence.
- Session recall is query-only, not a durable write target.

## Verification commands

Use these before claiming completion:

```bash
cd ~/.hermes/hermes-agent
python3 -m py_compile agent/openclaw_control_plane.py agent/task_router.py tests/agent/test_openclaw_control_plane.py
python3 ~/.hermes/scripts/hermes_openclaw_control_plane.py benchmark
python3 ~/.hermes/scripts/post-update-check.py
```

If pytest is unavailable, a manual fallback test runner is acceptable and should also be embedded in post-update-check.

## Acceptance bar

A complete productized pass should show:

- helper benchmark passes all checks
- post-update-check reports the OpenClaw productization regression as OK
- default config remains false
- TaskRouter default output is unchanged
- policy and memory helpers do not auto-execute
- P10/final-gate or equivalent self-evolution gate passes when the task is part of Hermes self-improvement
