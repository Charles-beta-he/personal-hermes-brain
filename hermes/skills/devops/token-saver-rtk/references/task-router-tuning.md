# Task Router Tuning Guide

## Architecture
agent/task_router.py — Complexity-based model routing. Zero API calls, <1ms.

## Scoring Dimensions (must sum to ~1.0)
| Dimension | Weight | Detection |
|-----------|--------|-----------|
| code_presence | 0.23 | ```/def/class/import detection |
| reasoning_markers | 0.19 | analyze/design/why/debug/optimize |
| technical_terms | 0.19 | api/deploy/architecture/refactor/database |
| question_complexity | 0.15 | length + sub-question count |
| multi_step_patterns | 0.12 | first...then...finally |
| token_count | 0.08 | len(text.split()) |
| simple_indicators | 0.04 | hi/ok/thanks/yes |

## Boundaries (config.yaml router.boundaries)
| Tier | Score Range | Model |
|------|-------------|-------|
| SIMPLE | 0.00 - 0.08 | gpt-4o-mini ($0.15/1M) |
| MEDIUM | 0.08 - 0.15 | gpt-4o ($2.50/1M) |
| COMPLEX | 0.15 - 0.25 | gpt-5.4 ($10/1M) |
| REASONING | 0.25+ | claude-sonnet-4 ($3/1M) |

## Tuning Process
1. Run test cases: `python3 -c "from agent.task_router import TaskRouter; ..."`
2. Check accuracy against expected tiers
3. Adjust boundaries (not weights) for fine-tuning
4. Verify weights sum: `sum(router.weights.values()) == 1.0`

## Known Issues
- Weights initially summed to 1.30 → boundaries meaningless
- Missing technical terms: architecture, migration, refactor, scale, optimize
- "fix the TypeScript error" classified as SIMPLE (code_presence=0, no code markers)
- Accuracy: ~67% (rule-based baseline, no API calls)

## Integration
- delegate_task: per-task routing in tools/delegate_tool.py
- run_agent.py: dynamic reasoning_effort via TaskRouter
- config: router.enabled: true, router.strategy: complexity
