# Sync Policy

- Use `sync_export.sh` on the primary machine.
- Use `sync_import.sh` or `bootstrap_machine.sh` on secondary machines.
- Run `validate_safe_tree.sh` before every commit and push.
- Do not auto-push from cron until the repo has several clean manual cycles.
