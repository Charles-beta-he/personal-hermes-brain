---
name: skill-eval
description: "Systematically evaluate Hermes agent skills — test trigger accuracy, behavior correctness, and quality regressions. Use when creating new skills, updating existing skills, or running quality audits across the skill library."
license: MIT
tags: [skills, evaluation, quality, regression, testing]
---

# Skill Evals — 测试 Agent Skills 的系统方法

> 把 skills 从"感觉好用"变成"可测试、可打分、可回归"。

Based on OpenAI's eval-skills methodology, adapted for Hermes Agent.

## When to Use

- After a session produces a new technique, add it to the governing class-level skill as either a concise SKILL.md pointer plus `references/<topic>.md`, or patch an existing reference. Avoid one-session-one-skill proliferation.
- For session-derived skill updates, verify both the pointer and support file with `skill_view(name)` and `skill_view(name, file_path=...)` before reporting completion.
- When a skill's trigger accuracy degrades (false positives/negatives)
- Periodic quality audits of the skill library
- Before publishing a skill to the hub

## Core Concept: 4 Dimensions of Success

Every skill should be evaluable across these dimensions:

| Dimension | Question | How to Check |
|-----------|----------|-------------|
| **Outcome** | Did the task complete? | Output artifacts exist, commands succeeded |
| **Process** | Did the agent follow intended steps? | Expected commands in session transcript |
| **Style** | Does output follow conventions? | Rubric-based grading (manual or LLM) |
| **Efficiency** | No thrashing or wasted steps? | Command count, token usage, no loops |

## Step 1: Write Definition of Done

Every skill must have a `## Definition of Done` section with checkboxes for each dimension. Example:

```markdown
## Definition of Done

- [ ] **Outcome**: [specific deliverable]
- [ ] **Process**: [key steps that must be followed]
- [ ] **Style**: [conventions that must be followed]
- [ ] **Efficiency**: [anti-patterns to avoid]
```

## Step 2: Build Prompt Test Set

Create a CSV file at `{skill-dir}/evals/prompts.csv` with test cases:

```csv
id,should_trigger,prompt,notes
test-01,true,"Explicit invocation using /skill name",Baseline
test-02,true,"Implicit trigger with natural language describing the skill's domain",Trigger accuracy
test-03,true,"Contextual trigger with domain-specific jargon",Real-world noise
test-04,false,"Adjacent request that should NOT trigger this skill",Negative control
test-05,false,"Generic action that overlaps with skill description",False positive check
```

### Prompt Categories (include ALL types)

1. **Explicit** (test-01): User directly invokes skill by name — tests that direct usage works
2. **Implicit** (test-02): Natural language describing the exact scenario — tests trigger accuracy
3. **Contextual** (test-03): Real-world prompt with extra domain context — tests robustness
4. **Negative control** (test-04, test-05): Adjacent requests that should NOT trigger — catches false positives

### Minimum Viable Test Set

- 3 positive prompts (explicit + implicit + contextual)
- 2 negative prompts (adjacent + generic)
- Total: 5 prompts minimum, 10-20 for mature skills

## Step 3: Manual Trigger Test

Before automating, manually trigger the skill with each prompt to:

1. **Verify trigger behavior**: Does the skill activate when expected? Does it NOT activate for negative cases?
2. **Expose hidden assumptions**: Environment prerequisites, missing steps, ordering issues
3. **Record baseline behavior**: What commands are run? What files are created?

Record findings in `{skill-dir}/evals/baseline.md`.

## Step 4: Deterministic Checks

For skills that produce file artifacts or run specific commands, write checks:

```python
# Example: verify dogfood skill output
def check_dogfood_output(output_dir):
    return {
        "report_exists": os.path.exists(f"{output_dir}/report.md"),
        "screenshots_dir": os.path.exists(f"{output_dir}/screenshots/"),
        "report_has_sections": "Executive Summary" in open(f"{output_dir}/report.md").read(),
    }
```

### What to Check (by skill type)

| Skill Type | Deterministic Checks |
|-----------|---------------------|
| Code generation | Files created, syntax valid, tests pass |
| QA/audit | Report generated, issues classified, screenshots captured |
| DevOps/deploy | Commands executed, config files valid, service healthy |
| Research/content | Output file exists, structure matches template |

## Step 5: Rubric-Based Grading (Qualitative)

For style and convention checks that can't be deterministic:

1. Run the skill with a test prompt
2. Use a second agent (delegate_task) to grade the output against a rubric
3. Require structured JSON response:

```json
{
  "overall_pass": true,
  "score": 85,
  "checks": [
    {"id": "structure", "pass": true, "notes": "Follows expected layout"},
    {"id": "conventions", "pass": false, "notes": "Missing ARIA labels on 3 elements"}
  ]
}
```

## Step 6: Regression Tracking

After each skill update, re-run the prompt test set and compare:

1. Trigger accuracy: same prompts still trigger/don't trigger?
2. Behavior: same commands executed? Same output structure?
3. Quality: rubric scores same or better?

Store results in `{skill-dir}/evals/results/{date}.json`.

## Eval Report Template

After running evals, generate a report:

```markdown
# Skill Eval Report: {skill-name}
Date: {date}

## Trigger Accuracy
- Positive cases: {N}/{M} triggered correctly
- Negative cases: {N}/{M} correctly rejected

## Behavior Checks
- Deterministic: {pass_count}/{total_count}
- Rubric score: {score}/100

## Regressions
- [list any regressions from previous eval]

## Recommendations
- [improvements to skill description, steps, or Definition of Done]
```

## Integration with Existing Skills

### For skills with Definition of Done (dogfood, uimax-audit, auto-optimize-loop, requesting-code-review, loop)

The Definition of Done checkboxes map directly to eval checks:
- Outcome → deterministic artifact checks
- Process → command sequence verification
- Style → rubric grading
- Efficiency → command count / token tracking

### For new skills

1. Write skill with Definition of Done
2. Create evals/prompts.csv (5+ test cases)
3. Run manual trigger test
4. Add deterministic checks for outcome
5. Document in evals/baseline.md

## Pitfalls

- **Don't over-engineer**: 5 prompts + 3 deterministic checks > 50 prompts with no checks
- **Trigger tests depend on model**: Different models may trigger skills differently — test with your primary model
- **Negative cases matter most**: A skill that triggers too eagerly is worse than one that doesn't trigger enough
- **Session transcript is your trace**: Hermes doesn't have codex's --json output, but session_search can retrieve execution history
- **Rubric grading is subjective**: Use it for style checks only, not for outcome/process verification
