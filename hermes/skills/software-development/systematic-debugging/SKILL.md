---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior. 4-phase root cause investigation — NO fixes without understanding the problem first.
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation]
    related_skills: [writing-plans, test-driven-development]
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Someone wants it fixed NOW (systematic is faster than thrashing)

## The Four Phases

You MUST complete each phase before proceeding to the next.

---

## Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

### 1. Read Error Messages Carefully

- Don't skip past errors or warnings
- They often contain the exact solution
- Read stack traces completely
- Note line numbers, file paths, error codes

**Action:** Use `read_file` on the relevant source files. Use `search_files` to find the error string in the codebase.

### 2. Reproduce Consistently

- Can you trigger it reliably?
- What are the exact steps?
- Does it happen every time?
- If not reproducible → gather more data, don't guess

**Action:** Use the `terminal` tool to run the failing test or trigger the bug:

```bash
# Run specific failing test
pytest tests/test_module.py::test_name -v

# Run with verbose output
pytest tests/test_module.py -v --tb=long
```

**Java/Spring Boot startup pitfalls:**
- After deleting or renaming controller/classes, `mvn package` may leave old `.class` files under `target/classes` and the repackaged jar can still fail with the same ambiguous mapping or bean conflict even though source search shows zero references. If a Spring Boot app still reports a deleted controller/mapping after source cleanup, verify with `jar tf ... | grep DeletedClass` and run `mvn clean package` before concluding the fix failed.
- In multi-module Maven repos, `mvn -pl app/<module> spring-boot:run` can fail because sibling reactor artifacts are not installed. Run `mvn -pl app/<module> -am -DskipTests install` first, then start the app module.
- Do not exclude an infrastructure auto-configuration just to get a local backend up if production beans constructor-require it (for example excluding RocketMQ auto-config while a controller requires `RocketMQTemplate`). That converts real-backend verification into a partial harness; either start/provide the real dependency or make the bean conditional in a proper test profile.
- In React/Vitest suites, many unrelated text/label failures can come from a shared i18next singleton, not from the components themselves. Symptom: expected English labels but rendered DOM is Chinese (or another prior test language). Reproduce one failure and inspect the DOM language first. Fix the test harness by adding the required resource bundle in `beforeEach` with overwrite/deep merge and `await i18next.changeLanguage('<lang>')`; do not rely on `if (!i18next.isInitialized) init(...)` alone, because earlier tests may already have initialized the singleton.
- Spring `Ambiguous mapping` errors are backend startup-contract bugs. If a legacy compatibility controller duplicates a canonical controller endpoint, keep the canonical route, remove/rename the duplicate compatibility mapping, and add a startup/contract test.
- If Flyway/MySQL reports `UndeclaredThrowableException` or fails around `performance_schema.user_variables_by_thread`, inspect any JDBC `DataSource`/`Connection`/`Statement` dynamic-proxy instrumentation. `Method.invoke(...)` wraps thrown `SQLException` in `InvocationTargetException`; an `InvocationHandler` must unwrap and rethrow the original cause, otherwise Flyway cannot catch `SQLException` and degrade capability probes correctly. Add a unit regression that a proxied `PreparedStatement.executeQuery()` rethrows the original `SQLException`, not `UndeclaredThrowableException`.
- A `Tomcat started on port ...` log line is not a Spring Boot readiness proof. The app can still fail during `ApplicationReadyEvent` listeners or seeders and immediately shut down. Treat startup as ready only after `Started <Application>` appears, the process remains alive, and `/actuator/health` (plus target smoke endpoints) returns 200/UP. If a post-ready seeder reports `Table '<schema>.<table>' doesn't exist`, check Flyway enablement/profile/schema before debugging controllers.
- Conversely, `mvn spring-boot:run` for a long-lived server reports Maven `BUILD FAILURE` when the tracked process is intentionally stopped by SIGTERM (`exit code 143`). Do not classify that as app startup failure if logs show `Started <Application>`, the app stayed alive, smoke endpoints were hit while alive, and shutdown appears under `ShutdownHook`. Record it as a manual/test-harness termination, not a failed boot.

See `references/spring-boot-real-backend-startup.md` for a concrete real-backend startup debugging checklist and error examples.

