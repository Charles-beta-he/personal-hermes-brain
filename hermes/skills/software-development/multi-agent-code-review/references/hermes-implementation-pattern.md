# Hermes Implementation: Multi-Agent Parallel Code Review

## Using Hermes delegate_task for Parallel Review

Hermes `delegate_task` supports batch mode with multiple tasks running
concurrently. Each sub-agent gets its own conversation and toolset.

### Pattern: Fan-Out Review

```python
# In the orchestrator agent:
delegate_task(
    tasks=[
        {
            "goal": "Review this code for SECURITY issues only. Focus on: SQL injection, XSS, path traversal, hardcoded secrets, auth bypass. Return findings as JSON.",
            "context": "<diff content>",
            "toolsets": ["terminal", "file"]
        },
        {
            "goal": "Review this code for LOGIC/CORRECTNESS issues only. Focus on: off-by-one, null handling, race conditions, edge cases. Return findings as JSON.",
            "context": "<diff content>",
            "toolsets": ["terminal", "file"]
        },
        {
            "goal": "Review this code for PERFORMANCE issues only. Focus on: O(n^2) loops, N+1 queries, unnecessary allocations, async misuse. Return findings as JSON.",
            "context": "<diff content>",
            "toolsets": ["terminal", "file"]
        }
    ]
)
```

### Pattern: Aggregator

After collecting results from all sub-agents:

1. Parse JSON findings from each agent
2. Deduplicate by file + line + category (structured matching)
3. For each unique finding:
   - Count how many agents flagged it (agreement_ratio)
   - Average self-reported confidences
   - Compute final_score = (agreement * 0.6) + (avg_conf * 0.4)
4. Apply severity-based thresholds
5. Sort by final_score descending
6. Output grouped by severity tier

### Using with github-code-review Skill

Combine with the `github-code-review` skill:
1. Use `gh pr diff` or `git diff` to get the code
2. Feed the diff into parallel reviewer agents
3. Aggregate findings
4. Post filtered results as PR review using `gh pr review`

### Concurrency Limits

- `delegate_task` default: 3 concurrent children
- Configurable via `delegation.max_concurrent_children`
- For 5 agents, 2 will queue (still faster than sequential)

### Output Format for Aggregation

Each sub-agent MUST return findings in this exact JSON format:

```json
{
  "agent": "security",
  "findings": [
    {
      "file": "path/to/file.py",
      "line": 42,
      "severity": "critical|high|medium|low",
      "finding": "Description of the issue",
      "suggestion": "How to fix it",
      "confidence": 0.85,
      "reasoning": "Why I believe this is real"
    }
  ]
}
```

### Aggregation Script (Python)

```python
import json
from collections import defaultdict

def aggregate_findings(agent_results, min_confidence=0.4, min_agreement=0.4):
    """Aggregate findings from multiple review agents."""
    # Parse all findings
    all_findings = []
    for result in agent_results:
        data = json.loads(result)
        for f in data["findings"]:
            f["source_agent"] = data["agent"]
            all_findings.append(f)

    # Deduplicate by file+line+category
    clusters = defaultdict(list)
    for f in all_findings:
        key = (f["file"], f["line"], f["category"])
        clusters[key].append(f)

    # Score each cluster
    total_agents = len(agent_results)
    scored = []
    for key, group in clusters.items():
        agreement = len(group) / total_agents
        avg_conf = sum(f["confidence"] for f in group) / len(group)
        max_severity = max(group, key=lambda f: {"critical":4,"high":3,"medium":2,"low":1}[f["severity"]])["severity"]
        final_score = (agreement * 0.6) + (avg_conf * 0.4)

        # Severity-based threshold
        threshold = {"critical": 0.3, "high": 0.5, "medium": 0.7, "low": 0.7}[max_severity]

        if final_score >= threshold:
            scored.append({
                "file": key[0],
                "line": key[1],
                "severity": max_severity,
                "finding": group[0]["finding"],
                "suggestion": group[0]["suggestion"],
                "confidence": round(final_score, 2),
                "agents_flagging": len(group),
                "agents": [f["source_agent"] for f in group]
            })

    # Sort by severity then confidence
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    scored.sort(key=lambda f: (severity_order[f["severity"]], -f["confidence"]))
    return scored
```
