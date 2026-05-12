---
name: post-update-patch-healing
description: "Create self-healing patches that survive `hermes update` (or any git-pull-based update). Covers the full controlled upgrade workflow: pre-upgrade conflict analysis, checker extension, stash/pull/pop with conflict resolution via subagent, and post-upgrade verification. Three-tier approach: Level 0 (user data, permanent) → Level 1 (standalone checker, update-safe) → Level 2 (vendor patches, updated-by-checker)."
---

# Post-Update Patch Healing

> **Problem**: `hermes update` runs `git pull` on the hermes-agent repo. Any local edits to `run_agent.py`, `cli.py`, `stream_consumer.py`, `chat_completions.py`, `types.py` etc. are **overwritten**.

> **Pattern**: Create a standalone script at `~/.hermes/scripts/` that detects known bug patterns in vendor files and re-applies fixes when needed. This script survives updates because it's outside the git repo.

## Three-Tier Architecture

```
Tier 0 — User Data (permanent, never overwritten)
  ├── ~/.hermes/memories/MEMORY.md        ghost entry cleanup
  ├── ~/.hermes/skills/                    skill files
  ├── ~/.hermes/scripts/                   custom scripts
  └── ~/.hermes/config.yaml                configuration
  
Tier 1 — Checker Script (update-safe, outside git)
  ├── ~/.hermes/scripts/post-update-check.py
  │   ├── Detects known bug patterns in vendor files
  │   ├── Re-applies patches with --fix mode
  │   └── Reports "already fixed by upstream" when applicable
  └── Auto-triggered by post-merge git hook
  
Tier 1.5 — Hermes Plugin (update-safe, native lifecycle hooks)
  ├── ~/.hermes/plugins/<name>/plugin.yaml      manifest
  ├── ~/.hermes/plugins/<name>/__init__.py       register() + hooks
  └── Survives update natively (outside git, loaded by Hermes at startup)

Tier 2 — Vendor Patches (overwritten by git pull)
  ├── run_agent.py                         step ordering fix
  ├── chat_completions.py                  truthiness fix
  └── stream_consumer.py / cli.py          think-tag state machine
```

> **Key insight from real usage**: Tier 1.5 (plugins) is strictly better than Tier 1+2 for most use cases. Prefer plugin hooks over vendor patches whenever possible.

## Git Post-Merge Hook Auto-Trigger

After `hermes update` (i.e., `git pull`), the post-merge hook auto-runs the checker:

```bash
# ~/.hermes/hermes-agent/.git/hooks/post-merge
#!/bin/sh
# Git post-merge receives one argument: 0 for a normal merge/fast-forward,
# 1 for a squash merge. It is NOT the string "merge"/"squash".
# For `hermes update`/`git pull`, run on normal post-merge events.
if [ "${1:-0}" != "0" ] && [ "${1:-0}" != "1" ]; then
    exit 0
fi
CHECKER="$HOME/.hermes/scripts/post-update-check.py"
if [ -f "$CHECKER" ]; then
    echo ""
    echo "⚕ Running post-update health check..."
    python3 "$CHECKER" --fix
    echo ""
fi
```

**Why this is safe**: `.git/hooks/` is not tracked by git — `git pull` never overwrites it. The hook survives updates indefinitely.

## Plugin Hooks Available for Self-Healing

Hermes exposes these hooks via `~/.hermes/plugins/<name>/`:

| Hook | Use Case | Example |
|------|----------|---------|
| `pre_tool_call` | Validate/skip tool calls before execution | Block dangerous file writes |
| `post_tool_call` | Observe tool results (observational only) | Skill usage tracking |
| `transform_tool_result` | Rewrite tool output before it enters context | Strip sensitive data |
| `pre_llm_call` | Inject context into user message before API call | Git branch info, timing data |
| `post_llm_call` | Observe final LLM response | WIP archive, logging |
| `pre_api_request` | Inject/modify API kwargs | Dynamic reasoning config |
| `on_session_start` | Initialize per-session state | Load tracking data |
| `on_session_end` | Flush/persist state | Write usage data to disk |

## How to Build a Post-Update Checker

### Step 1: Identify the 3 States

Every fix falls into one of these states after `git pull`:

