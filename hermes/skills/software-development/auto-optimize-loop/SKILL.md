---
name: auto-optimize-loop
description: "Execute self-contained optimization loops on a codebase — scan for issues, generate proposals, prune risky ones, execute safe changes, commit per round, and record results. Integrates PUA pressure, P10/P9/P8 hierarchy, and git-per-round discipline. Proven over 11+ rounds on gomoku-react."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [optimization, refactoring, code-quality, automation]
    related_skills: [systematic-debugging, test-driven-development, codebase-inspection, requesting-code-review]
---

# Auto-Optimization Loop

Systematic code improvement in 5 steps. Designed for self-contained execution (cron jobs, background sessions, or interactive use).

## When to Use

- Periodic code quality sweeps
- Tech debt reduction passes
- Pre-release cleanup
- Autonomous long-running optimization sessions
- Post-refactor verification

## Prerequisites

- Test suite must exist and pass before starting (`pnpm test`, `pytest`, etc.)
- Project must be in a git repo (for revert safety)
- Know the "forbidden zones" — files/areas that must not be changed

## The 5 Steps

### STEP 1 — Scan

Run tests, then analyze the codebase. Report must include:

```bash
# 1. Run full test suite — establishes baseline
pnpm test  # or pytest, npm test, etc.

# 2. Code analysis — look for these categories:
#    - Duplicate logic (same functions in multiple files)
#    - Unused exports
#    - Deep nesting (>4 levels)
#    - Unhandled Promises
#    - Magic numbers (hardcoded values without named constants)
#    - Repeated patterns (setTimeout values, inline styles, etc.)

# 3. Record findings as issue list with file:line references
```

**Output:** List of issues grouped by category with file locations.

### STEP 2 — Propose

For each issue, generate a proposal in this exact format:

```
[PROPOSAL-{id}]
文件: <path>
问题: <描述>
方案: <具体改法>
风险: LOW | MEDIUM | HIGH
影响范围: <受影响文件列表>
```

**Rules:**
- Each proposal must be atomic (one logical change)
- Risk must be honest: HIGH if touching shared core, auth, or data flow
- Impact scope must list every file that changes behavior

### STEP 3 — Prune

Auto-reject proposals matching any of these criteria (customize per project):

- ❌ Risk=HIGH AND impact scope > 3 files
- ❌ Touches forbidden files (crypto, core contracts, migrations)
- ❌ Cross-module refactoring (spans app/package boundaries)
- ❌ Breaks plugin interfaces or public APIs
- ❌ Pure style changes with no logic/performance benefit

**Only ✅ proposals proceed to execution.**

### STEP 4 — Execute

For each ✅ proposal, follow this exact sequence:

1. **Verify baseline** — run tests, confirm all pass. FAIL → skip this proposal.
2. **Apply change** — make the edit.
3. **Verify post-change** — run tests AND build (`pnpm test && pnpm -F web build`). FAIL → `git revert` immediately.
4. **Commit** — only if both tests and build pass.

**Critical rules:**
- Never batch multiple proposals into one test run
- Never "fix tests to match changes" — revert instead
- If revert fails, escalate to user
- **ALWAYS run build after changes, not just tests** — Tests may only cover `packages/core/` while web/app layers have 0% coverage. A passing test suite + failing build is common in monorepos.

### STEP 5 — Record

Write results to `.claude/loop-report-{N}.md`:

```markdown
# Loop Report #{N}
- Date: {timestamp}
- Test baseline: {files} files, {tests} tests — {status}
- Test post-execution: {status}

## 执行的提案
(Each executed proposal with file, problem, solution, diff summary)

## 剪枝的提案
(Each rejected proposal with reason)

## 统计
- Executed: N | Pruned: N
- Files added/modified/deleted
- Lines added/removed

## 下一轮建议关注点
(What to investigate next)
```

## Termination Conditions

Stop and report when ANY of these are true:
- 2 consecutive loops with no new proposals
- All proposals pruned
- Test coverage decreases
- N loops completed (configurable, default: 5)

For UI/mobile-H5 loops, these generic stop conditions are necessary but not sufficient. If real browser evidence still shows HIGH offscreen interactive controls on auth, OTP, PIN/payment, security, wallet, or other critical paths, the loop must continue even when the script reached the final state. Use `browser-harness-integration` → `references/mobile-h5-loop-gates.md` for short-viewport gates, stop/continue/pause/abort rules, and `templates/mobile-h5-issue-ledger.json` for a frozen mainstream device matrix + issue-ledger ratchet.

