# Private repo sync for a Hermes personal assistant

Use this when the user wants to reproduce/sync a personal Hermes setup through GitHub or another private Git remote.

## Core policy

Do not commit or push the whole `~/.hermes` directory.

Sync portable source-of-truth assets only:

- `~/Documents/brain` or the user's canonical brain vault as Markdown knowledge.
- `~/.hermes/skills` source files, excluding hub/cache/runtime state.
- selected deterministic `~/.hermes/scripts` files.
- sanitized config templates such as `config.example.yaml` and `env.example`.
- a policy note like `hermes/memory/README.md` explaining raw memory is local-only.

Never sync raw persistent memory:

- `~/.hermes/memories/MEMORY.md`
- `~/.hermes/memories/USER.md`
- `~/.hermes/memory/`
- SQLite indexes, WAL files, witness keys, sessions, logs, caches, checkpoints, tick artifacts, auth files, OAuth files, `.env`, or API keys.

Reason: raw memory contains personal profile, local paths, operational strategy, project facts, and potentially sensitive environment details. A private GitHub repo is not the right security boundary for raw assistant memory. Durable knowledge should be promoted into reviewed brain notes; portable behavior should be promoted into skills.

## Recommended repo shape

```text
personal-hermes-brain/
  README.md
  SECURITY.md
  CONFLICT_POLICY.md
  manifest.yaml
  .gitignore
  .gitattributes
  brain/
  hermes/
    skills/
    scripts/
    config/
    memory/README.md
  bootstrap/
    sync_export.sh
    sync_import.sh
    bootstrap_machine.sh
    verify.sh
    validate_safe_tree.sh
    install_push_guard.sh
    rollback.sh
  docs/
    BOOTSTRAP.md
    RESTORE_CREDENTIALS.md
    SYNC_POLICY.md
    MACHINE_ROLES.md
    ROUND*_PROOF.md
```

## Mechanical guards

`validate_safe_tree.sh` should fail closed on:

- `.env`, auth, OAuth, token/key/secret paths
- sessions/logs/cache/checkpoints/tick/state-snapshots/rate_limits/sandboxes/tmp
- sqlite/db/wal/shm/pid/lock/pyc/runtime files
- raw Hermes memory paths, allowing only `hermes/memory/README.md` if present
- token-looking content (`sk-*`, `gh*_`, `xox*`, `AIza*`, etc.) while allowing placeholder examples

Add an installable local pre-push hook:

```bash
if [ "${HERMES_ALLOW_PUSH:-}" != "1" ]; then
  echo "Push blocked. Run validation and set HERMES_ALLOW_PUSH=1 only after explicit approval." >&2
  exit 1
fi
bash bootstrap/validate_safe_tree.sh
```

Default policy: local commit is OK; do not push unless explicitly approved.

User-specific override pattern: if the user explicitly authorizes ongoing remote backup for Hermes itself / the personal assistant, treat that as approval for a guarded backup cadence, not as permission to push raw `~/.hermes`. Keep the fail-closed safe-tree validator and pre-push hook. Prefer a dedicated sanitized backup repo/worktree with an allowlist export, then push only after validation passes. Business/project repos remain separate and should still follow their own default push policy.

Recommended guarded cadence after explicit authorization:

- Commit sanitized evolution/source artifacts locally after meaningful self-improvement work.
- Push the sanitized backup repo on a regular cadence (for example daily or after verified evolution batches), provided `validate_safe_tree.sh` and `verify.sh` pass.
- Do not connect the live `~/.hermes` repo directly to a remote until `.env`, `auth.json`, raw memory, sessions, state DBs, tick outputs, caches, screenshots, checkpoints, and logs are excluded by construction and by validation.

## Export automation pattern

For a recurring private backup, create a sanitized export script rather than pointing Git at live `~/.hermes`.

Recommended script behavior:

1. Clean/rebuild a dedicated repo/worktree while preserving `.git`.
2. Copy only allowlisted text artifacts from the brain vault, skills, and selected deterministic scripts.
3. Deny by path, suffix, and secret-like content; skip rather than redact questionable source files.
4. Write repo policy files (`README.md`, `SECURITY.md`, `CONFLICT_POLICY.md`, `manifest.yaml`) and bootstrap scripts (`validate_safe_tree.sh`, `verify.sh`, `install_push_guard.sh`).
5. Install a pre-push hook that requires both safe-tree validation and `HERMES_ALLOW_PUSH=1`.
6. Run `brainctl sync`/`reindex`, export, validate, verify, commit, then push only after the guard passes.
7. In no-change cases, keep cron output silent; on changes/errors, emit compact JSON and append JSONL logs.

This preserves the user's ongoing backup cadence without turning private GitHub into a raw secret/memory store.

## Verification loop

Before declaring complete, run:

```bash
bash bootstrap/sync_export.sh
bash bootstrap/validate_safe_tree.sh
bash bootstrap/verify.sh
git diff --check
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search '<proof title>' --limit 3
git status --short --branch
git log --oneline -1
```

If a GitHub private remote is created but content must not be pushed, verify:

```bash
gh repo view <owner>/<repo> --json nameWithOwner,visibility,url
git remote -v
git ls-remote --heads origin | wc -l   # should be 0 before first approved push
```

If SSH host-key verification blocks `git ls-remote`, switch the remote to HTTPS for verification when `gh` is authenticated:

```bash
git remote set-url origin https://github.com/<owner>/<repo>.git
git ls-remote --heads origin
```

## Multi-model certification pattern

For evidence-first reviews, avoid monolithic evidence blobs. Create claim-linked evidence:

- C1: raw memory excluded → evidence from manifest, memory README, safe-tree deny rules, `find hermes/memory -type f`.
- C2: export/bootstrap/validation pass → evidence from command outputs.
- C3: no default push → evidence from no remote heads and installed pre-push hook.

If models complain about `needs_link_review` or evidence coverage 0.0, split evidence into `E-001`, `E-002`, `E-003` with explicit `supports: [C-...]`, rerun the review, then only claim grounded when evidence coverage is 1.0 and high-severity claims are verified.
