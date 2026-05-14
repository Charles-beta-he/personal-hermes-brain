# personal-hermes-brain

Sanitized private backup/export for Charles' Hermes personal brain.

Generated: 2026-05-14T20:39:40Z

This repo intentionally contains portable knowledge and deterministic source artifacts only.
It does not contain raw Hermes memory, auth files, OAuth tokens, logs, caches, sessions,
SQLite indexes, checkpoints, `.env`, or runtime state.
It does include reviewed `hermes/project-profiles/*.json` plus selected control-plane scripts
so another machine can restore project-profile-aware task routing.

Boundary:
- Portable control-plane capability is included: project profiles, selected scripts, and skills can be restored into `~/.hermes`.
- Machine-specific runtime state is still excluded.
- If the target machine uses different local checkout paths, some `project-profiles/*.json` `paths.*` entries may need local adjustment.

Restore path:

1. Clone this private repo.
2. Read `docs/BOOTSTRAP.md` and `docs/SYNC_POLICY.md`.
3. Restore credentials manually from the local password manager, never from Git.
4. Run `bash bootstrap/verify.sh` before importing.
5. Run `bash bootstrap/bootstrap_machine.sh` for one-click restore and validation.
   - Optional path rewrite: `bash bootstrap/bootstrap_machine.sh --rewrite-prefix /old/checkout=/new/checkout`
