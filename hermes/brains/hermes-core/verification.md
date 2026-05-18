# Hermes Core Verification v0.1.0

Minimum checks for private repo / multi-brain asset changes:

```bash
git -C ~/.hermes/hermes-agent status --short --branch
git -C ~/Code/personal-hermes-brain status --short --branch
python3 -m py_compile ~/.hermes/scripts/post-update-check.py
python3 ~/.hermes/scripts/post-update-check.py
```

For taskpool/multimodel WIP:

```bash
python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/brain_task_dispatch_tick.py ~/.hermes/scripts/consult_models.py
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
```

If P10 is required:

```bash
python3 ~/.hermes/scripts/pua_loop_self_optimize.py p10-check   --goal "..."   --boundary "..."   --evidence "..."   --next-action "..."
```
