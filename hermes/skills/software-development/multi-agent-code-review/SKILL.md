---
name: multi-agent-code-review
description: Use when the task falls under Multi-Agent Parallel Code Review with Confidence Filtering.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - code-review
    - multi-agent
    - parallel
    - confidence
    - aggregation
    - quality
    related_skills:
    - github-code-review
    - agent-team-parallel
    - delegate_task
---

# Multi-Agent Parallel Code Review with Confidence Filtering

## Overview


将代码审查分解为正交关注域，各 Agent 独立并行审查同一份代码，聚合时用跨 Agent 一致性 + 自报置信度计算复合分数，按 severity 分级阈值过滤噪声。

## When to Use

- PR 改动较大（100+ 行），单 Agent 审查容易遗漏
- 需要同时关注安全、性能、风格等多个维度
- 想减少 false positive —— 只有多个 Agent 都发现的问题才报告
- 用户要求 "thorough review" 或 "全面审查"
- 代码变更涉及关键路径（认证、支付、数据处理）

## When NOT to Use

- 小改动（< 30 行）—— 单 Agent 足够
- 纯文档/配置变更 —— 不需要多维度审查
- 资源紧张 —— 多 Agent 会消耗更多 tokens

## Architecture

```
┌─────────────┐
│  Diff/Code  │
└──────┬──────┘
       │ same code to all agents
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
    1. Semantic dedup (file+line+category)
    2. Cross-agent agreement scoring
    3. Confidence weighting
    4. Severity-based threshold filtering
           │
           ▼
    Filtered, Ranked Findings
```

## Step-by-Step Execution

### Step 1: Prepare the Diff

Get the code to review. Use `git diff` for local changes or `gh pr diff` for PRs.

```bash
# Local changes
git diff main...HEAD > /tmp/review-diff.txt

# Or for a PR
gh pr diff 123 > /tmp/review-diff.txt

# Get file list for context
git diff main...HEAD --name-only
```

### Step 2: Launch Parallel Review Agents

Use `delegate_task` with batch mode (up to 3 concurrent, configurable):

```python
delegate_task(
    tasks=[
        {
            "goal": """You are a SECURITY code reviewer. Review ONLY for security issues:
- SQL injection, XSS, path traversal
- Hardcoded secrets, API keys, credentials
- Authentication/authorization bypass
- Input validation gaps

For EACH finding, output JSON:
{
  "agent": "security",
  "findings": [
    {
      "file": "path", "line": N,
      "severity": "critical|high|medium|low",
      "finding": "description",
      "suggestion": "fix",
      "confidence": 0.0-1.0,
      "reasoning": "why this is real"
    }
  ]
}

Be CONSERVATIVE. Rate confidence honestly. Prefer false negatives over false positives.
If no issues found, return {"agent":"security","findings":[]}""",
            "context": "<diff content here>",
            "toolsets": ["terminal", "file"]
        },
        {
            "goal": """You are a LOGIC/CORRECTNESS code reviewer. Review ONLY for:
- Off-by-one errors
- Null/None handling gaps
- Race conditions, concurrency issues
- Edge cases (empty input, boundary values)
- Error handling gaps

Output JSON with same schema as above but agent:"logic".
Be CONSERVATIVE. Prefer false negatives over false positives.""",
            "context": "<diff content here>",
            "toolsets": ["terminal", "file"]
        },
        {
            "goal": """You are a PERFORMANCE code reviewer. Review ONLY for:
- O(n²) or worse algorithmic complexity
- N+1 database queries
- Unnecessary memory allocations
- Missing caching opportunities
- Blocking operations in async code

Output JSON with same schema as above but agent:"performance".
Be CONSERVATIVE. Prefer false negatives over false positives.""",
            "context": "<diff content here>",
            "toolsets": ["terminal", "file"]
        }
    ]
)
```

### Step 3: Aggregate and Score Findings

Parse results from all agents, deduplicate, and compute composite scores:

```python
import json
from collections import defaultdict

def aggregate(agent_results):
    all_findings = []
    for result in agent_results:
        data = json.loads(result)
        for f in data["findings"]:
            f["source_agent"] = data["agent"]
            all_findings.append(f)

    # Deduplicate by file+line+category
    clusters = defaultdict(list)
    for f in all_findings:
        key = (f["file"], f["line"], f.get("category", f["source_agent"]))
        clusters[key].append(f)

    total_agents = len(agent_results)
    scored = []
    for key, group in clusters.items():
        agreement = len(group) / total_agents
        avg_conf = sum(f["confidence"] for f in group) / len(group)
        final_score = (agreement * 0.6) + (avg_conf * 0.4)

        sev = max(group, key=lambda f: {"critical":4,"high":3,"medium":2,"low":1}[f["severity"]])["severity"]
        threshold = {"critical": 0.3, "high": 0.5, "medium": 0.7, "low": 0.7}[sev]

        if final_score >= threshold:
            scored.append({
                "file": key[0], "line": key[1],
                "severity": sev,
                "finding": group[0]["finding"],
                "suggestion": group[0]["suggestion"],
                "confidence": round(final_score, 2),
                "agents_flagging": len(group),
                "agents": [f["source_agent"] for f in group]
            })

    sev_order = {"critical":0, "high":1, "medium":2, "low":3}
    scored.sort(key=lambda f: (sev_order[f["severity"]], -f["confidence"]))
    return scored
```

