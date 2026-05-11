# Round 1 Proof — personal-hermes-brain

Created: 2026-05-11

## Scope

Round 1 lands a local private-repo-ready sync skeleton for reproducing Hermes personal assistant assets across machines.

## Memory upload policy

Raw Hermes persistent memory is not uploaded.

Excluded raw memory sources:

- `~/.hermes/memories/MEMORY.md`
- `~/.hermes/memories/USER.md`
- `~/.hermes/memory/`

Only `hermes/memory/README.md` is committed as policy documentation. Reviewed durable knowledge should be promoted to `brain/` Markdown notes. Portable behavior should be promoted to `hermes/skills/`.

## Implemented files

- `manifest.yaml`
- `.gitignore`
- `.gitattributes`
- `README.md`
- `SECURITY.md`
- `CONFLICT_POLICY.md`
- `bootstrap/sync_export.sh`
- `bootstrap/sync_import.sh`
- `bootstrap/bootstrap_machine.sh`
- `bootstrap/verify.sh`
- `bootstrap/validate_safe_tree.sh`
- `bootstrap/install_push_guard.sh`
- `bootstrap/rollback.sh`
- `docs/BOOTSTRAP.md`
- `docs/RESTORE_CREDENTIALS.md`
- `docs/SYNC_POLICY.md`
- `docs/MACHINE_ROLES.md`
- `hermes/memory/README.md`

## Deterministic verification observed

### Claim-to-evidence map

| Claim | Evidence | Status |
| --- | --- | --- |
| C-001 raw Hermes persistent memory is excluded | `manifest.yaml` memory policy, `hermes/memory/README.md`, `validate_safe_tree.sh` raw-memory path deny rules, observed repo memory file list | PASS |
| C-002 bootstrap/export/validation gates pass | `sync_export.sh` PASS, `validate_safe_tree.sh` PASS, `verify.sh` PASS, `brainctl reindex` PASS, `git diff --check` PASS | PASS |
| C-003 repo is ready for local commit but not remote push | no push performed, README states explicit push policy, `install_push_guard.sh` installs pre-push block unless `HERMES_ALLOW_PUSH=1` | PASS |

Commands executed locally:

```bash
cd /Users/charles/Code/personal-hermes-brain
bash bootstrap/sync_export.sh
bash bootstrap/validate_safe_tree.sh
bash bootstrap/verify.sh
git diff --check
python3 ~/.hermes/scripts/brainctl.py --json status
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search 'Hermes GitHub 个人助理同步方案' --limit 3
```

Observed results:

- `bootstrap/sync_export.sh`: PASS
- `bootstrap/validate_safe_tree.sh`: PASS
- `bootstrap/verify.sh`: PASS
- `git diff --check`: PASS
- repo tracked/exportable file count observed: 2881
- `brainctl status`: vault exists, index exists
- `brainctl reindex`: `indexed_blocks=2940`, `skipped_secret_blocks=54`
- `brainctl search`: found `06-治理与评审/reviews/2026-05-11-hermes-github-personal-assistant-sync-plan.md`
- memory file check under repo: only `hermes/memory/README.md` is intentionally present as raw-memory policy doc; raw runtime memory is absent.

Known non-blocking caveats from `hermes doctor`:

- xiaomi API key invalid in local `.env`
- optional provider/tool API keys missing
- these are local environment/provider issues, not repo bootstrap correctness blockers.

## Remote policy

GitHub private repo exists and is configured as `origin`:

- `https://github.com/Charles-beta-he/personal-hermes-brain`
- visibility: `PRIVATE`

No content push was performed. The local pre-push guard blocks push unless `HERMES_ALLOW_PUSH=1` is set after explicit user approval.
