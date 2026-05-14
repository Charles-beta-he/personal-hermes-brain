---
name: obsidian
description: Use when you need guidance on read, search, and create notes in the Obsidian vault.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - note
    - taking
    - obsidian
    related_skills:
    - design
    - framework-audit
    - note-taking
    - theory-driven-evolution
---

# Obsidian Vault

## Overview


**Current canonical local brain:** `~/Documents/brain/` (override with `HERMES_BRAIN_VAULT` or `OBSIDIAN_VAULT_PATH` when needed).

Legacy/narrow-sync vault may still exist at `~/Documents/Obsidian Vault`, but do not treat it as canonical unless the user explicitly asks.

Note: Vault paths may contain spaces - always quote them.

### Current control plane

Use `brainctl.py` first; it keeps filesystem fallback available even when Obsidian is not installed/running:

```bash
python3 ~/.hermes/scripts/brainctl.py --json status
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "query" --limit 10
python3 ~/.hermes/scripts/brainctl.py --json evidence "query" --limit 10
python3 ~/.hermes/scripts/brainctl.py --json wal --tail 20
python3 ~/.hermes/scripts/brainctl.py --json sync
```

When writing self-check scripts around `brainctl.py --json search`, parse defensively: some versions/commands return a top-level JSON list of hits, while others return a dict with `results` or `hits`. Treat both as valid; do not assume `data.get(...)` exists.

Derived indexes live under `~/.hermes/memory/` and are rebuildable caches; `~/Documents/brain` remains the truth source.

### Official Obsidian CLI

Install Obsidian on macOS with Homebrew cask when missing:

```bash
brew install --cask obsidian
```

Current observed Homebrew behavior: installing the cask places `Obsidian.app` at `/Applications/Obsidian.app` and links the official CLI as:

```bash
/opt/homebrew/bin/obsidian -> /Applications/Obsidian.app/Contents/MacOS/obsidian-cli
```

Obsidian's official CLI is app-mediated. The binary can exist while runtime commands still fail with:

```text
Command line interface is not enabled. Please turn it on in Settings > General > Advanced.
```

If that happens, the app must be opened and the user/app setting toggled: Settings → About/General → Advanced → Command line interface. In the Chinese UI this is 设置 → 关于 → 高级 → 命令行界面 (description: 允许从命令行与 Obsidian 交互。). Success is shown by the toast `Successfully registered to PATH.` Until then, treat the CLI as installed but not runtime-enabled; fall back to Markdown filesystem operations and `brainctl.py`.

Session-specific details for local-brain CLI enablement, sync verification, `brainctl search --json` output-shape parsing, and the `sync-brain.py` substring-filter pitfall are captured in `references/local-brain-sync-and-cli.md`.

Safe default capabilities: read/create/append/search/backlinks/tags/properties/tasks/open. Do not expose destructive or executable operations (`delete`, `eval`, arbitrary `command`, plugin install/enable/disable) without explicit scope and whitelist.

### Setting the vault path

Quick (per-session):
```bash
export HERMES_BRAIN_VAULT="$HOME/Documents/brain"
export OBSIDIAN_VAULT_PATH="$HOME/Documents/brain"
```

Persistent (save to skill directory):
```bash
cat > ~/.hermes/skills/note-taking/obsidian/env.sh << 'EOF'
export HERMES_BRAIN_VAULT="$HOME/Documents/brain"
export OBSIDIAN_VAULT_PATH="$HOME/Documents/brain"
EOF
# source ~/.hermes/skills/note-taking/obsidian/env.sh
```

## When to Use

- You need guidance on read, search, and create notes in the Obsidian vault

## Read a note

```bash
VAULT="${HERMES_BRAIN_VAULT:-${OBSIDIAN_VAULT_PATH:-$HOME/Documents/brain}}"
cat "$VAULT/Note Name.md"
```

## List notes

```bash
VAULT="${HERMES_BRAIN_VAULT:-${OBSIDIAN_VAULT_PATH:-$HOME/Documents/brain}}"

# All notes
find "$VAULT" -name "*.md" -type f

# In a specific folder
ls "$VAULT/Subfolder/"
```

## Search

```bash
VAULT="${HERMES_BRAIN_VAULT:-${OBSIDIAN_VAULT_PATH:-$HOME/Documents/brain}}"

# By filename
find "$VAULT" -name "*.md" -iname "*keyword*"

# By content
grep -rli "keyword" "$VAULT" --include="*.md"
```

### brainctl search query pitfall

