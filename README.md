# personal-hermes-brain

Sanitized private backup/export for Charles' Hermes personal brain.

Generated: 2026-05-14T20:05:31Z

This repo intentionally contains portable knowledge and deterministic source artifacts only.
It does not contain raw Hermes memory, auth files, OAuth tokens, logs, caches, sessions,
SQLite indexes, checkpoints, `.env`, or runtime state.

Restore path:

1. Clone this private repo.
2. Read `docs/BOOTSTRAP.md` and `docs/SYNC_POLICY.md`.
3. Restore credentials manually from the local password manager, never from Git.
4. Run `bash bootstrap/verify.sh` before importing.
