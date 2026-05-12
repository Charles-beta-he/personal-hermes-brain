# Local brain recovery after iCloud Documents duplication

Use when `brainctl status` shows `vault_exists: false` for `~/Documents/brain` and inspection finds the vault under an iCloud-created folder such as `~/Documents/文稿 - charles的MacBook Pro/brain`.

## Safe recovery

1. Inventory before moving:

```bash
python3 ~/.hermes/scripts/brainctl.py --json status || true
find "$HOME/Documents" -maxdepth 3 -type d \( -name brain -o -name '文稿 - *' \) -print
```

2. If `~/Documents/brain` is missing and the nested `文稿 - .../brain` contains the canonical vault markers (`00-索引`, `01-系统与偏好`, `05-实践与项目`, `07-仪表盘`, `99-hermes-notes`), move it back:

```bash
mv "$HOME/Documents/文稿 - charles的MacBook Pro/brain" "$HOME/Documents/brain"
ln -s ../brain "$HOME/Documents/文稿 - charles的MacBook Pro/brain"
```

Adjust the Mac-specific folder name. Do not overwrite an existing `~/Documents/brain`; inspect/merge manually if both exist.

3. Validate:

```bash
test -d "$HOME/Documents/brain"
test -L "$HOME/Documents/文稿 - charles的MacBook Pro/brain"
readlink "$HOME/Documents/文稿 - charles的MacBook Pro/brain"
python3 ~/.hermes/scripts/brainctl.py --json status
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/local_brain_exhaustive_audit.py
```

4. Write a review note in the local brain and keep external manifests under `~/Documents/_整理日志/`.

## Pitfalls

- Do not treat `~/Documents/Obsidian Vault` as canonical if the active brain is `~/Documents/brain`.
- Do not delete the iCloud duplicate folder; leave compatibility symlinks when users or apps may still navigate there.
- Do not bulk-move app directories while restoring the brain. Separate brain recovery from general Documents cleanup.
- If a review note is added to the brain, run `brainctl sync`, `reindex`, and `search` to prove it is indexed.
