# Sync policy

Export is allowlist/sanitized. Push only after validation passes.
Raw Hermes runtime state stays local-only.
Portable project profiles are exported so project-aware routing can be restored on another machine.
If checkout roots differ across machines, use `bootstrap/bootstrap_machine.sh --rewrite-prefix OLD=NEW` to rewrite profile path prefixes after import.