`brainctl.py --json search` can return zero hits for mixed Chinese+English multi-term queries even when the target notes exist, because the current FTS behavior may effectively over-constrain terms. If a verification self-check fails with 0 hits:

1. Retry with exact note titles/headings, e.g. `Agent技能树路由矩阵`.
2. Retry with frontmatter English concepts, e.g. `Project Workpad`, `frontend closure testing`.
3. Use separate queries for Chinese and English terms instead of one combined phrase.
4. Patch the verifier to use robust exact-title/frontmatter-keyword queries, and record the failed query plus fixed query in the proof log.

## Create a note

```bash
VAULT="${HERMES_BRAIN_VAULT:-${OBSIDIAN_VAULT_PATH:-$HOME/Documents/brain}}"
cat > "$VAULT/New Note.md" << 'ENDNOTE'
# Title

Content here.
ENDNOTE
```

## Append to a note

```bash
VAULT="${HERMES_BRAIN_VAULT:-${OBSIDIAN_VAULT_PATH:-$HOME/Documents/brain}}"
echo "
New content here." >> "$VAULT/Existing Note.md"
```

## Bidirectional Sync Workflow

For keeping Hermes notes and the canonical local brain in sync:

### Bidirectional sync (recommended)

```bash
python3 ~/.hermes/scripts/brainctl.py --json sync
# or directly:
python3 ~/.hermes/scripts/sync-brain.py
```

This mirrors `~/.hermes/notes/` ↔ `~/Documents/brain/` while keeping `~/Documents/brain` as the human-readable canonical vault and `~/.hermes/memory/index.sqlite` as a rebuildable derived index.

Before large or unfamiliar syncs, run status first and keep local git/snapshot evidence:
```bash
python3 ~/.hermes/scripts/brainctl.py --json status
python3 ~/.hermes/scripts/sync-brain.py --status
```
Treat sync output as an audit artifact; if there are unexpected pushed/pulled counts, inspect diffs before committing further local-brain changes.

Pitfall: the canonical sync script must skip only the pull-mirror subtree `~/.hermes/notes/brain/`, not every path containing the substring `brain`. If a valid Hermes note such as `...local-brain.md` does not appear under `~/Documents/brain/99-hermes-notes/` after sync, regression-test `~/.hermes/scripts/sync-brain.py` with `~/.hermes/scripts/test_sync_brain.py` and ensure the filter checks `src_path.relative_to(HERMES_NOTES).parts[0] == "brain"`.

When a task creates or changes the local-brain hierarchy, do not stop at a design note. Create a category-fill ledger and at least one concrete artifact in the affected layer folders, then `brainctl sync`, `brainctl reindex`, and `brainctl search` for both the ledger and any mirrored Hermes evolution note. Details: `references/local-brain-category-landing.md`.

When a theory/category folder exists but is empty or hollow (for example a `控制论基础` folder with no supporting notes), treat it as a local-brain content-governance gap. Fill it with a MOC, core concept cards, bibliography/evidence-boundary note, proof log, and search verification; see `references/local-brain-theory-folder-governance.md`. For deeper theory→Agent mapping details, load the `theory-driven-evolution` skill reference `references/local-brain-theory-foundation-fill.md`.

When iCloud moves or duplicates the canonical brain under a folder like `~/Documents/文稿 - charles的MacBook Pro/brain`, use `references/local-brain-icloud-documents-recovery.md`: restore `~/Documents/brain`, leave a compatibility symlink from the nested path, then run status/sync/reindex/audit before doing any broader Documents cleanup.

When the user asks to PUA-loop/audit/fill the whole local brain until no priority gaps remain, use the exhaustive proof gate in `references/local-brain-exhaustive-audit.md`: scan empty dirs, top-level MOCs, hollow parents, broken wikilinks, and sensitive-pattern hits; only stop after sync/reindex/search proof and a scoped local commit when applicable. Current `local_brain_exhaustive_audit.py` emits JSON text by default but does not accept `--json`; call it without `--json` (optionally with `--sample-limit N`) and capture stdout as the audit artifact.

When evaluating or landing an external memory/RAG/retrieval/KG/agent-memory project into the local brain, use `references/external-memory-system-landing.md`: keep `~/Documents/brain` as canonical source of truth, treat vector/KG/cache systems as derived unless explicitly decided otherwise, create P10/P9/playbook/review/task/evolution/atom artifacts, add a local-first self-check script, record multi-model caveats honestly, then sync/reindex/search and make a scoped local commit.

