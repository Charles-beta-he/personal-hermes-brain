# Local-brain exhaustive audit and PUA-loop closure

Use when the user asks to inspect/fill the canonical local brain until no priority gaps remain, especially with phrases like `pua-loop`, `全部补齐`, `检查空白目录`, `直至无后续建议`, or `本地大脑穷尽补齐`.

## Canonical target

- Truth source: `~/Documents/brain`
- Use Obsidian for human browsing, but use `brainctl.py` and filesystem scans for proof.
- Do not rely on multi-model agreement as proof; treat it as review/provenance unless a truth gate certifies it.

## Stop gates

Only declare completion when all are true:

```json
{
  "empty_dirs": [],
  "top_level_no_index": [],
  "parent_no_direct_md_top": [],
  "broken_wikilinks_count": 0,
  "secret_pattern_hits": 0
}
```

Also require:

- `brainctl sync` has expected pushed/pulled counts.
- `brainctl reindex` succeeds and `skipped_secret_blocks` is checked.
- `brainctl search` hits the new proof/task/evolution notes and representative filled categories.
- If an over-constrained combined query returns no hits, retry with atomic queries for the key status words, project name, and artifact names before treating search as failed; record the successful atomic queries in the proof log.
- If the user’s request is Chinese or bilingual, verify both English/technical-token queries and Chinese queries. `brainctl` FTS tokenization can miss Chinese multi-term combinations unless the landed notes include compact Chinese search aliases/keywords such as `一阶控制论 二阶控制论 多模型介入 观察者` in the same block.
- Before final verification/commit for lifecycle-gated notes, search current task artifacts for stale state labels (for example `LOCAL_COMPLETE_UNRATIFIED`, `not_certified`, `FULLY_CERTIFIED`, `ratification_status`) and patch any section that still presents an old state as current while preserving it as historical provenance where appropriate.
- Proof notes/logs are updated with observed command outputs.
- Scoped local git commit is made when the repository is dirty; do not push unless explicitly asked.
- Do not embed the exact commit hash inside the same commit you are creating/amending: adding the hash changes the hash. Record repo/message/scope in the note and report the final hash in the final response, or write the hash only in a later follow-up commit if truly needed.

## Audit scan recipe

Prefer the maintained deterministic scanner when present:

```bash
python3 ~/.hermes/scripts/local_brain_exhaustive_audit.py
```

It scans `~/Documents/brain` (or `HERMES_BRAIN_VAULT`/`OBSIDIAN_VAULT_PATH`) while ignoring hidden/system directories such as `.obsidian`, and reports the exact stop-gate fields. If it is unavailable, use a script or Python one-liner that reports:

1. All non-hidden dirs under the vault.
2. Dirs with no files and no subdirs: `empty_dirs`.
3. Top-level dirs without a direct MOC/index note. For this vault, prefer Chinese `00-...索引.md` naming over generic `index.md` when matching existing style.
4. Top-level parent dirs with child markdown but no direct markdown: `parent_no_direct_md_top`.
5. Broken wikilinks: parse `[[target]]`, strip aliases after `|`, strip headings after `#`, and resolve against note basenames and relative paths.
6. Sensitive-pattern hits. Reword false-positive policy strings instead of normalizing noisy scanner output. Never write real secrets.

## Fill strategy

1. First fill structural P0 gaps:
   - Empty top-level dirs get `00-...索引.md` plus at least one concrete support note.
   - Hollow parent dirs get a direct MOC/index.
2. Then fill P1 governance scaffolding:
   - `30-tasks/` proof log with expiry.
   - `05-进化日志/` event note when the brain structure/content changes materially.
   - `60-reviews/` review/provenance note for multi-model or P10/P9 reasoning.
   - `00-system/` proof note for final audit artifacts.
3. Fix wikilinks after content fill. Prefer creating lightweight theory/source cards for meaningful old links; rewrite links only when the old target is clearly wrong.
4. Run sync/reindex/search again after writing final proof sections, because proof edits themselves change the index.
5. For bilingual/Chinese concepts, add a short keyword/alias block inside representative notes before the final reindex, then verify Chinese queries explicitly. This is a searchability aid, not a substitute for content.

## Backlog-zero governance loops

Use this extension when the local brain has explicit project/backlog notes and the user asks for `无 backlog`, `继续完成直至无backlog`, or similar. Do not merely mark TODOs closed; either implement the smallest verifiable local slice, archive it as a documented non-blocking accepted risk, or leave it open and say the loop is not complete.

Recommended pattern:

1. Search all backlog/project notes for open markers before editing:
   ```bash
   grep -RInE "Status：open|status: active|- \[ \]|P0 open|P1 open|P2 open" "$HOME/Documents/brain/05-实践与项目/projects" --include='*.md'
   ```
