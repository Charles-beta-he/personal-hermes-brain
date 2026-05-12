# P10 iteration-budget loop for Hermes automation

Use this when an automated Hermes task can hit `Iteration budget reached (N/N) — response may be incomplete`, or when designing cron/task-pool/idle-runner work that may run longer than one agent loop.

## Core lesson

Treat the warning as a control-system saturation signal, not as a reason to blindly raise `agent.max_turns`. The safe pattern is: deterministic diagnosis -> bounded task tick -> durable handoff -> proof-gated resume/done.

## Evidence-backed implementation pattern

1. Diagnose effective caps, recent hits, and session-level self-correction signals:

```bash
python3 ~/.hermes/scripts/iteration_budget_doctor.py --json
python3 ~/.hermes/scripts/post-session-autopsy.py --recent 1 --write
```

The post-session autopsy must classify tool-call/iteration cap messages such as "maximum number of tool-calling iterations allowed" as `iteration_budget_saturation` / `control_system_saturation`, not as generic tool failure. User corrections like "揪出来的问题" or "自我修正是否触发" should also be captured as correction signals so the double-loop learning path has an auditable trigger.


Expected responsibilities:
- report `agent.max_turns`, `delegation.max_iterations`, compression config, and whether `HERMES_MAX_ITERATIONS` is present;
- count recent iteration-budget warnings in logs/sessions;
- summarize cron job shape: `no_agent`, script-first, prompt-driven, agent-only;
- summarize task-pool items related to automation/budget;
- never emit secret values or log/session snippets.

2. Prepare one bounded task slice:

```bash
python3 ~/.hermes/scripts/brain_task_budget_tick.py --json
```

Expected responsibilities:
- choose one canonical local-brain task or explicit `--task`;
- classify risk and `execution_mode`;
- compute a safety margin before the model loop cap;
- write `~/.hermes/artifacts/iteration-budget/*/handoff.md`;
- default to no mutation: no claim, no execution, no done.

3. Execute only after gates pass:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py claim <task-id> --actor <actor> --ttl-minutes 60 --json
# execute one bounded slice
python3 ~/.hermes/scripts/brain_task_orchestrator.py done <task-id> --evidence 'command:...' --evidence 'file:...' --json
```

If budget is near/exhausted, stop and hand off instead of forcing a partial answer.

## Execution modes

| Mode | Use | Policy |
|---|---|---|
| `script_first_no_agent` | deterministic cron/control-plane | prefer `no_agent=true`; script emits JSON |
| `tiny_summarizer` | script output needs human-readable summary | LLM only summarizes in 2-3 lines |
| `bounded_agent_tick` | local-brain task execution | claim one task; execute one slice; proof or handoff |
| `single_shot_capped` | small one-off | hard cap, no recursive fanout |
| `manual` | P0/high-risk/destructive/external side effect | human-triggered only |

## PUA-loop guardrail

When a loop approaches the cap:
- stop opening new directions at about 80% of effective budget;
- write a handoff artifact with completed gates, incomplete gates, artifact paths, and next bounded command;
- if a task is claimed, end with exactly one of release/retry/done;
- do not mark done without structured evidence;
- do not call a degraded multi-model advisory a full ratification.

## Resuming after a tool-call/iteration cap

When the user says to continue a task that stopped because of a tool-call limit or incomplete previous turn:

1. Load the governing skill(s) first, then recover the last concrete blocker with `session_search` using file names, failing assertions, and required outcomes from the handoff.
2. Inspect the live working tree before editing:
   ```bash
   git -C ~/.hermes status --short -- <target-files>
   git -C ~/.hermes diff --cached -- <target-files>
   git -C ~/.hermes diff -- <target-files>
   ```
   Do not assume previously mentioned files are still staged or unchanged.
3. Reproduce the blocker with the narrowest deterministic test before fixing. For task-pool/idle-runner bugs, add a regression fixture that creates the exact frontmatter/status shape (for example: `status: pending` with only `run_id` metadata plus another pending candidate).
4. Fix the source of truth mismatch, not just the visible output. If an orchestrator/list row can omit fields, either expose the field in the canonical row schema or make the detector merge from the persisted frontmatter before safety decisions.
5. Re-run the scoped verification bundle and `git diff --cached --check`; restage target files after any patch. Do not commit while the user/handoff says “blocker not clear” or “cannot commit”.

## Verification checklist

```bash
python3 -m py_compile ~/.hermes/scripts/iteration_budget_doctor.py ~/.hermes/scripts/brain_task_budget_tick.py ~/.hermes/scripts/test_iteration_budget_guard.py
python3 ~/.hermes/scripts/test_iteration_budget_guard.py -v
python3 ~/.hermes/scripts/iteration_budget_doctor.py --json
python3 ~/.hermes/scripts/brain_task_budget_tick.py --spent-tool-calls 50 --max-tool-calls 60 --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/skill-steward.py --graph-check --json
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search 'iteration-budget bounded-tick pua-loop' --limit 10
```

## Pitfalls

- Do not scan `.env`, `auth.json`, or session logs and then echo surrounding snippets. Path + counters are enough.
- `agent.max_turns` and `delegation.max_iterations` are separate budgets.
- Context compression solves token pressure, not iteration-loop saturation.
- Cron `last_status=ok` does not prove a long LLM loop was bounded; check whether the job is script-first/no-agent.
- A budget tick is a preparer, not an autonomous executor; merge into idle-runner only after claim/retry/proof gates are implemented.
