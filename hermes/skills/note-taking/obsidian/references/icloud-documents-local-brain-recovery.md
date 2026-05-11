# iCloud Documents local-brain recovery and Documents-folder cleanup

Use this when the canonical local brain appears missing because macOS/iCloud has placed it under a duplicated folder such as `~/Documents/文稿 - charles的MacBook Pro/brain`, or when the user asks to organize only the macOS Documents folder after iCloud sync.

## Trigger symptoms

- `python3 ~/.hermes/scripts/brainctl.py --json status` reports `vault_exists: false` for `~/Documents/brain`.
- A brain-like vault is found under `~/Documents/文稿 - charles的MacBook Pro/brain`.
- The user asks to整理/organize “文稿文件夹内容” after iCloud sync.

## Recovery workflow

1. Inventory before touching anything:
   ```bash
   python3 - <<'PY'
   from pathlib import Path
   import time
   for base in [Path.home()/"Documents", Path.home()/"Library/Mobile Documents/com~apple~CloudDocs/Documents"]:
       print("BASE", base, "exists", base.exists(), "symlink", base.is_symlink())
       if base.exists():
           for p in sorted(base.iterdir(), key=lambda p:(not p.is_dir(), p.name.lower()))[:120]:
               st=p.stat(); print(('D' if p.is_dir() else 'F'), p.name, st.st_size, time.strftime('%Y-%m-%d %H:%M', time.localtime(st.st_mtime)))
   PY
   ```
2. Locate brain-like dirs by markers (`00-索引`, `01-系统与偏好`, `05-实践与项目`, `07-仪表盘`, `08-模板`).
3. If `~/Documents/brain` is absent and `~/Documents/文稿 - charles的MacBook Pro/brain` is the only real vault, move it back:
   ```bash
   mv "$HOME/Documents/文稿 - charles的MacBook Pro/brain" "$HOME/Documents/brain"
   ln -s ../brain "$HOME/Documents/文稿 - charles的MacBook Pro/brain"
   ```
4. Do not delete or automatically merge differing legacy vaults. Move conflicting duplicates to a review quarantine such as `~/Documents/_待整理_iCloud迁移/` and keep a symlink if compatibility matters.
5. Run verification:
   ```bash
   test -d "$HOME/Documents/brain"
   test -L "$HOME/Documents/文稿 - charles的MacBook Pro/brain"
   readlink "$HOME/Documents/文稿 - charles的MacBook Pro/brain"
   python3 ~/.hermes/scripts/brainctl.py --json status
   python3 ~/.hermes/scripts/brainctl.py --json sync
   python3 ~/.hermes/scripts/brainctl.py --json reindex
   python3 ~/.hermes/scripts/local_brain_exhaustive_audit.py
   ```

## Documents-folder cleanup rules

When organizing only `~/Documents`:

- Scope strictly to `~/Documents`; do not touch Desktop, Downloads, project folders, or other iCloud roots.
- Never delete files. Write an inventory JSON and apply manifest with `src`, `dst`, `size`, `mtime`, `sha256_before`, `sha256_after`, and `rollback_command`.
- Protect/no-move by default:
  - `brain`, `文稿 - charles的MacBook Pro`, `Codex`, `Obsidian Vault`, `_待整理_iCloud迁移`, `_整理日志`
  - app-generated dirs such as `TencentMeeting`, `com_tencent_imsdk_data`, `Dadroit JSON Generator`, `KiCad`, `log`, `Playgrounds`, `Untitled`
  - hidden/system files such as `.DS_Store`, `.localized`, dot dirs
- Low-risk loose drafts can move to `_分类整理/01-草稿与图表/`.
- Ambiguous app-generated loose files (`*.xml`, reports, `*.db`) should move only to `_分类整理/90-待复核-应用生成文件/`, not be renamed deeply, merged, or deleted.
- After moving, verify root loose non-hidden files are empty if that was the goal, and re-run brainctl/audit gates.

## Multi-model classification pattern

For cleanup rules with user data risk, package a small state with:

- inventory counts and file names,
- protected paths,
- no-delete/no-cross-folder constraints,
- claims linked to evidence.

A four-model fanout is enough for classification advice if deterministic local verification passes; do not call it full certification unless discussion/ratification artifacts exist.

## Artifacts to write

- `~/Documents/_整理日志/<date>-documents-inventory-before-classification.json`
- `~/Documents/_整理日志/<date>-documents-classification-apply-manifest.json`
- `~/Documents/_整理日志/<date>-documents-classification-report.md`
- local-brain review under `~/Documents/brain/06-治理与评审/reviews/` summarizing scope, rules, moves, verification, and rollback.