| State | Meaning | Action |
|-------|---------|--------|
| **NEEDS_FIX** | Bug pattern present in vendor code | Apply patch |
| **OK** | Bug already fixed by upstream | Report "no action needed" |
| **UPSTREAM_CHANGED** | Upstream changed code in same area | Manual review needed |

### Step 2: Design the Check

Each check needs three things:

```python
# Pattern to detect (regex on file content)
needle = r'if reasoning_content:\s+provider_data\["reasoning_content"\]'

# Fix description (displayed to user)
fix_desc = "if reasoning_content: → if reasoning_content is not None:"

# Fix function
def fix_func(path):
    # Direct string replacement
    old = "if reasoning_content:"
    new = "if reasoning_content is not None:"
    with open(path) as f:
        content = f.read()
    if old in content:
        content = content.replace(old, new)
        with open(path, 'w') as f:
            f.write(content)
        return True
    return False
```

### Step 3: Use Comment Markers for Precise Detection

Vendor code changes frequently. Use **code comment headers** (not line numbers) to detect whether a fix is needed:

```python
# DETECTION: check for specific comment markers
has_bug_pattern = "# 2. DeepSeek / Kimi thinking mode: tool-call turns" in content
has_fix_pattern = "# 2. Healthy session: promote 'reasoning' field" in content

if has_bug_pattern:
    # Old (broken) order detected → apply swap
    apply_swap()
elif has_fix_pattern:
    # New (correct) order detected → skip
    pass
```

### Step 4: Structured Output

The checker should produce a machine-readable table:

```python
for name, status in results:
    icon = {"OK": "✅", "FIXED": "🔧", "NEEDS_FIX": "⚠️",
            "MANUAL": "👤", "DORMANT": "💤", "FIX_FAILED": "❌"}
    print(f"  {icon} {name}: {status}")
```

## Decision Framework: Plan A vs Plan B

Before patching vendor code, evaluate two approaches:

```
Plan A: Deep Fix (vendor code + post-update-check protection)
  ───────────────────────────────────────────────────────
  适合: 修复需要改核心逻辑，不容易从插件层实现
  方法: 直接改 hermes-agent/ 文件 + post-update-check 自动重打
  保护: post-merge git hook 自动运行 --fix
  风险: upstream 重构代码后 patch 可能冲突

Plan B: Zero Vendor Intrusion (plugin + config + skill only)
  ───────────────────────────────────────────────────────
  适合: 功能可以完全通过 hooks/config/SKILL.md 实现
  方法: ~/.hermes/plugins/<name>/ + config.yaml + skills/
  保护: 不需要 — 全部在 git repo 外
  风险: 部分修复是"弥补"而非"根治"

决策树:
  能否用插件 hook 实现？          → Yes → Plan B
  是否只需改 config/yaml？        → Yes → Plan B
  是否核心逻辑层 bug？            → Yes → Plan A
  修正后 upstream 可能合并吗？    → Yes → Plan A (+ 提 PR)
```

## Multi-Loop Convergence Pattern

When fixing multiple issues in one session, use an iterative convergence loop:

```
Iteration 1:  fix issue A  →  run checker  →  A OK, B discovered
Iteration 2:  fix issue B  →  run checker  →  A+B OK, C discovered
...
Iteration N:  fix issue N  →  run checker  →  ALL OK  →  DONE
```

**Convergence condition:** All checks report OK or explicitly time-dependent (💤/📦).

```python
# In practice, structure as:
todo_list = [
    "config changes (persistent)",
    "plugins (update-safe)",
    "vendor patches (post-update-check protected)",
    "skills + test-prompts",
]

while not all_done:
    pick_next_todo()
    execute_fix()
    run_self_check()
    if no_new_issues:
        mark_done()
    
# Stop when:
#   - All actionable items are OK or 💤/📦
#   - Remaining items are time-dependent (will self-resolve)
```

## Time-Dependent Metrics

Some checks can never report OK on day 1:

| Metric | Why | When it resolves |
|--------|-----|-----------------|
| Steward rule liveness (💤 DORMANT) | Rules need cron history | ~7 days of nightly runs |
| Skill usage tracking (📦 INSTALLED_NO_DATA_YET) | No data until next session restart | After 1+ agent session |
| Rule triggers (0 active) | No stale skills to flag yet | When a skill hits 90d without tests |

Label these explicitly so they don't block convergence:

