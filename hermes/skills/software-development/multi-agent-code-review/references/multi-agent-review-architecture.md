# Multi-Agent Code Review Architecture Reference

## Overview

Multi-agent parallel code review decomposes the review process into orthogonal
expertise domains, each handled by an independent AI agent. Findings are then
aggregated with confidence scoring to filter noise from signal.

## Agent Decomposition (Orthogonal Concerns)

Split review into independent agents, each with a specialized system prompt:

| Agent | Focus | Checklist |
|-------|-------|-----------|
| Security | SQLi, XSS, path traversal, secrets, authz/authn | OWASP Top 10, hardcoded creds, input validation |
| Style | Naming, formatting, idioms, dead code, readability | Language conventions, DRY, naming clarity |
| Logic | Off-by-one, null handling, race conditions, edge cases | Boundary values, error paths, concurrency |
| Performance | O(n^2) loops, unnecessary allocations, N+1 queries | Hot paths, caching, async/await misuse |
| Architecture | Coupling, SOLID violations, dependency misuse | Module boundaries, abstraction levels |

Each agent receives the SAME code but a DIFFERENT system prompt.

## Structured Output Schema

All agents return findings in a consistent JSON structure:

```json
{
  "findings": [
    {
      "file": "src/auth.py",
      "line": 42,
      "category": "security",
      "severity": "high",
      "finding": "User input used directly in SQL query",
      "suggestion": "Use parameterized queries with cursor.execute(query, params)",
      "confidence": 0.92,
      "reasoning": "Classic SQL injection pattern - string concatenation with user input"
    }
  ]
}
```

Key fields:
- `confidence` (0.0-1.0): Agent's self-reported certainty
- `reasoning`: Why the agent believes this is a real issue
- `severity`: critical / high / medium / low
- `category`: Must match agent's expertise domain

## Confidence Scoring Methods

### Method 1: Self-Reported Confidence
Each agent rates its own certainty. Works moderately well when prompt-engineered:
"Rate your confidence that this is a real issue, not a false positive, from 0.0 to 1.0. Be conservative — prefer false negatives over false positives."

### Method 2: Cross-Agent Agreement (More Powerful)
After all agents finish, check overlap:
- Same file + line + similar category = high overlap
- Same file, different lines = medium overlap
- Related files (caller/callee) = low overlap

### Method 3: Composite Score (Recommended)
```
final_score = (agent_agreement_ratio * 0.6) + (avg_self_confidence * 0.4)
```
Where:
- `agent_agreement_ratio` = count(agents_flagging_issue) / total_agents
- `avg_self_confidence` = mean of self-reported confidences for that finding

### Method 4: Noisy OR
```
score = 1 - (1-p1)(1-p2)...(1-pN)
```
If any agent is confident, the finding is likely real.

## Filtering Thresholds

| Score Range | Label | Action |
|-------------|-------|--------|
| >= 0.85 | High confidence | Auto-include |
| 0.60 - 0.85 | Medium | Include with warning |
| 0.40 - 0.60 | Low | Optional/supplementary |
| < 0.40 | Noise | Suppress |

### Severity-Based Adjustments
- Security findings: lower threshold to 0.3 (catch more, tolerate false positives)
- Style/formatting: raise threshold to 0.7 (users ignore noisy suggestions)
- Performance: keep at 0.5

## Semantic Deduplication

Findings from different agents must be clustered. Approaches:
1. **Structured matching**: file + line + category (simple, fast)
2. **Embedding similarity**: cosine similarity on finding descriptions (more accurate)
3. **AST proximity**: same AST node or nearby nodes (most precise)

## Implementation Architecture

```
┌─────────────┐
│  Input Code  │
└──────┬──────┘
       │ (same code to all)
  ┌────┴────┬────────┬────────┬────────┐
  ▼         ▼        ▼        ▼        ▼
Security  Style   Logic   Perf    Arch
Agent     Agent   Agent   Agent   Agent
  │         │        │        │        │
  ▼         ▼        ▼        ▼        ▼
[{findings}]  [{findings}]  ...
  └────────┬────┴────────┬──┘
           ▼
    Aggregator
    - Semantic dedup
    - Cross-agent agreement scoring
    - Confidence weighting
    - Severity boosting
           │
           ▼
    Filtered, Ranked Findings
    (grouped by severity + confidence)
```

## Implementation Tips

- Use structured output (JSON schema) for all agent responses
- Add "confidence" and "reasoning" fields to every finding
- Run agents in parallel via asyncio.gather() or delegate_task
- The aggregator can be rule-based (no LLM needed) or a final LLM call
- Keep temperature low (0.0-0.2) for reviewer agents; moderate (0.3) for aggregator
- Log raw findings before filtering for debugging/tuning
