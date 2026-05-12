# iCloud Documents safe organization on macOS

Use this when the user asks to organize `~/Documents`, especially after iCloud creates folders such as `文稿 - <Mac name>` or duplicates a local-brain/Obsidian vault.

## Principles

- Scope strictly to `~/Documents` unless the user explicitly includes Desktop/Downloads/iCloud root.
- Never delete first. Inventory -> classify -> move low-risk loose files -> verify. Delete only after explicit user approval.
- Preserve canonical workflow paths with symlinks when iCloud-created duplicate folders contain active content.
- Protect local-brain/Obsidian paths, app directories, hidden files, and legacy vaults until inspected.
- Always write manifests with source, destination, size, mtime, sha256, reason, and rollback notes.

## Discovery commands

```bash
python3 - <<'PY'
from pathlib import Path
import json, time
root = Path.home() / 'Documents'
protected = {'brain', '文稿 - charles的MacBook Pro', 'Codex', 'Obsidian Vault', '_整理日志', '_待整理_iCloud迁移'}
app_like = {'TencentMeeting', 'com_tencent_imsdk_data', 'log', 'KiCad', 'Dadroit JSON Generator', 'Playgrounds', 'Untitled'}
items = {'loose_files': [], 'protected_dirs': [], 'app_dirs': [], 'other_dirs': [], 'hidden': []}
for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
    rec = {'name': p.name, 'path': str(p), 'is_dir': p.is_dir(), 'is_symlink': p.is_symlink(), 'suffix': p.suffix.lower() if p.is_file() else '', 'size': p.lstat().st_size}
    if p.name.startswith('.') or p.name in {'.DS_Store', '.localized'}:
        items['hidden'].append(rec)
    elif p.is_dir() and p.name in protected:
        items['protected_dirs'].append(rec)
    elif p.is_dir() and p.name in app_like:
        items['app_dirs'].append(rec)
    elif p.is_dir():
        items['other_dirs'].append(rec)
    else:
        items['loose_files'].append(rec)
print(json.dumps(items, ensure_ascii=False, indent=2))
PY
```

## Classification rules

1. Protected/no-move:
   - `~/Documents/brain` canonical local brain.
   - iCloud compatibility folder such as `~/Documents/文稿 - charles的MacBook Pro` when it contains symlinks back to canonical folders.
   - `Codex`, legacy `Obsidian Vault`, `_整理日志`, `_待整理_iCloud迁移`.
   - app-generated directories and hidden/system files.
2. Low-risk loose user files:
   - unnamed `.md`, `.drawio`, screenshots, obvious drafts -> `~/Documents/_分类整理/01-草稿与图表/` or equivalent.
3. App-generated loose files:
   - tiny config XML, old report data, empty diagnostic DBs -> `~/Documents/_分类整理/90-待复核-应用生成文件/` first.
   - Audit content before deletion. If user approves deletion, write a delete manifest first.
4. Legacy vaults or non-empty duplicate folders:
   - Move to `_待整理_iCloud迁移/<name>` only when not canonical and not identical to root; keep a symlink from the old iCloud duplicate path when needed.

## Low-value review heuristics

A file is usually low-value if several of these hold:
- old mtime, tiny size, machine-generated name;
- content is only generic config such as `<config><log><Level>inf</Level></log></config>`;
- SQLite diagnostic DB has empty tables (`select count(*) = 0`);
- `file` reports opaque `data` and `strings` shows no meaningful user content;
- duplicate name exists only in the review folder and not in active app paths.

Delete only after explicit user approval. Before deleting, record sha256 and metadata in `~/Documents/_整理日志/*delete-manifest.json`.

## Verification

After organization:

```bash
# No unexpected top-level loose files
find ~/Documents -maxdepth 1 -type f ! -name '.*' -print

# Local brain safety, if applicable
test -d ~/Documents/brain
python3 ~/.hermes/scripts/brainctl.py --json status
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex

# Symlink compatibility, if applicable
readlink "$HOME/Documents/文稿 - charles的MacBook Pro/brain"
```

## Session-proven pattern

In one iCloud cleanup, the safe sequence was:
1. Restore `~/Documents/brain` from `~/Documents/文稿 - charles的MacBook Pro/brain` and leave the nested path as symlink `../brain`.
2. Move top-level loose files into `_分类整理`.
3. Review `90-待复核-应用生成文件`: delete `.DS_Store`, tiny XML configs, opaque old `ssoreport.txt`, and an empty SQLite `tim_database_quallity_report.db` only after user approval.
4. Keep manifests/reports under `~/Documents/_整理日志/`.