```python
elif result.startswith("DORMANT"):
    print(f"    💤 {result}")
elif result.startswith("INSTALLED"):
    print(f"    📦 {result}")
```

## Cross-Session Detection Pattern

After converging a loop, always check if the **system itself** has blind spots:

```python
# After all existing checks pass, ask:
# 1. "Are there dimensions of quality my current checks miss?"
# 2. "Do I need a new check for something that happened during the fix?"
# 3. "Is the steward detecting everything the ecosystem needs?"
```

## Content Overlap False-Positive Mitigation

The content_overlap detector went through **two iterations** before producing useful results:

```
Iteration 1: Full body token overlap -> 253 false-positive pairs
             Root cause: common words dominate Jaccard
             Fix: added STOPWORDS set with ~80 English + Chinese words

Iteration 2: Description-only overlap -> 255 pairs (still false)
             Root cause: category stubs all have "X workflow skill" pattern
             Fix: skip skills with <200 body words (filters out stubs)

Iteration 3: Body words >200, STOPWORDS filtered -> 2 real pairs
             semantic-release vs cloudflare-pages (0.41)
             axolotl vs unsloth (0.39)
```

Key lesson: Start with strict filters. Only loosen if real overlaps are missed. False negatives beat false positives.

## Multi-Agent Design for Complex Patches

When a patch grows beyond a single-location regex fix (e.g., touches 6+ locations across a file), the standard post-update-check auto-fix approach breaks down. Use this workflow instead:

### When to Use

- Patch touches 3+ locations in the same file
- Patch requires architectural decisions (not just bug fixes)
- Patch needs to interact with upstream's own changes (e.g., upstream added a lock, local added a timeout)

### Workflow

1. **Analyze**: Identify all affected locations and their current state
2. **Consult**: Delegate design to Claude Code with full context (current code, upstream changes, design constraints)
3. **Review**: Claude Code produces a design document with exact diffs, risk assessment, and PR template
4. **Implement**: Apply changes using patch tool or execute_code
5. **Verify**: Claude Code reviews the implementation against the design
6. **Test**: Run pytest with isolated HERMES_HOME

### Example: MCP _mcp_rpc_call Architecture

Problem: Upstream added `server._rpc_lock`, local patch added `asyncio.wait_for`. Combined they created double timeout, double circuit breaker bump, and lock starvation.

Solution: Claude Code designed a `_mcp_rpc_call` helper that centralizes lock + timeout. The outer `_run_on_mcp_loop` timeout became a safety net (inner + 30s) with `future.cancel()` on expiry. Applied to all 5 MCP operations for consistency.

Key design principle: **Inner timeout = primary (clear error, circuit breaker). Outer timeout = safety net (catastrophic failures only).**

### Patch Complexity Classification

| Complexity | Auto-fix? | Approach |
|-----------|-----------|----------|
| 1 location, simple string replace | YES | post-update-check regex |
| 2-3 locations, pattern-based | MAYBE | post-update-check with careful regex |
| 4+ locations, architectural | NO | Separate apply script + checker detects absence |
| Cross-file, design decisions | NO | Multi-agent design → implement → verify |

For "NO" auto-fix: checker detects the OLD state (bare `await server.session.xxx`) and reports NEEDS_FIX. User re-applies from backup or runs a dedicated script.

## Pitfalls (General)

1. **Don't use line numbers**: Line numbers change every time the file is edited. Use unique comment strings or code patterns.

2. **Don't use complex indentation parsing**: Multi-line expressions (e.g. `needs_empty_reasoning = (\n    source_msg.get(...)`) are fragile. Use exact string replacement of the full block instead.

2b. **Don't use regex for multi-line indentation changes**: `re.sub()` with patterns spanning `async with X:\n    result = await ...` breaks indentation when the `async with` line is removed but the inner line retains its extra indent. The correct approach is **line-by-line processing**: scan for the lock line, skip it, and dedent the next line by the exact amount (typically 4 spaces). This was the root cause of 3 failed attempts in the 2026-05-12 MCP patch session — regex approach broke syntax, restore from backup, then line-by-line succeeded on first try.

3. **Auto-fix must be opt-in**: Default to dry-run. Require `--fix` flag to apply changes.

4. **Report upstream fixes**: When upstream has already fixed something, say "no longer needed" explicitly.