### 3. Check Recent Changes

- What changed that could cause this?
- Git diff, recent commits
- New dependencies, config changes

**Action:**

```bash
# Recent commits
git log --oneline -10

# Uncommitted changes
git diff

# Changes in specific file
git log -p --follow src/problematic_file.py | head -100
```

### 4. Gather Evidence in Multi-Component Systems

**WHEN system has multiple components (API → service → database, CI → build → deploy):**

**BEFORE proposing fixes, add diagnostic instrumentation:**

For EACH component boundary:
- Log what data enters the component
- Log what data exits the component
- Verify environment/config propagation
- Check state at each layer

Run once to gather evidence showing WHERE it breaks.
THEN analyze evidence to identify the failing component.
THEN investigate that specific component.

### 5. Trace Data Flow

**WHEN error is deep in the call stack:**

- Where does the bad value originate?
- What called this function with the bad value?
- Keep tracing upstream until you find the source
- Fix at the source, not at the symptom

**Action:** Use `search_files` to trace references:

```python
# Find where the function is called
search_files("function_name(", path="src/", file_glob="*.py")

# Find where the variable is set
search_files("variable_name\\s*=", path="src/", file_glob="*.py")
```

### 6. Trace Data Through Pipeline Boundaries (Multi-Component Systems)

**WHEN the data flows through a normalization → persistence → reconstruction → API replay pipeline:**

This is a common pattern in LLM agent frameworks. Data enters the system in one shape, gets transformed, stored to DB, loaded, transformed again, and sent to an API. **Each boundary can silently drop fields.**

**Map the full pipeline before picking a fix:**

```
API response → normalize_response() → [NormalizedResponse object] → _build_assistant_message() → dict
  → append_message() → SQLite → get_messages_as_conversation() → dict
  → _copy_reasoning_content_for_api() → api_messages dict → transport.build_kwargs() → API call
```

At EACH boundary, verify:
- **Inbound**: what fields does the input have? (use `print(list(input.keys()))` or `dir()`)
- **Outbound**: what fields does the output have?
- **Loss**: did any field disappear? Was it intentionally stripped?
- **Transformation**: did any field change type or format?

**Action:** Read EVERY file in the pipeline chain, following each function call. Focus on:

1. **`getattr(obj, field, None)` vs `hasattr(obj, field)`**  
   - `hasattr` returns `True` for `@property` definitions even when the underlying data is missing
   - `getattr` returns the property's return value (which may be `None`)

2. **`if value:` vs `if value is not None:`**  
   - `if value:` uses truthiness: empty string `""`, `0`, `[]`, `False` all fail the check
   - `if value is not None:` preserves the value even when it's falsy  
   - This is the #1 cause of silent field loss at normalization boundaries

3. **Deep copy vs shallow copy** — `msg.copy()` (shallow) vs `copy.deepcopy(messages)` (deep). Nested dicts/lists in shallow copies share references with the original, so modifications to one affect the other — or vice versa when the same mutable object is reused.

4. **`if row["field"]:` vs `if row["field"] is not None:` in DB readback** — SQLite returns `""` for empty text fields and `None` for NULL. `if row["field"]:` treats both as falsy, silently dropping empty strings on round-trip.

5. **`msg.copy()` on dicts with complex nested objects** — Tool calls, function arguments, and provider_data all contain nested structures. A shallow copy means child objects are shared between source and destination — mutations in one path leak into the other. Use `copy.deepcopy` when the dict contains mutable children.

```python
# WRONG — shallow copy passes through None for missing keys
api_msg = msg.copy()
api_msg["reasoning_content"] = api_msg.get("reasoning_content")  # None if missing

# WRONG — truthiness check drops empty strings
if reasoning_content:
    provider_data["reasoning_content"] = reasoning_content

# RIGHT — explicit None check preserves empty strings
if reasoning_content is not None:
    provider_data["reasoning_content"] = reasoning_content
```

**Real example (DeepSeek reasoning_content loss, April 2026):**
```
Root cause: chat_completions.py:351 used `if reasoning_content:` instead of
`if reasoning_content is not None:`. Empty string `""` was silently dropped
from provider_data, never flowing into the stored msg dict.

Impact: DeepSeek's assistant messages lost reasoning_content on replay →
HTTP 400 on every turn after the first. Fallback retried with the same
broken schema → all retries failed → session never persisted.

Fix: One-line change — truthiness check → None check.
```

