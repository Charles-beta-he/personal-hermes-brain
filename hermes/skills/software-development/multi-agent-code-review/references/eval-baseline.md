# Eval Baseline: multi-agent-code-review
# Date: 2026-05-13

## Trigger Test Results

### Positive Cases (should trigger)

| ID | Prompt | Triggered | Notes |
|----|--------|-----------|-------|
| test-01 | "Use multi-agent code review on this PR" | ✅ | Direct skill name match |
| test-02 | "parallel code review with confidence filtering" | ✅ | Core concept match |
| test-03 | "多agent并行审查，置信度过滤" | ✅ | Chinese trigger phrases present |
| test-04 | "5-agent security/style/logic/perf/arch review" | ✅ | Agent decomposition language |
| test-05 | "Aggregate findings from multiple review agents" | ✅ | Aggregation + severity threshold |
| test-10 | "全面代码审查，安全、性能、架构多维度并行" | ✅ | Chinese natural language |

### Negative Cases (should NOT trigger)

| ID | Prompt | Correctly Rejected | Redirect Target |
|----|--------|-------------------|-----------------|
| test-06 | "Review my PR" | ✅ | github-code-review |
| test-07 | "Run parallel tasks on 3 files" | ✅ | agent-team-parallel |
| test-08 | "Check this code for bugs" | ✅ | Single-agent sufficient |
| test-09 | "Set up CI pipeline" | ✅ | DevOps domain |

### Summary
- Positive accuracy: 6/6 (100%)
- Negative accuracy: 4/4 (100%)
- Overall trigger accuracy: 10/10 (100%)

## Behavior Baseline

### Expected Agent Dispatch (3-agent default)
1. Security agent: OWASP Top 10, secrets, auth bypass
2. Logic agent: off-by-one, null handling, edge cases
3. Performance agent: complexity, N+1 queries, allocations

### Expected Output Structure
- Severity-grouped (Critical → High → Medium → Low)
- Each finding: file, line, confidence, agents_flagging, suggestion
- Confidence distribution summary at end

### Expected Aggregation
- Dedup by file + line + category
- final_score = (agreement × 0.6) + (avg_conf × 0.4)
- Severity thresholds: critical=0.3, high=0.5, medium=0.7, low=0.7

## Deterministic Checks

1. ✅ SKILL.md has YAML frontmatter with required fields
2. ✅ 3 reference files exist (architecture, calibration, implementation)
3. ✅ Python aggregation script is syntactically valid (stdlib only)
4. ✅ Scoring formula documented with rationale
5. ✅ Definition of Done section present (added 2026-05-13)
6. ✅ Historical precision formula surfaced in SKILL.md (added 2026-05-13)
7. ✅ Model-specific confidence notes present (added 2026-05-13)
8. ✅ eval-prompts.csv with 10 test cases created (added 2026-05-13)