### Step 4: Present Filtered Results

Output format (plain text, CLI-friendly):

```
=== Multi-Agent Code Review Summary ===

Total findings: 12 (from 5 raw → 3 agents)
After confidence filtering: 7 findings

🔴 CRITICAL (threshold: 0.3)
  src/auth.py:42  [conf:0.91  agents:3/3]
    SQL injection: user input concatenated into query
    Fix: Use parameterized queries

⚠️  HIGH (threshold: 0.5)
  src/models.py:23  [conf:0.78  agents:2/3]
    Password stored without hashing
    Fix: Use bcrypt/argon2 before storage

💡 MEDIUM (threshold: 0.7)
  src/utils.py:8  [conf:0.72  agents:2/3]
    Duplicated logic with core/utils.py:34
    Fix: Extract shared function

📊 Confidence Distribution
  >= 0.85: 1 finding (auto-include)
  0.60-0.85: 4 findings (include with note)
  0.40-0.60: 2 findings (supplementary)
  < 0.40: 5 findings (suppressed)
```

### Step 5: Post to GitHub (Optional)

If reviewing a PR, post the filtered results:

```bash
gh pr review 123 --comment --body "$(cat <<'EOF'
## Multi-Agent Code Review (3 agents: Security, Logic, Performance)

Found 7 issues after confidence filtering (5 raw findings suppressed).

### 🔴 Critical
- **src/auth.py:42** — SQL injection (confidence: 0.91, 3/3 agents agree)

### ⚠️ High
- **src/models.py:23** — Plaintext password (confidence: 0.78, 2/3 agents)

### 💡 Medium
- **src/utils.py:8** — Duplicated logic (confidence: 0.72, 2/3 agents)

---
*Multi-agent review by Hermes — confidence threshold applied*
EOF
)"
```

## Scoring Formula

```
final_score = (agent_agreement_ratio × 0.6) + (avg_self_confidence × 0.4)
```

- `agent_agreement_ratio` = agents_flagging / total_agents
- `avg_self_confidence` = mean of self-reported confidences

### Threshold Table

| Severity | Threshold | Rationale |
|----------|-----------|-----------|
| critical | 0.3 | Asymmetric cost — miss a vuln >> review a false positive |
| high | 0.5 | Balance between coverage and noise |
| medium | 0.7 | Users ignore noisy medium-severity suggestions |
| low | 0.7 | Style/minor issues need high confidence to be useful |

## Variant: 5-Agent Full Review

For maximum coverage, use 5 agents:

1. **Security** — OWASP Top 10, secrets, auth
2. **Style** — naming, formatting, idioms, dead code
3. **Logic** — correctness, edge cases, concurrency
4. **Performance** — complexity, queries, allocations
5. **Architecture** — coupling, SOLID, dependencies

With 5 agents, agreement_ratio becomes more meaningful:
- 5/5 agree = near-certain real issue
- 3/5 agree = likely real
- 1/5 = probably noise

## Variant: Lightweight 2-Agent Review

For moderate PRs, 2 agents suffice:

1. **Bugs** — correctness + security combined
2. **Quality** — style + performance + architecture combined

Agreement = both agents flagging same issue = very high confidence.

## Definition of Done

- [ ] **Outcome**: Findings JSON produced for each agent, aggregated and filtered results presented
- [ ] **Process**: 5-step flow followed (diff → parallel dispatch → aggregate → filter → present)
- [ ] **Style**: Output grouped by severity tier (Critical/High/Medium/Low), confidence and agent count shown
- [ ] **Efficiency**: Aggregation done with rule-based script (no LLM call for scoring); no redundant re-reviews

## Historical Precision Weighting

When a feedback loop exists (human accept/reject tracked), use the enhanced formula instead of the default:

```
final_conf = (self_conf × 0.3) + (agreement × 0.3) + (historical_precision × 0.4)
```

Where `historical_precision` = agent's accepted findings / total findings across past reviews.