5. **Standalone script, not plugin**: Put the checker at `~/.hermes/scripts/` (outside the git repo).

6. **Don't use truthiness checks in normalize_response**: `if reasoning_content:` silently drops empty strings `""`. Use `if reasoning_content is not None:` instead.

7. **Regex needle mismatch causes false OK**: Test each needle against a known-broken file copy. Verify the needle does NOT match after the fix is applied.

8. **Post-merge hook only runs on actual merges**: `git pull --rebase` won't trigger post-merge.

9. **Git hooks persist through updates**: `.git/hooks/` is not tracked by git. Post-merge hooks survive indefinitely.

10. **Use venv python for py_compile, not system python**: System `python3` may have different build flags or PATH issues. Always use `./venv/bin/python -m py_compile` (or `.venv/`). In the 2026-05-12 session, system python3 hit `SyntaxError: invalid syntax` on `match` statements (even though both reported 3.11), while venv python correctly showed the actual indentation error. Pattern: `cd ~/.hermes/hermes-agent && ./venv/bin/python -m py_compile tools/mcp_tool.py`.

11. **Always backup before patching**: `cp path/to/file path/to/file.bak.$(date +%Y%m%d%H%M%S)`. When a multi-location patch breaks syntax, restoring from backup is faster than trying to reverse individual edits. The 2026-05-12 session needed 3 restores from backup before finding the correct patching approach.

12. **Run MCP-specific tests after patching mcp_tool.py**: `./venv/bin/python -m pytest tests/tools/test_mcp_tool.py tests/tools/test_mcp_stability.py -x -q` — the 199-test suite covers all 5 RPC operations, timeout behavior, and interrupt handling. Two RuntimeWarning about unawaited coroutines in interrupt-test scenarios are expected (not regressions).

13. **Line-by-line processing template for indentation-sensitive patches**: When a patch removes a wrapping construct (like `async with X:`) and needs to dedent the inner line, use this pattern:
    ```python
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if stripped == "async with server._rpc_lock:" and i + 1 < len(lines):
            next_line = lines[i + 1]
            next_stripped = next_line.lstrip()
            if next_stripped.startswith("result = await server.session."):
                indent = line[:len(line) - len(stripped)]
                new_lines.append(indent + next_stripped)
                i += 2
                continue
        new_lines.append(line)
        i += 1
    content = '\n'.join(new_lines)
    ```

14. **Codex timeout hardening must cover both main and auxiliary paths**: If Codex/OAuth transport starts timing out, do not only increase a global timeout. Add provider/model-scoped circuit breaking, split HTTP timeouts, and close/evict poisoned cached clients on every timeout branch. The auxiliary foreground-deadline branch is easy to miss because it can set `timed_out=True` without raising the same exception path as API timeouts. See `references/codex-transport-hardening.md`.

15. **Certification manifest beats discussion optimism**: In multi-model verification after a self-update, a `discussion_result.json` approval is not sufficient if the manifest reports planner/fanout mismatch, parser failure, or `can_claim_complete_certification=false`. Report it as deterministic gates passing plus degraded/advisory model review; do not claim 4/4 certification.

## Plugin Example: Skill Usage Tracker

```yaml
# ~/.hermes/plugins/skill-tracker/plugin.yaml
name: skill-tracker
hooks:
  - post_tool_call
  - on_session_end
```

```python
# ~/.hermes/plugins/skill-tracker/__init__.py
import json, os, time
from pathlib import Path
USAGE_FILE = Path(os.path.expanduser("~/.hermes/skills/steward/skill_usage.json"))
def _on_post_tool_call(tool_name="", args=None, **kwargs):
    if tool_name == "skill_view" and args and args.get("name"):
        _record(args["name"])
def _on_session_end(**kwargs):
    _flush()
def register(ctx):
    ctx.register_hook("post_tool_call", _on_post_tool_call)
    ctx.register_hook("on_session_end", _on_session_end)
```

## Known Patches (as of Apr 2026)

