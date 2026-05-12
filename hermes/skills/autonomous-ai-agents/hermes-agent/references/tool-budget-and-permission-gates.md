# Hermes tool budget and permission gates

Use this when a task runs into single-session tool-call limits, long autonomous loops, subagent orchestration, or permission/safety problems.

## Core principle

Do not try to turn one Hermes chat session into an unbounded daemon. Treat the session tool-call limit as an engineering boundary: move state, evidence, and execution ticks into durable artifacts and deterministic scripts.

## Tool-call budget pattern

1. **Batch mechanical calls**: combine 3+ repetitive read/check commands into one `execute_code` or local script that emits compact JSON.
2. **Externalize state**: write task state, evidence bundles, issue ledgers, verification outputs, and commit hashes to Markdown/JSON artifacts.
3. **Use resumable ticks**: split long missions into `plan -> execute -> verify -> certify -> commit` ticks. Each tick has explicit inputs, outputs, stop gates, and resume commands.
4. **Delegate or background long work**: use `delegate_task`, background terminal jobs, `hermes chat -q`, tmux sessions, or cron for long-running fanout/tests. The parent session reads verifiable handles, not full transcripts.
5. **Keep deterministic controllers outside the LLM loop**: local scripts should own list/next/claim/release/done/dashboard/selfcheck-style operations so the LLM spends tool calls on decisions and evidence, not repeated state mutations.
6. **Handoff on limit**: if tool-call or context limits interrupt the task, output a recovery handoff with completed gates, incomplete gates, artifact paths, and the next command. Never claim full certification without the required artifact.

## Permission gate tiers

| Tier | Examples | Default |
|---|---|---|
| T0 read-only | read/search/status/diff/audit | allow |
| T1 derived write | dashboards, sorted pools, review artifacts, temp evidence | scoped allowlist |
| T2 canonical mutation | add/claim/release/done/retry task notes | typed command + atomic write + actor/lease/proof log |
| T3 external side effect | PRs, issues, messages, deploys, push | dry-run first + explicit scope + verification |
| T4 destructive/secrets | delete, credentials, prod data, unbounded shell | deny by default; require explicit user authorization |

## Dynamic/typed tool proxy pattern

Inspired by OpenAI Symphony/Codex App Server dynamic tool calls: keep high-privilege credentials and APIs in the host/orchestrator, and expose only typed, allowlisted functions to working agents/subagents.

Rules:
- Subagents get task summaries and read-only evidence by default, not secrets.
- Vault writes go through typed local controllers, not arbitrary shell edits.
- External-system tokens remain in the parent/host tool; return minimum necessary results.
- Destructive or external actions first produce a dry-run plan.
- Every mutating command writes proof/evidence suitable for later audit.

## Iteration budget reached warning

For the full P10 pattern and exact helper scripts, see `references/p10-iteration-budget-loop.md`.

When CLI or automation prints `Iteration budget reached (N/N) — response may be incomplete`, the agent hit its LLM/tool-calling iteration cap, not necessarily the context window. Diagnose before raising the cap:

1. Check the effective cap:
   ```bash
   hermes config | grep -A5 '^agent:'
   python3 - <<'PY'
   import yaml, pathlib
   cfg=yaml.safe_load(pathlib.Path('~/.hermes/config.yaml').expanduser().read_text()) or {}
   print((cfg.get('agent') or {}).get('max_turns'))
   PY
   ```
2. For gateway/cron, check startup logs for `Agent budget: max_iterations=...`. `config.yaml` `agent.max_turns` should override stale `.env` `HERMES_MAX_ITERATIONS`; if it does not, restart gateway and inspect the config→env bridge.
3. If the task is a long autonomous mission, do not solve it only by increasing `agent.max_turns`. Split into resumable ticks (`plan -> execute -> verify -> certify -> commit`) and write handoff/proof artifacts after each tick.
4. Prefer script-first cron (`no_agent=True` for deterministic watchdog/control-plane jobs, or script + tiny summarizer prompt for reports) so repeated mechanical work does not burn iterations.
5. If more headroom is genuinely needed, raise the cap explicitly:
   ```bash
   hermes config set agent.max_turns 120
   # restart CLI/gateway after config changes
   ```
   Keep separate child-agent budgets in mind: `delegation.max_iterations` controls `delegate_task` children.
6. Add a recovery rule to automation prompts: if close to the cap, produce a non-empty final handoff with completed gates, incomplete gates, artifact paths, next command, and whether the task is safe to resume.

## P10 iteration-budget strategy

Treat `Iteration budget reached (N/N)` as a control-system saturation signal. The policy is four-layered:

1. **Strategic policy**: keep normal `agent.max_turns` bounded; raise it only for explicitly scoped long runs after a handoff/proof path exists.
2. **Deterministic doctor**: run `python3 ~/.hermes/scripts/iteration_budget_doctor.py --json` to inspect effective caps, recent warning hits, cron job risk shape, and task-pool automation exposure. The doctor is read-only and never emits secret values.
3. **Bounded task tick**: run `python3 ~/.hermes/scripts/brain_task_budget_tick.py --json` before long local-brain work. It selects one canonical task/dispatch hint, classifies risk/execution mode, computes a safe remaining budget, and writes `~/.hermes/artifacts/iteration-budget/*/handoff.md`.
4. **LLM execution boundary**: execute at most one bounded slice after claim. If the tick says `handoff_required`, stop and resume later instead of pushing into an incomplete response.

Execution modes:

| Mode | Use | Budget behavior |
|---|---|---|
| `script_first_no_agent` | deterministic cron/control-plane jobs | prefer `no_agent=True`; no LLM loop |
| `tiny_summarizer` | script output needs a short human summary | script collects evidence; LLM only summarizes |
| `bounded_agent_tick` | local-brain task execution | claim one task, execute one slice, proof or handoff |
| `single_shot_capped` | small interactive one-off | hard cap + no recursive fanout |
| `manual` | high-risk/P0/destructive/external side effect | human-triggered only |

PUA-loop rule: when a loop approaches the cap, do not rationalize a partial answer as completion. Write a handoff artifact, release/retry the task if applicable, and make the next bounded command explicit.

## Verification checklist

- A durable artifact exists for each tick or decision gate.
- Long fanout/test jobs have timeout/degraded records.
- No secrets are copied into prompts, state JSON, Markdown, or git.
- Scoped commits exclude `.env`, `auth.json`, caches, screenshots, checkpoints, and tick directories unless explicitly intended.