### 7. Cross-Reference With Upstream Repository

**WHEN working with a fork or open-source project that receives updates:**

BEFORE proposing a fix, check whether the bug is already known upstream. This avoids:
- Wasting time duplicating work
- Writing a fix that will be overwritten by `git pull` on next update
- Missing context from existing discussions (root cause analysis, edge cases, alternative approaches)

**Action:**

```bash
# Search GitHub issues with relevant keywords
open_browser -> https://github.com/<owner>/<repo>/issues?q=is%3Aissue+{keywords}
```

Sample keywords from common bug classes:
- `reasoning_content` + `400` — DeepSeek/Kimi thinking mode validation
- `think` + `stream` + `tag` — streaming reasoning tag display leaks
- `_clean_for_display` — gateway stream filtering
- `context_compressor` + `memory` — compression + memory interaction

**When you find a matching issue:**
- Note its status (Open/Closed/PR-linked)
- Check if a PR already exists with a fix
- Check if the fix has been merged — if so, `hermes update` will bring it
- If the fix is not yet merged, decide whether to patch locally or wait

### 8. Fix Sustainability Audit — Will This Survive `hermes update`?

**WHEN the fix touches files inside the hermes-agent repo (`~/.hermes/hermes-agent/`):**

Before writing any fix, map which files it affects against the update mechanism:

```
`hermes update` does git pull on ~/.hermes/hermes-agent/
→ Any file inside this directory WILL be overwritten on next update

Exempt files (NOT overwritten by update):
  ~/.hermes/config.yaml         — user config
  ~/.hermes/.env                — API keys
  ~/.hermes/memories/           — persistent memory
  ~/.hermes/skills/             — user skills
  ~/.hermes/scripts/            — user scripts
  ~/.hermes/cron/               — cron job data
```

**Three-layer fix strategy (ranked by sustainability):**

| Layer | Method | Survives update? | Effort |
|-------|--------|-----------------|--------|
| **User data** | Edit ~/.hermes/memories/MEMORY.md, config.yaml | ✅ Always | Low |
| **Monkey-patch** | Python runtime override at startup | ✅ Yes (inject from ~/.hermes/config.yaml or startup script) | Medium |
| **Vendor code** | Edit run_agent.py, cli.py, transport files in ~/.hermes/hermes-agent/ | ❌ Overwritten by git pull | Low (but ephemeral) |
| **PR upstream** | Submit fix to official repo, get merged | ✅ Once merged, future updates carry it | High |

**Prefer higher layers when possible. Document lower-layer fixes with git hooks.**

**For monkey-patching:**
```python
# Example: Patch ChatCompletionsTransport at startup
# Place in ~/.hermes/hermes-agent/hermes_cli/startup_patch.py
from agent.transports.chat_completions import ChatCompletionsTransport

_orig_normalize = ChatCompletionsTransport.normalize_response

def _patched_normalize(self, response, **kwargs):
    result = _orig_normalize(self, response, **kwargs)
    # Fix: preserve empty string reasoning_content
    if hasattr(response, 'choices') and response.choices:
        msg_rc = getattr(response.choices[0].message, 'reasoning_content', None)
        if msg_rc is not None:
            pd = result.provider_data or {}
            pd['reasoning_content'] = msg_rc
            object.__setattr__(result, 'provider_data', pd)
    return result

ChatCompletionsTransport.normalize_response = _patched_normalize
```

**For git hooks (auto-reapply patches after update):**
```bash
# ~/.hermes/hermes-agent/.git/hooks/post-merge
#!/bin/sh
# Auto-apply local patches after git pull
git diff --quiet HEAD -- agent/transports/chat_completions.py || exit 0
# Apply patch if not already present
cd "$(git rev-parse --show-toplevel)"
grep -q "is not None" agent/transports/chat_completions.py || \
  sed -i '' 's/if reasoning_content:/if reasoning_content is not None:/' \
    agent/transports/chat_completions.py
```

