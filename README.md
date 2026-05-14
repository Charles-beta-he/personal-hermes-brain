# personal-hermes-brain

Sanitized private backup/export for Charles' Hermes personal brain.

Generated: 2026-05-14T20:16:51Z

This repo intentionally contains portable knowledge and deterministic source artifacts only.
It does not contain raw Hermes memory, auth files, OAuth tokens, logs, caches, sessions,
SQLite indexes, checkpoints, `.env`, or runtime state.
It does include reviewed `hermes/project-profiles/*.json` plus selected control-plane scripts
so another machine can restore project-profile-aware task routing.

Restore path:

1. Clone this private repo.
2. Read `docs/BOOTSTRAP.md` and `docs/SYNC_POLICY.md`.
3. Restore credentials manually from the local password manager, never from Git.
4. Run `bash bootstrap/verify.sh` before importing.
5. Run `bash bootstrap/sync_import.sh` to restore scripts, skills, and project profiles into `~/.hermes`.
