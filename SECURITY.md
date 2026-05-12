# Security policy

Private GitHub is not treated as a secret store.

Forbidden in this repo:
- API keys, tokens, passwords, OAuth files, auth.json, `.env`
- raw `~/.hermes/memories/*`
- `~/.hermes/memory/*`, SQLite indexes, WAL files
- logs, caches, sessions, checkpoints, tick artifacts, state DBs

All pushes must pass `bootstrap/validate_safe_tree.sh`.
