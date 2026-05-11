# Desktop safe organization on macOS/iCloud

Use when asked to整理桌面 / organize Desktop, especially when iCloud Desktop may contain cloud-only files.

## Safe default

1. Inventory first.
   - Scan `~/Desktop` top-level entries.
   - Separate loose files from directories.
   - Treat project/course/code directories as `keep in place` for the first pass.
   - Do not delete anything.

2. Classify loose files into dated organizer folders, e.g.:
   - `_桌面整理_YYYY-MM-DD/00_敏感_身份合同简历财务健康`
   - `_桌面整理_YYYY-MM-DD/01_安装包_可后续清理`
   - `_桌面整理_YYYY-MM-DD/02_技术学习资料`
   - `_桌面整理_YYYY-MM-DD/03_文档资料_待细分`
   - `_桌面整理_YYYY-MM-DD/04_图片截图二维码`
   - `_桌面整理_YYYY-MM-DD/05_视频会议录屏`
   - `_桌面整理_YYYY-MM-DD/06_压缩包_代码课程资料`
   - `_桌面整理_YYYY-MM-DD/07_零散代码脚本`
   - `_桌面整理_YYYY-MM-DD/08_其他_待确认`

3. Write artifacts under `~/Desktop/_整理日志/`:
   - classified inventory JSON
   - human-readable inventory/report Markdown
   - JSONL move manifest
   - rollback script

4. Move only top-level loose files.
   - Skip `.DS_Store`, `.localized`, organizer dirs, log dirs, symlinks, and all directories.
   - Use unique destination names to avoid overwrite.
   - Set sensitive review folder permissions to `0700`.

5. Verify after moving:
   - moved count equals manifest move records
   - every `dst` exists
   - no original `src` remains
   - remaining top-level loose files excluding system/log/organizer files is empty
   - sensitive folder mode is `0700`

## iCloud pitfall

Hashing every byte of `.dmg`, `.pkg`, `.zip`, videos, or cloud-only files can stall for minutes because iCloud may download files on read. Prefer this staged approach:

- For normal local files: full sha256 in manifest.
- For large files: quick fingerprint using first+last 1MB plus size.
- If a run stalls or cloud-only files are suspected: finish remaining same-volume moves with size+mtime metadata-only manifest, clearly label `fingerprint: metadata_only`, and keep rollback available.

Never let hashing failures turn a safe organization pass into deletion or destructive cleanup.

## Deep directory organization mode

Use this only when the user explicitly asks for deeper Desktop cleanup after the loose-file pass, or says to organize directories too.

Additional rules:

1. Preserve exclusions literally.
   - If the user excludes a folder, do not enter it, inventory its contents, move it, or alter its mtime/inode.
   - Record the excluded path in the inventory and verify `exists`, inode, and mtime after the run.

2. Preserve known workspaces in place.
   - Keep stable workspace roots such as `~/Desktop/folder` in place when memory or project conventions depend on subpaths.
   - If organizing inside a workspace, only move loose top-level files unless the user explicitly authorizes project moves.

3. Separate low-risk directories from path-sensitive code.
   - Course/learning/material folders can move into a dated deep organizer, e.g. `_桌面深度整理_YYYY-MM-DD/_学习课程`.
   - Sensitive certificate/health/domain folders move into `_敏感区` with mode `0700`.
   - Empty folders move into `_空目录`.
   - Code/project directories are path-sensitive. Before moving them, scan likely dependency roots (`~/.hermes/scripts`, `~/.hermes/skills`, `~/Documents/brain`, existing organizer logs) for hardcoded absolute and `~/Desktop/<name>` references. If hits are only historical inventory/logs, moving to `_代码项目_待评估` is acceptable with rollback; otherwise keep in place or create explicit compatibility symlinks after user confirmation.

4. Evidence-first verification for deep moves.
   - Write a separate inventory that states which folder contents were not entered.
   - Write a JSONL manifest and rollback script for every moved top-level directory.
   - Run rollback `--dry-run` before finalizing; require exit code 0 and expected line count.
   - Final verification should include remaining top-level items, unexpected items, organizer category counts, sensitive mode, excluded folder unchanged, and preserved workspace unchanged.

Recommended deep organizer layout:

```text
~/Desktop/_桌面深度整理_YYYY-MM-DD/
  _学习课程/
  _敏感区/        # chmod 700
  _空目录/
  _代码项目_待评估/
```

## Duplicate iCloud/Mac Desktop folder replacement mode

Use when the user later authorizes organizing a previously excluded duplicate Desktop folder such as `~/Desktop/桌面 - <Mac name>` and asks for one `work` folder to "delete"/"cover" another.

1. Treat destructive wording as reversible replacement unless the user explicitly confirms irreversible purge.
   - Never `rm -rf` user workspaces in the first pass.
   - Move the current canonical target (for example `~/Desktop/folder/work`) into a timestamped rollback quarantine under the dated organizer, e.g. `_桌面深度整理_YYYY-MM-DD/_rollback_quarantine/work-original-YYYYMMDD-HHMMSS`.
   - Then move or copy the duplicate source (for example `~/Desktop/桌面 - <Mac name>/folder/work`) into the canonical path.
   - This satisfies "source fully covers target" while preserving the old target for rollback.

2. Compare source/target top-level names before changing anything.
   - Record common names, target-only names, and source-only names.
   - Target-only names prove direct deletion would lose data; list them in the report as preserved in quarantine.
   - For code/work directories, run a bounded hardcoded path scan over likely dependency roots (`~/.hermes/scripts`, `~/.hermes/skills`, `~/Documents/brain`, organizer logs) before moving canonical paths.

3. Organize the duplicate root after extracting the source workspace.
   - Move residual duplicate-root content into an organizer bucket such as `_MacBook重复桌面_剩余/`.
   - Move loose docs into `_文档资料/` and reimbursement/health/credential folders into `_敏感区/` with mode `0700`.
   - Keep path/metadata reports only; do not summarize sensitive contents.

4. Verification must prove:
   - canonical target exists after replacement;
   - canonical target top-level names exactly match the duplicate source preflight names;
   - original target backup/quarantine exists;
   - rollback script dry-run exits 0;
   - sensitive bucket remains `0700`;
   - Desktop top-level no longer contains the duplicate folder if it was intentionally absorbed.

If multi-model consultation times out after only some planners return, report it honestly as partial multi-model advisory + deterministic verification, not full 4/4 certification.

## Rollback script behavior

Generate a rollback script that reads the manifest in reverse order and moves `dst -> src`.

Verification policy:
- full hash records: require full hash match
- quick fingerprint records: require quick fingerprint + size match
- metadata-only records: require destination exists and size matches

Default user flow:

```bash
python3 "$HOME/Desktop/_整理日志/rollback-desktop-YYYY-MM-DD.py" --dry-run
python3 "$HOME/Desktop/_整理日志/rollback-desktop-YYYY-MM-DD.py" --apply
```

## Sensitive classification signals

Conservatively route filenames containing these concepts into the sensitive review folder: 简历/resume, offer, employment contract/合同, 学历/学信网, 体检/报告, 发票/报销, wallet/钱包/Solana, personal names, certificates/keys/domain key material.

Do not summarize sensitive file contents in the final report; mention counts and paths only.
