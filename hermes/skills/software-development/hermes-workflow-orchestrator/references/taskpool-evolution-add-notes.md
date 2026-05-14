# Taskpool evolution add notes

Session-derived notes for adding self-optimization tasks into the Hermes taskpool.

Key observations
- `brain_task_orchestrator.py add` rejects `lane=evolution` tasks unless these architecture-alignment fields are present: `capability_delta`, `anti_drift_check`, `acceptance_evidence`.
- After successful creation, task files are written under `~/Documents/brain/05-实践与项目/tasks/` and derived views refresh automatically.
- `task_added` event hooks may return `ERROR` / `returncode=2` while the task itself is still created and `derived_refresh` reports success.

Recommended handling
1. For evolution/self-optimization tasks, always provide `--capability-delta`, `--anti-drift-check`, and `--acceptance-evidence` up front.
2. Verify success from the JSON result: `status`, `created`, and `derived_refresh` matter more than hook noise.
3. Read back `任务池-排序.md` or `list --json` to confirm queue position.
4. Treat event-hook failure as a secondary investigation unless `created` is missing or derived refresh failed.

Batching pattern
- External article / repo links can be converted into a sequence of similarly-scoped evolution tasks, one per source, using a consistent title/objective/acceptance template.