| Fix | File | Status | Detection Pattern |
|-----|------|--------|-------------------|
| Truthiness for empty reasoning_content | `agent/transports/chat_completions.py` | **ACTIVE** — regresses after upstream refactors | `if reasoning_content:` before `provider_data["reasoning_content"]` |
| Step ordering in `_copy_reasoning_content_for_api` | `run_agent.py` | **UPSTREAM SUPERSEDED** — upstream refactored reasoning handling with cross-provider leak blocking (ee1a07f9), our old patch no longer needed | `# 2. DeepSeek / Kimi thinking mode` before `needs_empty_reasoning` |
| MemoryManager provider registration rollback | `agent/memory_manager.py` | **ACTIVE + CHECKER-COVERED** | `self._providers.append(provider)` followed by bare `for schema in provider.get_tool_schemas()` without try/except rollback |
| MCP RPC timeout guard (all operations) | `tools/mcp_tool.py` | **ACTIVE + FULLY INTEGRATED** | `_mcp_rpc_call(server, coro, timeout)` helper present — centralizes `server._rpc_lock` + timeout across all 5 MCP operations (call_tool, list/read resources, list/get prompts). Commit f0e69bd5d (2026-05-12). Post-update-check now detects OLD state and reports NEEDS_FIX. Re-apply via `~/.hermes/scripts/apply-mcp-timeout-patch.py` (line-by-line processing, not regex). 199 tests pass. |
| Codex transport hardening | `agent/codex_circuit_breaker.py`, `agent/auxiliary_client.py`, `run_agent.py`, `hermes_cli/timeouts.py` | **ACTIVE — SHOULD BE CHECKER-COVERED** | File-backed provider/model-scoped circuit breaker, split Codex HTTP timeouts (`connect=30/read=600/write=60/pool=60`), and cached-client close/evict on all timeout paths. Reapply via dedicated script/patch under `~/.hermes/scripts/` and integrate into `post-update-check.py`. See `references/codex-transport-hardening.md`. |
| Context compressor anti-ghost rules | `agent/context_compressor.py` | **ACTIVE + CHECKER-COVERED** | Compaction prompt without `CRITICAL — ANTI-GHOST RULES` (stale counters, "This session..." carry-forward) |
| Prompt builder ghost prevention | `agent/prompt_builder.py` | **ACTIVE + CHECKER-COVERED** | MEMORY_GUIDANCE without "Will this fact still be true in 10 sessions?" guard |

> **2026-05-12 upgrade (0.11.0 → 0.13.0)**: `hermes update` triggered `pip install` upgrading hermes-agent + 7 new deps. Post-update-check found 6 issues: 4 auto-fixed (--fix), 2 needed manual work. MCP RPC timeout guard FIX_FAILED (expected — 6-location patch). Manual re-apply: 3 failed attempts using regex-based `re.sub()` (broke indentation each time), restored from backup each time, finally succeeded with line-by-line processing approach. Key new pitfall: regex for multi-line indentation changes is fundamentally fragile — use line-by-line processing (see pitfall 2b). Also discovered: system python3 vs venv python behave differently on `match` statements — always use venv python for py_compile (pitfall 10). 199 MCP tests passed. All 9 post-update checks green. Commit f0e69bd5d.
>
> **2026-04-29 upgrade (198 commits)**: Pre-upgrade analysis identified 10 overlapping files. Extended checker with 4 new checks (memory_manager rollback, prompt_builder ghost, context_compressor anti-ghost, mcp rpc timeout guard). Post-merge hook fixed (was comparing `$1` to wrong strings). `git stash pop` had "would be overwritten" trap — resolved by restoring checker-modified files to HEAD before popping. `tools/mcp_tool.py` conflict resolved via multi-agent design: Claude Code designed `_mcp_rpc_call` helper architecture (lock + wait_for centralized, safety-net outer timeout with future.cancel), Hermes implemented all 12 changes, Claude Code verified. 182 MCP tests passed post-implementation. Key insight: complex patches (6+ locations) can't be auto-fixed by checker — use checker to detect absence, separate apply script or manual re-apply.
>
> **2026-04-27 upgrade (280 commits)**: truthiness regressed after upstream refactor, auto-fixed by post-update-check --fix. step_ordering superseded by upstream's better implementation (cross-provider reasoning leak blocking + unconditional DeepSeek/Kimi padding). 4 new patches added.
>
> **Critical lesson**: Patches marked "UPSTREAM FIXED" can REGRESS on the next upgrade. Always run post-update-check after every `hermes update`, even if patches were previously confirmed fixed. The post-merge hook handles this automatically.