Initialize with Beta(2, 2) prior (uniform with mild regularization). Update after each review:
- Finding accepted → alpha += 1
- Finding rejected → beta += 1
- historical_precision = alpha / (alpha + beta)

Without historical data, fall back to the default formula: `final_score = (agreement × 0.6) + (avg_conf × 0.4)`

## Model-Specific Confidence Notes

Different LLMs have different confidence calibration profiles:
- **Claude**: tends toward 0.75–0.95 range; moderate overconfidence
- **GPT-4/5**: wider spread 0.6–0.95; better at expressing uncertainty
- **DeepSeek/Mimo**: may cluster around 0.8–0.9; less calibrated for code tasks

When mixing models across agents, the cross-agreement term (weighted 0.6) compensates for model-specific bias. For highest reliability, use the same model across all review agents and let the orthogonal prompts create diversity.

## Common Pitfalls

- **Confidence filtering is not the truth gate** — agreement scoring reduces noise, but it can suppress real medium-severity security/correctness bugs. If a single-agent finding includes deterministic reproduction, an exact file-state proof, or a new failing test, promote it as `accepted_by_deterministic_override` even when agreement score is below the default threshold. See `references/historical-diff-replay-2026-05-13.md`.
- **Autonomous task-pool reviews need runtime wiring checks, not just static code reading** — when reviewing controllers/schedulers/envelope buses for auto-execution safety, inspect the cron/job configuration and scheduler semantics that invoke them. A common high-priority bug is a job field like `script: "controller.py cycle"` being treated as a literal path instead of `script + args`; recommend structured argv or a wrapper, never `shell=True`.
- **Proof gates must be enforced below the controller** — if a controller claims "proof required for DONE", verify the state-transition layer rejects `DONE` without proof/hash evidence. Flag paths like `done_no_proof` entering model verification as P0: model judgment can supplement but must not replace deterministic proof/artifact validation.
- **Review type boundaries around verifier glue** — task automation often passes proof dicts, strings, and profile names through the same path. Reproduce minimal calls for suspected `str`/`dict`/`None` mismatches before finalizing findings; these are often higher priority than syntax issues because they crash after a task is claimed.
- **Distinguish historical escape counters from recent/consecutive failures** — human-escape or circuit-breaker logic that counts all historical `FAILED`/`BLOCKED` rows can permanently self-DoS the pipeline. Recommend scoped, time-windowed, or consecutive-failure counters plus explicit human reset/ack events.
- **Do not propose unsafe fixes for scheduler arguments** — never suggest `shell=True`, arbitrary absolute-path allowlists, or clearing the state DB as a fix. Prefer bounded argv, scripts-dir path validation, wrapper scripts, and preserving audit history.
- **Token cost scales linearly** — 5 agents = ~5x tokens vs single review. Use 3 agents as default; 5 only for critical code.
- **Sub-agents cannot interact with user** — delegate_task children cannot use clarify. All context must be in the prompt.
- **JSON output format must be explicit** — LLMs may return markdown-wrapped JSON. Parse with `json.loads()` after stripping code fences.
- **Semantic dedup is imperfect** — file+line matching misses near-duplicates. For high-stakes reviews, add embedding similarity.
- **Self-reported confidence is miscalibrated** — LLMs tend toward 0.7-0.9 range. The cross-agreement term compensates but doesn't fully fix this.
- **Same file conflicts** — if multiple agents suggest different fixes for the same line, present both options to the human.
- **Large diffs may exceed context** — for PRs with 1000+ lines changed, split into per-file reviews and aggregate.
- **Temperature matters** — use 0.0-0.2 for reviewer agents (deterministic). Higher temps increase variance in confidence scores.
- **Agent order doesn't matter** — but prompt specificity does. Vague prompts produce vague findings.
- **Don't review generated code** — auto-generated files (protobuf, lock files) should be excluded from review scope.
- **Concurrency limit** — delegate_task default is 3 concurrent. For 5 agents, 2 will queue. Adjust via `delegation.max_concurrent_children`.
- **Aggregator can be rule-based** — no need for another LLM call. The Python aggregation script above is deterministic and fast.
1. Skipping prerequisite checks and assuming the environment already matches the workflow.
2. Applying the workflow mechanically without confirming that the request still matches this skill's trigger class.
3. Reporting success before reading back the actual outputs, files, or external side-effects.
## References

- `references/multi-agent-review-architecture.md` — Architecture patterns, agent decomposition, scoring methods
- `references/confidence-calibration.md` — Calibration techniques, Bayesian reputation, feedback loops
- `references/hermes-implementation-pattern.md` — Hermes-specific delegate_task patterns, aggregation script

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] The Definition of Done items above were explicitly checked, not assumed.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

