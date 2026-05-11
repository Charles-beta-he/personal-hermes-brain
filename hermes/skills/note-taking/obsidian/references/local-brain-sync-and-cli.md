# Local Brain Sync + Obsidian CLI Session Notes

Use this reference when working on Hermes' canonical local brain at `~/Documents/brain` and Obsidian CLI integration.

## Observed Environment

- Canonical vault: `~/Documents/brain`
- Human UI: `/Applications/Obsidian.app`
- Observed Obsidian version: `1.12.7`
- Official CLI symlink observed via Homebrew cask: `/opt/homebrew/bin/obsidian -> /Applications/Obsidian.app/Contents/MacOS/obsidian-cli`
- Some shells may resolve `obsidian` via `/usr/local/bin/obsidian`; `brainctl` may still report `/opt/homebrew/bin/obsidian`.
- Hermes control plane:
  - `~/.hermes/scripts/brainctl.py`
  - `~/.hermes/scripts/sync-brain.py`
  - `~/.hermes/memory/index.sqlite`
  - `~/.hermes/memory/wal.jsonl`

## CLI Runtime Enablement

A present `obsidian` binary is not enough. Runtime may fail with:

```text
Command line interface is not enabled. Please turn it on in Settings > General > Advanced.
```

Enable in Obsidian UI:

- English UI: Settings -> About/General -> Advanced -> Command line interface
- Chinese UI observed: 设置 -> 关于 -> 高级 -> 命令行界面
- The successful toast is:

```text
Successfully registered to PATH.
```

After enabling, verify with:

```bash
command -v obsidian
obsidian --help
python3 ~/.hermes/scripts/brainctl.py --json status
```

## Canonical Sync Verification Loop

After creating or editing notes that should be visible in Obsidian:

```bash
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "distinctive phrase from the note" --limit 8
```

Expected signs:

- sync pushed/pulled counts match the change
- reindex reports a nonzero `indexed_blocks`
- search hits the expected vault path, often under `99-hermes-notes/` for Hermes note mirrors

## `brainctl search --json` output shape

When automating verification, parse `brainctl.py --json search` defensively. Depending on the command/version, stdout may be either:

```json
[{"path":"...","heading":"...","excerpt":"..."}]
```

or a dict-shaped response:

```json
{"results":[{"path":"..."}], "query":"..."}
```

Use logic equivalent to:

```python
data = json.loads(stdout)
if isinstance(data, list):
    hits = data
elif isinstance(data, dict):
    hits = data.get("results") or data.get("hits") or []
else:
    hits = []
```

Do not call `data.get(...)` before checking the top-level type; this caused a false self-check failure even though search had valid hits.

## Sync Filter Pitfall

The Hermes -> brain push path must skip only the pull-mirror subtree:

```text
~/.hermes/notes/brain/
```

Do not skip every path containing substring `brain`; that incorrectly drops valid notes such as:

```text
~/.hermes/notes/evolution/2026-05-06-symphony-obsidian-local-brain.md
```

Correct shape:

```python
try:
    rel_parts = src_path.relative_to(HERMES_NOTES).parts
except ValueError:
    rel_parts = src_path.parts
if rel_parts and rel_parts[0] == "brain":
    continue
```

Regression test when editing sync behavior:

```bash
python3 ~/.hermes/scripts/test_sync_brain.py -v
python3 -m py_compile ~/.hermes/scripts/sync-brain.py ~/.hermes/scripts/test_sync_brain.py
```

## Evolution/Event Logging Pattern

When a local-brain/Obsidian change is also a Hermes self-evolution event, create durable evidence in all relevant surfaces:

1. Evolution note under `~/.hermes/notes/evolution/`.
2. Append-only log in `~/.hermes/logs/evolve.log`.
3. JSONL event in `~/.hermes/notes/engineering-cybernetics/autonomous-evolution-log.jsonl`.
4. `brainctl sync` -> `brainctl reindex` -> `brainctl search` evidence showing the note is visible in `~/Documents/brain`.
5. Run `~/.hermes/scripts/verify-evolution-event.py` when applicable.

Do not store WIP/session-local state as long-term memory. Put durable procedures in skills and durable facts/designs in the vault.