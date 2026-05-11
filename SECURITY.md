# Security Policy

This repository is private by default and must remain secret-free.

Never commit:

- `~/.hermes/.env`
- `~/.hermes/auth.json`
- `~/.hermes/auth/`
- OAuth tokens, provider API keys, cookies, credentials
- witness keys
- sessions, logs, caches, checkpoints, tick artifacts
- SQLite/DB derived indexes
- pid/lock files

Credentials are restored per-machine with Hermes setup, OAuth login, or a password manager. Git is only for portable behavior and knowledge.
