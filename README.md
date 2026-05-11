# personal-hermes-brain

Private GitHub repo for reproducing Charles' Hermes personal assistant across machines.

This repo stores only portable source-of-truth assets:

- `brain/` — mirror of `~/Documents/brain` Markdown-first local brain.
- `hermes/skills/` — Hermes skills (`SKILL.md`, references, templates, scripts, assets).
- `hermes/scripts/` — selected user scripts from `~/.hermes/scripts`.
- `hermes/config/` — sanitized examples only.
- `bootstrap/` — import/export/validation scripts.

This repo MUST NOT contain secrets, OAuth tokens, runtime state, sessions, logs, caches, checkpoints, tick artifacts, or derived SQLite indexes.

Default workflow:

```bash
# Primary machine export
bash bootstrap/sync_export.sh
bash bootstrap/validate_safe_tree.sh
bash bootstrap/install_push_guard.sh
git status --short

# New machine import
bash bootstrap/bootstrap_machine.sh
bash bootstrap/verify.sh
```

Remote push policy: local commits are safe; pushing to GitHub is explicit and only after `validate_safe_tree.sh` passes.
