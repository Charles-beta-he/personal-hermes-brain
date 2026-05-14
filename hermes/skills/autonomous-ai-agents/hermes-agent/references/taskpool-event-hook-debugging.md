# Taskpool event hook debugging and bounded automation

Use this reference when `brain_task_orchestrator.py add` succeeds but its `event_hook` reports `ERROR` / `returncode: 2`, especially for `task_added`.

## Diagnosis pattern

1. Inspect the newest hook log:
   ```bash
   python3 - <<'PY'
   import json, pathlib
   base=pathlib.Path('~/.hermes/state/taskpool_event_hooks').expanduser()
   p=max(base.glob('*.json'), key=lambda x:x.stat().st_mtime)
   j=json.loads(p.read_text())
   print(p)
   print('event',j.get('event'),'status',j.get('status'),'rc',j.get('returncode'))
   print('cmd',' '.join(j.get('cmd') or []))
   print('stderr', (j.get('stderr') or '')[-2000:])
   try:
       s=json.loads(j.get('stdout') or '{}')
       print('tick_status',s.get('status'),'errors',s.get('errors'),'error_count',s.get('error_count'))
       for k in ['multimodel_step','autorun','auto_close_review','post_autorun_dispatch']:
           v=s.get(k)
           print(k, v.get('status') if isinstance(v,dict) else None,
                 {kk:v.get(kk) for kk in ['reason','returncode','closed_count','skipped_count','error_count','task_id','to_status'] if isinstance(v,dict) and kk in v} if isinstance(v,dict) else '')
   except Exception as e:
       print('stdout_parse_error', e)
       print((j.get('stdout') or '')[:1000])
   PY
   ```
2. Treat `returncode: 2` as a structured tick failure, not necessarily add failure. Confirm whether the task was created and `derived_refresh` succeeded.
3. If stdout JSON shows `auto_close_review.status: ERROR` with empty stderr, inspect whether post-autorun auto-close is spawning nested multi-model certification inside an event hook.
4. If many old model processes are present, clear only the taskpool/model subprocesses before verification:
   ```bash
   pkill -f '/Users/charles/.hermes/scripts/brain_task_dispatch_tick.py' || true
   pkill -f '/Users/charles/.hermes/scripts/brain_task_orchestrator.py auto-close-review' || true
   pkill -f '/Users/charles/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention' || true
   pkill -f '/Users/charles/.hermes/scripts/consult_models.py' || true
   pkill -f 'Hermes Agent architecture planner' || true
   ```

## Durable fix pattern

Event hooks should be bounded by default. `task_added` should enqueue/refresh/dispatch quickly and should not spawn long-running multi-model discussions unless explicitly opted in.

Recommended semantics:

- `maybe_fire_taskpool_event_hook`: default command is `brain_task_dispatch_tick.py --summary --autorun-step --no-state --print-always`.
- Add `--multimodel-step` only when `HERMES_TASKPOOL_EVENT_HOOK_MULTIMODEL=1`.
- `dispatch_tick` may call post-autorun `auto-close-review`, but pass `HERMES_AUTO_CLOSE_REVIEW_TRIGGER_CERT=0` so it consumes existing certification only and does not spawn nested certification.
- Standalone/manual `auto-close-review` can keep `HERMES_AUTO_CLOSE_REVIEW_TRIGGER_CERT=1` by default to run the stronger certification loop.

This preserves automation without making every `task_added` hook a long-running multi-model job.

## Verification recipe

1. Compile and selfcheck:
   ```bash
   python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/brain_task_dispatch_tick.py
   python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
   ```
2. Add a low-risk verification task and inspect `event_hook`:
   ```bash
   python3 ~/.hermes/scripts/brain_task_orchestrator.py add \
     '测试 task_added event hook 不再 returncode 2' \
     --priority P3 --project hermes-agent --status pending --lane advisory \
     --concepts taskpool,event-hook,verification --json
   ```
   Expected: add `status: OK`, `event_hook.status: OK`, `event_hook.returncode: 0`, `derived_refresh.status: OK`.
3. Inspect the hook log. Expected tick fields: `status: OK`, `errors: None`, `auto_close_review.status: OK`, and `multimodel_step` absent unless explicitly opted in.
4. Archive the verification task afterwards with artifact evidence pointing to the hook log.