When the user asks “how many key points are covered” or asks to “cover and supplement” a framework/protocol inside the local brain, use `references/local-brain-keypoint-coverage-audit.md`: distinguish keyword file hits from conceptual keypoint coverage, fill gaps with atoms/reviews/tasks/evolution logs, update MOCs, then sync/reindex/search and verify new-file wikilinks/secrets before committing scoped paths.

When the user asks whether to rewrite the Obsidian main hierarchy, whether to do a one-shot “一步到位” reorganization, or how to land theory/control-plane recommendations without disrupting the vault, use `references/local-brain-hierarchy-overlay-routing.md`: keep the main hierarchy stable, land semantic/control-plane overlays first, define reversible migration gates, verify bilingual search, and make only scoped commits.

When evaluating an external AI-memory/RAG/local-first memory repo for whether it helps the local-brain hierarchy, treat `~/Documents/brain` Markdown as canonical and any vector DB/palace/memory server as a derived index unless the user explicitly chooses otherwise. Inspect current brain status/top-level MOCs before mapping the repo, and prefer selective extraction of ideas such as L0-L3 wake-up layers, evidence-vs-index separation, temporal facts, and cross-domain tunnels over auto-rewriting the Obsidian hierarchy. See `framework-audit` reference `references/local-brain-memory-repo-adoption.md` for the detailed audit checklist.

When evaluating an external tracker-driven agent runner or orchestration repo for local-brain pending-task planning, keep the vault as the task source of truth and treat boards/daemons/dashboards as derived. Prefer selectively extracting task lifecycle frontmatter, claim/lease, retry/backoff, reconciliation-before-dispatch, persistent workpad, task-tree/DAG decomposition, workflow contracts, host-side typed tool proxies, and non-canonical dashboard patterns. For user-facing “加入任务池” or task-flow closure questions, also apply the direct-add and closure-audit patterns in `references/local-brain-task-orchestration.md`: session-local todo is not visible in Obsidian, `brain_task_orchestrator.py add` + `dashboard --write` is the canonical path, and `dispatch-dry-run` is not autonomous closure.

When updating a project Workpad with test environments, test accounts, OTP/SMS debug channels, or other semi-sensitive QA facts, keep it project-scoped and method-first: store durable access method and verification workflow, not one-time values. Use `references/project-workpad-test-env-credentials.md` for the safe deposition pattern, including Railway backend log OTP retrieval and delayed log-emission pitfalls.

When the user asks to check session memory + project memory so a fresh session can understand a project, use `references/project-workpad-handoff-bootstrap.md`: maintain the three-layer pattern (global memory = stable pointers only, Workpad = full project context and scoped QA facts, repo `AGENTS.md` = non-sensitive boot pointer), add a `New Session Handoff / Boot Capsule`, then sync/reindex/search and run any Workpad self-check.

When macOS/iCloud moves the local brain under a duplicated folder such as `~/Documents/文稿 - charles的MacBook Pro/brain`, restore `~/Documents/brain` as canonical, leave a compatibility symlink at the duplicate path, avoid deleting/merging legacy vaults, and verify with brainctl sync/reindex/search/audit. When asked to organize only the Documents folder, use inventory + manifest + no-delete classification rules and move only low-risk loose files; see `references/icloud-documents-local-brain-recovery.md`.

### Legacy narrow sync

`sync-to-obsidian.py` and `obsidian-watch.py` still exist for the old/narrow `~/Documents/Obsidian Vault` workflow. Do not use them for canonical local-brain work unless the user explicitly asks for the legacy vault.

### Automation

Prefer a cronjob that runs the canonical brain sync:
```yaml
schedule: "0 */6 * * *"
prompt: "Run python3 ~/.hermes/scripts/brainctl.py --json sync, then python3 ~/.hermes/scripts/brainctl.py --json reindex. Always produce a non-empty final response."
```

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.

## Common Pitfalls

### System credential files are write-protected

The agent cannot write to protected system files under `~/.hermes/`. If environment persistence is needed, use `env.sh` in the skill directory instead:
```bash
cat > ~/.hermes/skills/note-taking/obsidian/env.sh << 'EOF'
export HERMES_BRAIN_VAULT="$HOME/Documents/brain"
export OBSIDIAN_VAULT_PATH="$HOME/Documents/brain"
EOF
chmod +x ~/.hermes/skills/note-taking/obsidian/env.sh
# source ~/.hermes/skills/note-taking/obsidian/env.sh
```
1. Skipping prerequisite checks and assuming the environment already matches the workflow.
2. Applying the workflow mechanically without confirming that the request still matches this skill's trigger class.
3. Reporting success before reading back the actual outputs, files, or external side-effects.
## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

