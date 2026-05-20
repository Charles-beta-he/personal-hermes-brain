# 2026-05-20 Claude Code runtime provider routing patch

Runtime source commit in `~/.hermes`:

- `21cedc9 fix: route claude models through claude-code`

Patch file:

- `2026-05-20-claude-code-runtime-provider.patch`

Purpose:

- Preserve the verified runtime fix for Hermes/local-brain multi-model routing.
- Canonical Claude models (`claude-opus-4-7`, `claude-sonnet-4-6`) resolve to runtime provider `claude-code` when the local `claude` CLI is available.
- Keep configured provider provenance (`configured_provider=anthropic`) separate from runtime provider (`provider=claude-code`).
- Prevent Anthropic API-key quota / extra-usage errors from being treated as Claude Code / Claude Max OAuth exhaustion.

Verified before archival:

- Focused pytest: `176 passed, 28 subtests passed`
- Python compile: `consult_models.py`, `model-router.py`
- `model-router.py probe`: Claude canonical models show `provider=claude-code`
- Claude CLI smoke: returned `OK_CLAUDE_CLI`
- `consult_models.call_discussion_model('claude-opus-4-7', ...)`: returned `OK_CLAUDE_CONSULT`
- T3 multi-model smoke: planner fan-out 4/3, Claude plan metadata `provider=claude-code`, `adapter=claude-code`
- `post-update-check.py --fix`: exit 0, 16 OK, 0 fixed; only pre-existing skill_quality / steward notes
- taskpool `proof-check --json`: PASS

Apply locally from `~/.hermes` if needed:

```bash
git am /Users/charles/personal-hermes-brain/hermes/runtime-patches/2026-05-20-claude-code-runtime-provider.patch
```