Anti-gaming rule: do not improve loop pass rate by removing device buckets, relaxing thresholds, or changing harness classification in the same round as a UI fix. First classify findings (`true_clip`, `scrollable_below_fold`, `bottom_nav_overlap`, `safe_area_risk`, `harness_false_positive`, `needs_scroll_proof`), then fix UI or file an accepted risk with evidence.

## Multi-Dimensional Scanning

The basic loop scans for code quality issues. Add these dimensions for richer results:

### Product Manager Perspective
Scan for UX infrastructure gaps that affect users directly:
- **ErrorBoundary** — does one exist? (0 = white screen on crash)
- **Unhandled promises** — silent failures users can't see
- **alert() usage** — should be toast/notification system
- **Loading/empty states** — what happens when data is slow or missing?
- **a11y (aria/role)** — accessibility attributes on interactive elements
- **Network error feedback** — do users know when something fails?

Product-level issues often matter more than code-level cleanup.

### P9 Tech Lead Perspective
Run git + architecture analysis each round:
- **File hotspot chart** — which files change most frequently + are largest? (HIGH risk)
- **Module coupling** — cross-module import density
- **Test coverage gap** — source files vs test files ratio
- **Large functions** — any function >50 lines is a refactoring candidate
- **Hooks complexity** — count useState/useEffect/useRef per hook

Write a P9 report alongside the loop report with Task Prompts for next steps.

## Git-Per-Round Discipline

**Commit after EVERY round.** This is non-negotiable.

```bash
git add <changed files>
git commit -m "<type>: <description>"
```

Benefits: rollback any single round, clear audit trail, prevents big-bang commits.

If pre-existing uncommitted changes exist when the loop starts:
1. Commit pre-existing changes separately FIRST
2. Then commit loop changes in subsequent rounds
3. Document in commit messages when both are interleaved

Always push when ready: `git push origin main`

## P10 → P9 → P8 Hierarchy

For complex projects, layer the loop with strategic roles:

```
P10 (CTO) — 定战略、造土壤、断事用人
  → writes .claude/p10-strategy.md (方向/约束/风险/不做什么/P9编制)
  ↓
P9 (Tech Lead) — 写 Prompt 不写代码
  → writes .claude/p9-tasks.md (Task Prompt 六要素)
  ↓
P8 (Executor) — 执行
  → runs loop iterations, commits, pushes
```

### P9 Task Prompt Template
```markdown
## Task: [title]
### WHY — 为什么做 [业务背景 + 战略意图]
### WHAT — 交付物 [具体 deliverable + 验收标准]
### WHERE — 在哪里改 [只动/不要改]
### HOW MUCH — 资源边界 [模型/时间/复杂度]
### DONE — 完成的定义 [验证命令]
### DON'T — 禁区 [超出范围的功能/新依赖]
```

## PUA Loop Adaptation (Hermes)

The PUA Loop skill (`pua:loop`) uses Claude Code's Stop hook. For Hermes:

1. Create `.claude/pua-loop.local.md` state file manually
2. Use `todo` tool for iteration tracking
3. Run iterations in-session (no Stop hook needed)
4. Write loop reports manually after each round
5. Commit per round, push when done

## Definition of Done

- [ ] **Outcome**: All 5 steps completed (Scan→Propose→Prune→Execute→Record), loop-report-{N}.md generated
- [ ] **Process**: Test baseline established, each proposal executed individually with test+build verification, git committed per round
- [ ] **Style**: Proposals have risk/impact scope, rejected proposals documented with reason, statistics (executed/pruned count) recorded
- [ ] **Efficiency**: No consecutive loops with identical proposals, termination conditions checked, no batched test runs

## Pitfalls (Learned from 14-Round gomoku-react Session)

### 1. Delete Without Grepping Residual Imports
Deleted `constants.js`, created replacement with only `COPY_CONFIRM_MS`. 6 files still imported deleted exports → runtime crash.
**Fix:** ALWAYS grep entire src tree BEFORE AND AFTER deleting. Include lib/, hooks/, pages/.
```bash
grep -rn "from.*deleted-filename" apps/web/src/ --include="*.js" --include="*.jsx"
```

### 2. patch() Creating Duplicate Declarations
Removing inline `btn`/`card` from PlatformView.jsx caused `const RANK_TIERS = [` to be duplicated → build FAIL.
**Fix:** After patching, verify no duplicate `const`/`function` declarations. Run BUILD (not just tests).