## Controlled Upgrade Workflow

When upgrading with local vendor patches, follow this exact sequence. Skipping steps causes conflicts that are harder to resolve than the upgrade itself.

### Phase 0: Pre-Upgrade Analysis (before touching anything)

Use this both for deciding whether an update is worth doing and for preparing the actual update.

```bash
cd ~/.hermes/hermes-agent

# 1. Check how far behind/ahead
git fetch origin main --prune
git rev-list --left-right --count HEAD...origin/main
git describe --tags --always HEAD 2>/dev/null || true
git describe --tags --always origin/main 2>/dev/null || true

# 2. Summarize upstream value, not just count commits
git rev-list --count HEAD..origin/main
git diff --name-only HEAD..origin/main | wc -l
git diff --numstat HEAD..origin/main | awk '{a+=$1; d+=$2} END{printf("+%s -%s\n", a+0, d+0)}'
git log --first-parent --date=short --pretty=format:'%h%x09%ad%x09%s' HEAD..origin/main | sed -n '1,120p'
git show origin/main:RELEASE_v0.12.0.md 2>/dev/null | sed -n '1,220p' || true

# 3. Identify local modifications
git diff --stat                            # unstaged tracked changes
git diff --cached --stat                   # staged tracked changes
git ls-files --others --exclude-standard   # untracked custom files

# 4. Identify overlap: files changed both locally AND upstream
{ git diff --name-only HEAD; git diff --cached --name-only; git ls-files --others --exclude-standard; } | sort -u > /tmp/hermes-local-files.txt
git diff --name-only HEAD..origin/main | sort -u > /tmp/hermes-upstream-files.txt
comm -12 /tmp/hermes-local-files.txt /tmp/hermes-upstream-files.txt

# 5. Check whether untracked local files already exist upstream
while read -r f; do
  if git cat-file -e "origin/main:$f" 2>/dev/null; then echo "$f"; fi
done < <(git ls-files --others --exclude-standard)

# 6. Predict stash-pop/patch conflicts by simulating on a detached worktree
TMP=/tmp/hermes-upgrade-check-$$
PATCH=/tmp/hermes-local-tracked-$$.patch
git diff --binary HEAD > "$PATCH"
git worktree add --detach "$TMP" origin/main
(cd "$TMP" && git apply --3way --check "$PATCH")
git worktree remove --force "$TMP"
rm -f "$PATCH"
```

Interpretation:
- `git apply --3way --check` passing means the tracked patch will probably re-apply cleanly, but it does **not** prove behavior is correct. Still run `post-update-check.py`, py_compile, focused pytest, and `hermes doctor` after the update.
- Untracked files that do not exist in `origin/main` are not a path-collision risk, but they can still be forgotten if you stash or reset carelessly.
- If `HEAD...origin/main` reports `ahead > 0`, this is a private-fork state. Do **not** blindly follow the fast-forward-only path; choose merge/rebase strategy explicitly (see Phase 2).

### Phase 1: Pre-Upgrade Fixes

Before upgrading, ensure:

1. **Post-merge hook is correct** — Git post-merge `$1` is `0` (normal merge/fast-forward) or `1` (squash), NOT the strings `"merge"`/`"squash"`. Verify:
   ```bash
   cat .git/hooks/post-merge
   ```

2. **Checker covers all local patches** — Run `post-update-check.py` dry-run. If any local vendor patch is NOT in the checker, add it BEFORE upgrading. Otherwise the patch will be lost after upgrade with no auto-recovery.

3. **Clean working tree** — `git diff --check` should produce no output (no trailing whitespace, no conflict markers).

4. **Backup everything**:
   ```bash
   mkdir -p ~/.hermes/backups
   git diff --binary > ~/.hermes/backups/pre-upgrade-$(date +%Y%m%d-%H%M%S).patch
   cp .git/hooks/post-merge ~/.hermes/backups/
   cp ~/.hermes/scripts/post-update-check.py ~/.hermes/backups/
   ```

### Phase 2: Upgrade Execution

Choose the path based on ahead/behind state from Phase 0.

#### Path A — No private commits ahead (`ahead = 0`): fast-forward