2. For governance-tool backlog items, prefer dry-run/local-first scripts plus tests over aspirational notes. Examples: `brainctl validate/expire/promote/review record`, evidence-request runner, stale-index/evidence gate, derived-index benchmark, claim/budget envelope wrapper.
3. Add or update proof artifacts in task/review/evolution locations with an explicit **Evidence Boundary**: model agreement, RRF ranking, vector/KG/derived indexes, and theory analogies are provenance or retrieval aids, not canonical truth.
4. For old review/theory notes that predate the boundary standard, add concise `Evidence Boundary` sections rather than rewriting the whole note.
5. Convert backlog checkboxes only after a corresponding executable proof exists or the item is explicitly moved to accepted-risk/non-blocking research. Add a small no-open-backlog register such as `open_backlog_count: 0` and `unchecked_checkboxes: 0` to the backlog note.
6. Re-run an active-backlog marker scan after closure. Do **not** treat generic frontmatter such as `status: active` on long-lived project/MOC/dashboard notes as backlog by itself; count explicit backlog/TODO markers such as `Status：open`, `P0 open`, `P1 open`, `P2 open`, `- [ ]`, `open_backlog_count: [1-9]`, or `unchecked_checkboxes: [1-9]`. A remaining explicit marker is a stop-gate failure unless it is inside a quoted historical example and documented as non-active. Example:
   ```bash
   python3 - <<'PY'
from pathlib import Path
import re, json
root = Path.home() / 'Documents/brain'
rx = re.compile(r'Status：open|P[0-2] open|- \[ \]|open_backlog_count:\s*[1-9]|unchecked_checkboxes:\s*[1-9]')
res = []
for base in [root/'05-实践与项目/projects', root/'05-实践与项目/tasks']:
    if not base.exists():
        continue
    for p in base.rglob('*.md'):
        for i, line in enumerate(p.read_text(errors='ignore').splitlines(), 1):
            if rx.search(line):
                res.append({'path': str(p.relative_to(root)), 'line': i, 'text': line[:220]})
print(json.dumps({'active_backlog_marker_count': len(res), 'samples': res[:80]}, ensure_ascii=False, indent=2))
PY
   ```
7. Before finalizing dashboard/backlog closure, scan for stale current-state labels and old “open” claims, but scope the strict backlog marker gate to project/task backlog locations. Broad whole-vault scans are useful for stale wording discovery, yet they can produce false positives from policy templates, negative phrases like “当前无 P0/P1 open”, or historical examples. Patch stale dashboard/review text that presents old states as current; do not treat quoted history, templates, or accepted-risk policy text as active backlog.
8. If tool-call/session limits interrupt before sync/reindex/audit/commit, do **not** claim `LOOP_DONE`; report the true state and resume from final verification next time.

## Mirror + scoped commit pitfalls

When the canonical vault is mirrored into `~/.hermes/notes/brain` for a local commit, do not assume `brainctl sync` and `git add notes/brain` are enough:

1. After editing `~/Documents/brain`, run `brainctl sync`, `brainctl reindex`, and the deterministic self-check/search gates.
2. Mirror the canonical vault explicitly before staging the repo mirror:
   ```bash
   cd ~/.hermes
   rsync -a --delete --exclude '.obsidian/' "$HOME/Documents/brain/" notes/brain/
   git add -A -- notes/brain <task-specific-scripts-or-ledgers>
   ```
3. Inspect `git status --short -- notes/brain scripts notes/evolution` rather than global status; this repo often contains unrelated runtime/cache/config/log churn.
4. If `git diff --cached --check` fails on whitespace inside files mirrored under `notes/brain/99-hermes-notes`, clean the source files under `~/.hermes/notes/` as well as the canonical vault. Those files can be re-pushed into the vault by `brainctl sync`, so cleaning only `~/Documents/brain` may not stick.
5. After whitespace/source-note cleanup, rerun `brainctl sync`, `brainctl reindex`, self-check/search gates, `rsync`, and restage. Then rerun `git diff --cached --check` and an added-lines secret scan before committing.
6. If new untracked `~/.hermes/notes/evolution/*.md` files appear during sync and are legitimate mirrored Hermes notes, either stage them with the same scoped commit or explicitly leave them out and report why; do not let them remain as unnoticed task residue.
7. In very dirty long-lived Hermes repos, a clean scoped status is enough for the local-brain closure even if global `git status` contains runtime/cache/config churn. Verify with explicit pathspecs, e.g. `git status --short -- notes/brain scripts/<task-script.py> ...`, and report unrelated global dirt as out of scope rather than staging it.
8. If `git diff --cached --check` reports `new blank line at EOF` after mirror/sync, trim trailing blank lines in **both** the canonical vault and `notes/brain` mirror, then restage with the same explicit pathspecs. Cleaning only one side can be undone by the next sync/rsync. If the blank line is generated by a script such as `brainctl validate --write-dashboard`, patch the generator to write `"\n".join(lines).rstrip() + "\n"` (or equivalent) before regenerating; otherwise the next validation run will reintroduce the whitespace failure.
9. For Python verification inside `~/.hermes`, prefer the Hermes venv `python` when available (`command -v python` may point at `~/.hermes/hermes-agent/venv/bin/python`). System `/usr/bin/python3` may not have `pytest`; fall back to `python -m unittest <tests...>` for stdlib-only test suites.
10. Dry-run budget/claim wrappers must receive the full envelope expected by `long_evolution_guard.check_budget`: `hop_count/max_hops`, `spent_tokens/max_tokens`, `spent_usd/max_usd`, `tool_calls/max_tool_calls`, and `elapsed_seconds/max_wall_seconds`. Minimal ad-hoc fields like `provider` or `max_cost_usd` will correctly fail as malformed budget evidence.
11. Current `brainctl validate`, `expire`, and `promote` are governance gates that report `dry_run: true` by design; `promote` currently has no non-dry-run side effect beyond WAL recording. Do not treat “running without `--dry-run`” as proof of a non-dry promotion. Use `review record` or explicit note edits for writable proof artifacts, then rerun sync/reindex/audit/search.

## Multi-model caveat

If multi-model discussion returns `not_certified`, `dissent`, times out, or has unresolved issues, say so plainly. It can justify a low-risk fill direction, but the completion claim must come from local audit, sync/reindex/search, and git evidence.

## Final response shape

Report concise evidence, not just a narrative:

- Final JSON audit summary.
- Key files created/changed.
- `brainctl sync` / `reindex` observed outputs.
- Search queries and hit categories.
- Local commit hash/message if committed.
- Caveat if multi-model result was not certified.