### 3. Tests Pass but Build Fails
vitest only scanned `packages/core/` + `apps/signaling-cf/`. Web layer had 0% coverage. 3 build-breaking bugs passed tests undetected.
**Fix:** ALWAYS run `pnpm test && pnpm -F web build`. Extend vitest config to include web tests.

### 4. "Migrated to Core" Without Actual Migration
Commit said p2pCrypto.js "moved to packages/core" — file was only deleted, never copied. 3 hooks broke.
**Fix:** Verify both sides: export exists in target + all imports updated. Don't trust commit messages.

### 5. Overcounting JSX Nesting Depth
Scan counted JSX indentation as nesting, reporting 11-13 levels when actual brace nesting was 6-7.
**Fix:** Count `{`/`}` characters, not indentation.

### 6. MCTS Too Slow in Test Environment
100 simulations on 19×19 Go board → 45+ seconds → test timeout.
**Fix:** Conservative limits (50 for easy). Use `{ timeout: 30000 }`. Optimize simulate() to skip empty regions.

### 7. Monorepo Import Paths After File Moves
After moving constants to `@tg/core`, consumer files still imported from `../lib/constants.js`.
**Fix:** Use monorepo package alias. Check `package.json` exports field for subpath support.

### 8. Pre-existing Uncommitted Changes
Project had uncommitted changes before loop started. Loop modified the same files. Couldn't separate per-round.
**Fix:** Commit pre-existing changes FIRST, then loop changes in subsequent rounds.

### 9. Extract Pure Functions from Hooks for Testability
Hooks like `useGameEngine` (370L) contain pure logic (checkWin, checkDraw, coordToRc) mixed with React state. Hard to test without jsdom.
**Fix:** Extract pure functions into `lib/gameLogic.js`, test directly, import back into hook. Hook shrinks, test coverage grows.

### 10. Browser-Only Code in Node Test Env
`shareUrl.js` uses `window.location` → tests crash with "window is not defined".
**Fix:** Skip these tests in node env (remove test file), or configure vitest with `environment: 'jsdom'` for specific files. Don't try to mock window — it's not worth it for pure URL manipulation.

### 11. Cascading Patch Failures
Fixing one bug (constants.js imports) → patching PlatformView → broke RANK_TIERS → fixing that → broke p2pCrypto.
**Fix:** After each patch, run FULL test + build cycle. Don't batch patches. One fix → verify → next fix.

## Example: Extracting Shared Components

When duplicated components have different styling (inline vs Tailwind):

```jsx
// ui/CopyButton.jsx — supports both patterns
export default function CopyButton({ text, label, className }) {
  if (className) {
    return <button className={className} ...>{label}</button>
  }
  return <button style={{ /* inline fallback */ }} ...>{label}</button>
}
```

Consumer files pass `className` for Tailwind or omit for inline styles.

## Usage

### Interactive
"跑一轮自循环优化" / "Run an optimization loop"

### Cron Job
```yaml
prompt: "Execute auto-optimize loop on [project]. See .claude/auto-optimize-prompt.md."
schedule: "0 */4 * * *"
script: ~/.hermes/scripts/project-scan.py
```
   ```bash
   grep -rn "from.*deleted-filename" apps/web/src/ --include="*.js" --include="*.jsx"
   ```