```bash
cd ~/.hermes/hermes-agent

# 1. Stash ALL changes (tracked + untracked)
git stash push -u -m "pre-hermes-upgrade-$(date +%Y%m%d-%H%M%S)"

# 2. Pull (fast-forward preferred)
git pull --ff-only origin main
# ↑ This triggers post-merge hook → post-update-check.py --fix automatically
# The checker re-applies all vendor patches to the new upstream code

# 3. Verify checker results — look for FIXED/OK/NEEDS_FIX in output
```

#### Path B — Private fork has local commits ahead (`ahead > 0`): controlled merge

When the repo is `ahead N, behind M`, `git pull --ff-only` will fail by design. Treat upstream as an upgrade source and preserve private commits with an explicit merge (preferred for large upstream jumps) unless the user explicitly wants a rebase.

```bash
cd ~/.hermes/hermes-agent

# 0. Create restore points before changing history or working tree
git branch private-backup-before-upstream-$(date +%Y%m%d-%H%M%S)
git tag pre-upstream-update-$(date +%Y%m%d-%H%M%S)
mkdir -p ~/.hermes/backups
git diff --binary HEAD > ~/.hermes/backups/hermes-agent-local-tracked-before-update-$(date +%Y%m%d-%H%M%S).patch
cp .git/hooks/post-merge ~/.hermes/backups/post-merge-before-update 2>/dev/null || true
cp ~/.hermes/scripts/post-update-check.py ~/.hermes/backups/post-update-check-before-update.py 2>/dev/null || true

# 1. Stash all dirty work, including untracked private files
git stash push -u -m "pre-upstream-update-private-patches-$(date +%Y%m%d-%H%M%S)"

# 2. Merge upstream explicitly (not ff-only, not implicit pull)
git fetch origin main --prune
git merge --no-ff origin/main -m "merge: sync from origin/main"
# post-merge hook may run post-update-check.py --fix here.

# 3. Reapply local dirty work
git stash pop
```

Alternative when untracked private modules are long-lived repo-level artifacts: commit them first in a clear private commit, then stash only tracked dirty patches before the merge. This reduces risk of losing untracked files but creates another local commit to carry forward.

```bash
git add <private-untracked-files>
git commit -m "feat(private): add private agent modules"
git stash push -m "pre-upstream-update-tracked-private-patches" -- <tracked-patch-files>
git merge --no-ff origin/main -m "merge: sync from origin/main"
git stash pop
```

### Phase 3: Stash Pop + Conflict Resolution

**Critical trap**: If post-update-check already applied patches to files that are also in the stash, `git stash pop` will fail with "Your local changes to the following files would be overwritten by merge". This happens because both the checker AND the stash modified the same files.

**Solution**: Restore checker-modified files to clean HEAD, then pop:

```bash
# For files where checker already applied the same patch as stash:
git checkout HEAD -- agent/context_compressor.py agent/memory_manager.py ...

# Then pop — only truly different changes will conflict
git stash pop
```

After pop, exactly ONE file may still conflict: files where upstream AND local patch changed the same region differently (e.g., `tools/mcp_tool.py` where upstream added `server._rpc_lock` and local patch added `asyncio.wait_for`).

**For mechanical conflicts** (both sides add independent features to the same function), delegate to Claude Code:

```bash
# From Hermes, delegate the conflict resolution
# Claude Code can read the conflict markers and produce the correct merge
```

**Resolution principle**: Keep BOTH sides' changes. In the mcp_tool example:
```python
async def _call():
    async with server._rpc_lock:       # ← upstream's addition
        try:
            result = await asyncio.wait_for(  # ← local patch
                server.session.call_tool(...),
                timeout=tool_timeout,
            )
        except asyncio.TimeoutError:   # ← local patch
            ...
```

### Phase 4: Verification

Run the verify script at `~/.hermes/scripts/hermes-pre-update-verify.sh`:

```bash
~/.hermes/scripts/hermes-pre-update-verify.sh
```

This checks:
- `git diff --check` (no trailing whitespace)
- `post-update-check.py` dry-run (all patches applied)
- `py_compile` on all patched runtime files
- `pytest` with isolated `HERMES_HOME` (temp directory, avoids polluting real state)

Then verify the CLI itself:
```bash
hermes --version
hermes doctor
```

### Phase 5: Cleanup

```bash
git stash drop   # only after verification passes
```

### Verify Script Template

