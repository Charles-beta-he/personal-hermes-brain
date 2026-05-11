---
type: playbook
layer: L4
status: active
created: 2026-05-06T18:07:23+08:00
project: local-brain-mempalace-derived
---

# MemPalace 派生索引落地 Playbook

## Purpose

把 MemPalace 的检索架构转译为 Hermes-native 本地大脑实践。目标是增强召回和证据路由，不替换现有 Obsidian 层级。

## Safety contract

- Canonical vault: `/Users/charles/Documents/brain`。
- Never run `mempalace init` inside canonical vault。
- Any experiment must use an isolated sample and explicit `--palace` path。
- Default to `--no-llm`。
- If any external provider is proposed, stop and require explicit consent。

## Minimal isolated experiment

```bash
rm -rf /tmp/brain-sample /tmp/brain-palace
mkdir -p /tmp/brain-sample
# copy only non-sensitive sample markdown files manually or by allowlist
mempalace --palace /tmp/brain-palace init /tmp/brain-sample --no-llm --yes
mempalace --palace /tmp/brain-palace mine /tmp/brain-sample --mode projects
mempalace --palace /tmp/brain-palace search "技能生态 熵债 淘汰机制"
```

`--palace` is a global argument and must appear before the subcommand。

## Drawer / Closet rule

- Drawer = original evidence: `09-引用原文`, source excerpts, logs, raw notes。
- Closet = lossy index: `00-索引`, MOCs, short semantic pointers, dashboards。
- A Closet may summarize, route, and cluster；it must not become the fact source。
- Every derived claim needs a source pointer back to original evidence。

## Temporal facts convention

For mutable facts, record:

```yaml
subject: <entity>
predicate: <relationship>
object: <value>
valid_from: <date/time>
valid_to: <date/time or null>
confidence: <0-1 or qualitative>
source_file: <vault-relative path>
source_block: <heading/block if available>
```

Temporal facts are derived; Markdown source remains authoritative。

## PUA loop verification

每轮执行后：

```bash
python3 ~/.hermes/scripts/local_brain_mempalace_selfcheck.py --json
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "MemPalace派生索引 P10 source of truth" --limit 8
```

## Rollback

Rollback is simple because this landing only adds docs and a local-first verifier:

1. Remove or archive `05-实践与项目/projects/local-brain-mempalace-derived/`。
2. Remove this playbook and corresponding review/task/evolution notes。
3. Remove `~/.hermes/scripts/local_brain_mempalace_selfcheck.py` if no longer used。
4. Run `brainctl sync` and `brainctl reindex`。