### 9. Ghost Memory Detection (Context-Compression-Aware)

**WHEN analyzing issues related to persistent memory and context compression:**

Past-tense entries in persistent memory survive context compression and get re-injected as current facts. This is a common source of confusion in agent systems.

**Check for ghosts in `~/.hermes/memories/MEMORY.md`:**

| Ghost Pattern | Example | Why It's Dangerous |
|--------------|---------|-------------------|
| **Past-tense completion summary** | "三轮审查修复10个问题，最终达到无改进状态" | Future sessions treat this as current state |
| **Version number** | "v1.4.8" | Becomes stale as project evolves |
| **Past progress** | "Discover 页面 + BottomNav 已上线" | Pages may have been modified/removed |
| **Redundant entries** | Same project described twice | Wastes limited memory budget (2,200 chars) |

**Detection heuristic:**
```python
# A memory entry is a ghost if it answers "Was this task COMPLETED?"
# rather than "Is this fact STILL TRUE?"
#
# Linguistic markers:
# - Past tense (完成/上线/修复了/was/implemented/done)
# - Completion quantifiers (三轮/10个/全部)
# - Version numbers (v1.4.x)
# - Session-local progress (not system architecture)
```

**Fix:**
- Remove ghost entries from MEMORY.md
- Keep only architecturally durable facts (project structure, tool conventions, user preferences)
- Duplicates → merge into single entry

### 10. Multi-Loop Convergence — Iterate Until No Issues Remain

**WHEN fixing multiple bugs in a single session:**

```
Fix → Re-check → Fix → Re-check → ... until 0 issues
```

Track progress with a structured todo list. Each loop iteration:
1. Fix the highest-priority remaining issue
2. Run the self-check
3. If new issues found, add them to the todo list
4. Stop when only time-dependent items remain

**Convergence signal:** All checks pass or are explicitly labeled as time-dependent.

### 11. Claim-Validation Audit — Verify System Weakness Claims Against Source Code

**WHEN presented with a list of system weaknesses or "known issues" (from documentation, issue reports, or analysis):**

BEFORE accepting any claim as true:
1. **Read the actual source code** — do not rely on documentation or reputation
2. **Categorize each claim** using a systematic framework:

```python
def audit_claim(claim, source_code):
    """
    Categories:
    ✅ TRUE:       Claim accurately describes a real weakness
    ⚠️ PARTIAL:    Claim is directionally correct but mitigations exist
    ❌ FALSE:      Claim is wrong — the code doesn't match the description
    """
```

3. **For each claim, produce evidence:**

```
| Claim: "MCP stdio lacks chunking → deadlock"
| Reading: mcp_tool.py:1053 async with stdio_client(...)
| Finding: ⚠️ PARTIAL — asyncio streams don't block, but large payloads 
|           can time out. 300s read timeout mitigates permanent deadlock.
| Verdict: Theory risk exists, but has timeout guardrails.
```

**Real example (Apr 2026 MCP 7-claim audit):**
```
Out of 7 claims:
  ✅ 4 real:     memory noise, error solidification, learning loop, OAuth no heartbeat
  ⚠️ 2 partial:  stdio blocking (has timeout), context overflow (has compression)
  ⚠️ 1 limited:  MemoryManager dirty instance (doesn't cause global deadlock)
```

**Why this matters:** Accepting false claims leads to unnecessary fixes that waste time and add complexity. Validating against source code is the only reliable way to separate real bugs from design tradeoffs.

### Phase 1 Completion Checklist

- [ ] Error messages fully read and understood
- [ ] Issue reproduced consistently
- [ ] Recent changes identified and reviewed
- [ ] Evidence gathered (logs, state, data flow)
- [ ] Problem isolated to specific component/code
- [ ] Root cause hypothesis formed
- [ ] Claim validated against source code (if third-party claim)
- [ ] Upstream repository cross-referenced (if related)

**STOP:** Do not proceed to Phase 2 until you understand WHY it's happening.

---

## Phase 2: Pattern Analysis

**Find the pattern before fixing:**

### 1. Find Working Examples

- Locate similar working code in the same codebase
- What works that's similar to what's broken?

**Action:** Use `search_files` to find comparable patterns:

```python
search_files("similar_pattern", path="src/", file_glob="*.py")
```

### 2. Compare Against References

- If implementing a pattern, read the reference implementation COMPLETELY
- Don't skim — read every line
- Understand the pattern fully before applying

### 3. Identify Differences

- What's different between working and broken?
- List every difference, however small
- Don't assume "that can't matter"

### 4. Understand Dependencies

- What other components does this need?
- What settings, config, environment?
- What assumptions does it make?

---

## Phase 3: Hypothesis and Testing

**Scientific method:**

### 1. Form a Single Hypothesis

- State clearly: "I think X is the root cause because Y"
- Write it down
- Be specific, not vague

### 2. Test Minimally (Isolation First for Destructive Tests)

- Make the SMALLEST possible change to test the hypothesis
- One variable at a time
- Don't fix multiple things at once

**For destructive tests (backup/restore, migrations, format conversions):**
- NEVER test on production data or active skill directories directly
- Copy the target to `/tmp` or a disposable workspace first
- Run the destructive operation against the copy
- Verify the outcome, then apply to the real target only after confirmation
- Clean up the temporary copy when done

### 3. Verify Before Continuing

- Did it work? → Phase 4
- Didn't work? → Form NEW hypothesis
- DON'T add more fixes on top

### 4. When You Don't Know

- Say "I don't understand X"
- Don't pretend to know
- Ask the user for help
- Research more

---

## Phase 4: Implementation

**Fix the root cause, not the symptom:**

### 1. Create Failing Test Case

- Simplest possible reproduction
- Automated test if possible
- MUST have before fixing
- Use the `test-driven-development` skill

### 2. Implement Single Fix

- Address the root cause identified
- ONE change at a time
- No "while I'm here" improvements
- No bundled refactoring

### 3. Verify Fix

```bash
# Run the specific regression test
pytest tests/test_module.py::test_regression -v

# Run full suite — no regressions
pytest tests/ -q
```

### 4. If Fix Doesn't Work — The Rule of Three

- **STOP.**
- Count: How many fixes have you tried?
- If < 3: Return to Phase 1, re-analyze with new information
- **If ≥ 3: STOP and question the architecture (step 5 below)**
- DON'T attempt Fix #4 without architectural discussion

### 5. If 3+ Fixes Failed: Question Architecture

**Pattern indicating an architectural problem:**
- Each fix reveals new shared state/coupling in a different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere

**STOP and question fundamentals:**
- Is this pattern fundamentally sound?
- Are we "sticking with it through sheer inertia"?
- Should we refactor the architecture vs. continue fixing symptoms?

**Discuss with the user before attempting more fixes.**

This is NOT a failed hypothesis — this is a wrong architecture.

---

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals a new problem in a different place**

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** Question the architecture (Phase 4 step 5).

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern, don't fix again. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence, trace data flow | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare, identify differences | Know what's different |
| **3. Hypothesis** | Form theory, test minimally, one variable at a time | Confirmed or new hypothesis |
| **4. Implementation** | Create regression test, fix root cause, verify | Bug resolved, all tests pass |

## Hermes Agent Integration

### Investigation Tools

Use these Hermes tools during Phase 1:

- **`search_files`** — Find error strings, trace function calls, locate patterns
- **`read_file`** — Read source code with line numbers for precise analysis
- **`terminal`** — Run tests, check git history, reproduce bugs
- **`web_search`/`web_extract`** — Research error messages, library docs

### With delegate_task

For complex multi-component debugging, dispatch investigation subagents:

```python
delegate_task(
    goal="Investigate why [specific test/behavior] fails",
    context="""
    Follow systematic-debugging skill:
    1. Read the error message carefully
    2. Reproduce the issue
    3. Trace the data flow to find root cause
    4. Report findings — do NOT fix yet

    Error: [paste full error]
    File: [path to failing code]
    Test command: [exact command]
    """,
    toolsets=['terminal', 'file']
)
```

### With test-driven-development

When fixing bugs:
1. Write a test that reproduces the bug (RED)
2. Debug systematically to find root cause
3. Fix the root cause (GREEN)
4. The test proves the fix and prevents regression

## Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common

**No shortcuts. No guessing. Systematic always wins.**