Create at `~/.hermes/scripts/hermes-pre-update-verify.sh`:

```bash
#!/bin/sh
set -eu
REPO="${HERMES_REPO:-$HOME/.hermes/hermes-agent}"
CHECKER="$HOME/.hermes/scripts/post-update-check.py"
if [ -x "$REPO/venv/bin/python" ]; then PY="$REPO/venv/bin/python"
elif [ -x "$REPO/.venv/bin/python" ]; then PY="$REPO/.venv/bin/python"
else PY="$(command -v python3)"; fi

cd "$REPO"
echo "== git diff --check =="; git diff --check
echo "== post-update-check dry run =="; python3 "$CHECKER"
echo "== py_compile patched files =="
"$PY" -m py_compile agent/context_compressor.py agent/memory_manager.py \
  agent/prompt_builder.py agent/transports/chat_completions.py cli.py \
  hermes_cli/commands.py run_agent.py tools/mcp_tool.py tools/skill_manager_tool.py
echo "== isolated pytest =="
TMP_HOME="$(mktemp -d)"; trap 'rm -rf "$TMP_HOME"' EXIT
HERMES_HOME="$TMP_HOME" "$PY" -m pytest tests/test_model_health.py \
  tests/test_task_classifier.py -q -o 'addopts='
echo "== OK =="
```

### Pitfalls

1. **Stash pop fails with "would be overwritten"**: Checker already modified those files. Restore them to HEAD first, then pop. See Phase 3.

2. **Post-merge hook doesn't run**: Hook compares `$1` to wrong values. Fix: compare to `0`/`1`, or just always run checker unconditionally.

3. **Checker misses a patch**: After upgrade, a local patch silently vanishes. Always verify checker coverage BEFORE upgrading. If a patch isn't covered, add it to the checker first.

4. **Tests fail with stale state**: `model_health` and other stateful tests read `~/.hermes/rate_limits/` and other real paths. Always use temp `HERMES_HOME` for isolated testing.

6. **`hermes --version` shows "behind" after upgrade**: The version string in `pyproject.toml` may not be bumped yet even though code is at origin/main HEAD. Check `git rev-list HEAD..origin/main | wc -l` (should be 0) to confirm you're current. If git says `HEAD..origin/main=0` but `hermes --version` still reports old behind count, clear the cached update result (`rm -f ~/.hermes/.update_check`) and rerun `hermes --version`; the update checker caches results for ~6h. Note: running `hermes --version` can itself fetch/update `origin/main`; re-check `git rev-list --left-right --count HEAD...origin/main` afterward before declaring the upgrade current.

7. **TUI tests need generated hermes-ink dist first**: In `ui-tui`, a direct `npm test` can fail with `Cannot find module './dist/entry-exports.js'` from `packages/hermes-ink/index.js`. Build the package first, then rerun tests:
   ```bash
   cd ~/.hermes/hermes-agent/ui-tui
   npm run build --prefix packages/hermes-ink
   npm test
   ```
   A Python traceback during the slash-parity helper on systems whose default `python` is too old may be reported while Vitest exits 0 and skips those parity checks; treat non-zero Vitest exit as blocking, and record skipped parity separately if present.

8. **Config version outdated after large upstream jump**: Run `hermes doctor --fix` after code validation, with a backup of `~/.hermes/config.yaml` first. This migrates `config_version` and seeds new defaults (for example curator/auxiliary config) without touching secrets. Re-run `hermes doctor` afterward and distinguish real blockers from optional missing provider keys.

8. **Upstream timeout is silent**: In MCP tools, upstream's `_run_on_mcp_loop` timeout returns `None` on expiry, which gets misreported as success. The local `asyncio.wait_for` patch provides correct error reporting + circuit breaker bump. Keep it even though upstream has "timeout handling".

7. **MCP conflict resolution is always mechanical**: When upstream adds `server._rpc_lock` and local adds `asyncio.wait_for`, combine them (lock outside, wait_for inside). Never choose one or the other.

## Known Patches (as of Apr 2026)

- `systematic-debugging` — general debugging methodology
- `skill-ecosystem-diagnosis` — five hard problems diagnosis
- `skill-ecosystem-governance` — steward governance system
- `mcp/native-mcp` — MCP transport handling
- `claude-code` — delegating complex conflict resolution and architectural design
