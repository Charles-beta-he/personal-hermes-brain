# Conflict policy

Canonical live source remains the local machine:
- brain: `~/Documents/brain`
- Hermes runtime: `~/.hermes`

This repo is a sanitized export/backup. Import is review-first but includes an automated
restore path for selected portable artifacts:
- `hermes/project-profiles/*.json` → `~/.hermes/project-profiles/`
- `hermes/scripts/*` → `~/.hermes/scripts/`
- `hermes/skills/*` → `~/.hermes/skills/`

Never blindly overwrite local runtime state outside this portable allowlist.
