# Hermes Memory Sync Policy

Raw Hermes persistent memory is intentionally not synchronized through this repository.

Do not commit:

- `~/.hermes/memories/MEMORY.md`
- `~/.hermes/memories/USER.md`
- `~/.hermes/memory/`
- SQLite indexes, WAL files, witness keys, session recall databases

Reason: raw memory contains durable personal profile, project conventions, local paths, operational strategy, and sometimes sensitive environment details. A GitHub private repo is still not the right boundary for raw assistant memory.

Portable knowledge should be promoted into `brain/` as reviewed Markdown notes. Portable behavior should be promoted into `hermes/skills/` as skills. A new machine should rebuild runtime memory locally from normal use, plus any manually reviewed non-sensitive notes from `brain/`.

If a future migration requires memory portability, use an encrypted export outside Git or a manually reviewed `memory.seed.example.md` with only non-sensitive preferences.