7. **Git commit per round** — don't batch all loop changes into one commit. Commit after each successful round for clean history. If pre-existing changes interleave with loop changes, use descriptive commit messages that separate concerns.
8. **When consolidating imports after file deletion** — check if the project has a monorepo package alias (e.g., `@tg/core`) and use that instead of relative paths
9. **ALWAYS run build after changes, not just tests** — Tests may only cover `packages/core/` while web/app layers have 0% coverage. A change passing all tests can still break the build. Always run: `pnpm test && pnpm build`. (Learned: loop introduced 3 build-breaking bugs that tests didn't catch because vitest only scanned core + signaling.)
10. **Don't trust "migrated to core" in commit messages** — Verify both sides: (a) the export exists in the target package, (b) all consuming files import from the new path. A file deletion claiming migration without the actual migration causes immediate build failure.
11. **Verify file structure after patch operations on externally-modified files** — When a file was modified by a previous loop round and then patched again, duplicate declarations or orphaned code blocks can result. After patching, verify no duplicate `const X =` / `function X` declarations and that arrays/objects are properly closed.
12. **Pre-existing uncommitted changes complicate per-round commits** — If the project has uncommitted changes before the loop starts, some files will contain both pre-existing and loop changes. Document this in commit messages. Consider committing pre-existing changes separately first.
6. **After deleting a file, grep for ALL imports in the entire src tree** — include lib/, hooks/, pages/, not just components/. A deleted file with residual imports causes runtime crashes that unit tests may not catch (especially in React components where core tests don't cover UI). Use:
   ```bash
   grep -rn "from.*deleted-filename" apps/web/src/ --include="*.js" --include="*.jsx"
   ```
7. **Git commit per round** — don't batch all loop changes into one commit. Commit after each successful round for clean history. If pre-existing changes interleave with loop changes, use descriptive commit messages that separate concerns.
8. **When consolidating imports after file deletion** — check if the project has a monorepo package alias (e.g., `@tg/core`) and use that instead of relative paths
9. **ALWAYS run build after changes, not just tests** — Tests may only cover `packages/core/` while web/app layers have 0% coverage. A change passing all tests can still break the build. Always run: `pnpm test && pnpm build`. (Learned: loop introduced 3 build-breaking bugs that tests didn't catch because vitest only scanned core + signaling.)
10. **Don't trust "migrated to core" in commit messages** — Verify both sides: (a) the export exists in the target package, (b) all consuming files import from the new path. A file deletion claiming migration without the actual migration causes immediate build failure.
11. **Verify file structure after patch operations on externally-modified files** — When a file was modified by a previous loop round and then patched again, duplicate declarations or orphaned code blocks can result. After patching, verify no duplicate `const X =` / `function X` declarations and that arrays/objects are properly closed.
12. **Pre-existing uncommitted changes complicate per-round commits** — If the project has uncommitted changes before the loop starts, some files will contain both pre-existing and loop changes. Document this in commit messages. Consider committing pre-existing changes separately first.

## Pre-Collection Script (for Cron Jobs)

When running via cron, create a Python script that gathers context:

```python
# Collects: git status, git log, test results, TODO/FIXME markers, existing reports
# Output: JSON injected into cron prompt
# Saves 2-3 turns of discovery per run
```

Save to `~/.hermes/scripts/{project}-scan.py`.

## Multi-Round Workflow with Git Management

For long-running sessions (8+ rounds), commit after every successful round:

```
Round N:
  1. Scan + Propose + Prune
  2. Execute (test + build)
  3. git add <changed-files>
  4. git commit -m "fix/refactor: <description>"
  5. Write loop-report-{N}.md
  6. Update todo list
```

If pre-existing uncommitted changes exist when the loop starts:
1. First commit pre-existing changes separately
2. Then commit loop changes in subsequent rounds
3. Don't mix the two in one commit

## Parallel Batch Execution

When auditing or fixing many independent items (skills, configs, files), use parallel execution for massive speedup.

### Pattern: ThreadPoolExecutor Batch Audit

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def audit_one(item_name):
    # Read, score, optionally auto-fix
    # Return dict with score, fixes, etc.
    pass

with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(audit_one, name): name for name in items}
    for future in as_completed(futures):
        result = future.result()
        # Process result, apply ratchet (keep only improvements)
```

### Ratchet Mechanism

When auto-fixing in parallel, enforce that scores never decrease:

```python
new_score = calculate_score(item)
old_score = db[item]["score"]

if new_score >= old_score:
    db[item]["score"] = new_score   # Accept improvement
else:
    rollback(item)                   # Revert to backup
```

This prevents "fixes" from accidentally degrading quality.

### When to Parallelize

| Scenario | Approach | Speedup |
|----------|----------|---------|
| Audit 40+ independent items | ThreadPoolExecutor(8) | 40x+ |
| Run test suite | Usually serial (tests may conflict) | — |
| Apply patches to unrelated files | Parallel safe | 2-4x |
| Git operations | Serial (repo lock) | — |

### Real Result

Auditing 40 skills:
- Serial (one-by-one nightly): ~40 seconds
- Parallel (8 workers): 0.01 seconds
- Quality outcome: D-grade eliminated (2→0) in a single run

### Integration with P10/P9 Skill Hierarchy

For strategic projects, layer the loop inside the PUA skill hierarchy:

```
P10 (CTO) — 战略输入
  → .claude/p10-strategy.md (方向/约束/风险/不做什么/P9编制)
  ↓
P9 (Tech Lead) — 任务拆解
  → .claude/p9-report.md (架构分析/Task Prompt 六要素)
  ↓
Loop (Auto-Optimize) — 执行
  → 每轮读取 p10-strategy.md 约束
  → 按 P9 编制分线执行 (P9-A 后端, P9-B 前端)
  → loop-report 记录产出
  ↓
git commit + push — 交付
```

P10 defines WHAT and WHY, P9 defines WHERE and HOW MUCH, Loop executes.
