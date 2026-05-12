---
type: evaluation
project: hermes-skill-learning
source_candidate: "Planning with Files"
source_origin: "screenshot #2 — obra/superpowers ecosystem (Claude Code Skills)"
evaluated_at: 2026-05-11T23:57:00+08:00
decision: borrow
---

# Planning with Files — Evidence-First Evaluation

## 1. Source Verification

| Item | Finding |
|------|---------|
| Source | obra/superpowers (github.com/obra/superpowers, 186k stars) |
| Author | Jesse Vincent (@obra) + 11 contributors |
| License | MIT (repo-level) |
| Version | v5.1.0 (latest release) |
| Status | Active — 440 commits, 64 branches, weekly releases |
| Screenshot entry | #2: "把规划写进文件，上下文压缩了也不丢状态" |

Note: "Planning with Files" is a PATTERN described in the superpowers ecosystem,
not a standalone skill file in the repo. The pattern is distributed across
`writing-plans` and `executing-plans` skills. Hermes already adapted
`writing-plans` (author: "Hermes Agent (adapted from obra/superpowers)").

## 2. Capability Analysis

Core mechanism:
  Agent writes plans/progress to files on disk.
  When context is compressed/truncated, agent re-reads the file to recover state.
  Plans include: objective, step checklist, decisions, files changed, resume protocol.

Why it works:
  - Files survive context window compression (external memory)
  - Checklist format enables progress tracking (checked/unchecked)
  - "Current step" marker enables precise resume
  - Decisions captured prevent re-deliberation after context loss

## 3. Hermes Coverage Comparison

### Already Present (2/6)

| Feature | Hermes Implementation | Coverage |
|---------|----------------------|----------|
| plan_to_file | `writing-plans` + `plan` skills → .hermes/plans/ | Full |
| task_pool_files | Markdown tasks in ~/Documents/brain/ with frontmatter | Full |

### Missing (4/6)

| Feature | Gap | Severity |
|---------|-----|----------|
| handoff_artifacts | IterationBudget strategy designed but templates not created | Medium |
| workpad | No scratchpad for intermediate reasoning state | Medium |
| compression_resume_protocol | No standard "re-read plan after context loss" instruction | High |
| checkpointing | No auto-checkpoint on context pressure signals | Low |

## 4. Compression-Recovery Simulation

Test: wrote plan file with 5 steps, completed 2, marked step 3 as current.
Simulated full context loss. Re-read file only. Verified 10/10 state checks:

  PASS: objective_found
  PASS: current_step_found
  PASS: current_marker_found
  PASS: completed_steps_found
  PASS: pending_steps_found
  PASS: decisions_preserved
  PASS: files_changed_tracked
  PASS: next_action_clear
  PASS: blocker_status
  PASS: resume_protocol

Result: 10/10 — full state recovery from file alone.

## 5. Decision: BORROW

Rationale:
  - The PATTERN is sound and proven (compression-recovery test: 10/10)
  - Hermes already has 2/6 features (plan_to_file, task_pool_files)
  - The 4 gaps are INTEGRATION improvements, not a new skill
  - No need to install/import a new skill — bolt onto existing infrastructure

What to borrow (not adopt wholesale):
  1. Add resume protocol to existing `plan` skill instructions
  2. Create handoff template (already designed in IterationBudget strategy)
  3. Add workpad concept as .hermes/workpad/ convention
  4. Optional: auto-checkpoint hook on context pressure (P2)

What NOT to do:
  - Do not install a new "planning-with-files" skill (redundant with writing-plans)
  - Do not create a second canonical plan location
  - Do not claim this is adopted — it's advisory borrowing

## 6. Residual Risk

- Low: pattern is well-understood and low-complexity
- Medium: handoff_artifacts gap means long-running tasks still risk state loss
  at budget exhaustion (mitigated by existing bounded-tick pattern)
- The 4 gaps are actionable within existing Hermes architecture
