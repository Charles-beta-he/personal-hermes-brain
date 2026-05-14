---
name: theory-driven-evolution
description: 'Use when you need guidance on study a theoretical framework (book, theory, system) and operationalize it into Agent self-evolution infrastructure: chapter-by-chapter notes, capability mapping, health metrics, execution plan, and automated heartbeat monitoring.'
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - evolution
    - theory
    - framework
    - automation
    - self-improvement
    - control-theory
    related_skills:
    - domain
    - multi-model-thinking
    - plan
    - pua
---

# Theory-Driven Agent Evolution

## Overview


> Take any theoretical framework — control theory, systems theory, organizational science — and turn it into concrete Agent capability improvements with automated tracking.

## When to Use

- User says "study X book/theory and apply it to my Agent/workflow"
- User wants to ground Agent behavior in established scientific/framework principles
- Need quantitative metrics for "is my Agent getting better or worse?"
- Want automated heartbeat/cronjob to trigger self-improvement without manual prompting

## The Pattern

### Step 1: Source Discovery & Reconstruction

**Try to find the source material:**
```bash
# Wikipedia / Baidu Baike for structure
curl -s "https://zh.wikipedia.org/wiki/BOOK_NAME" -H "User-Agent:..."
# Douban for TOC
curl -s "https://book.douban.com/subject/ID/"
# Search local files
search_files("BOOK_NAME", target="content")
```

**If no clean TOC exists** (common for older/Chinese texts):
- Reconstruct from domain knowledge of the field
- Group concepts into logical chapters
- Aim for 8-20 chapters, each with a clear theme
- Don't fake quotes — state "reconstructed from domain knowledge" if needed

**Output:** `~/.hermes/notes/{topic}/ch{NN}-{slug}.md` for each chapter

### Step 2: Chapter-by-Chapter Theory → Agent Mapping

For each chapter, produce notes with exactly 5 sections:

```markdown
# Chapter N — Title

## Core Concepts
[What the theory says, in plain language]

## Key Ideas
[Bullet points of the important mechanisms/theorems]

## Math/Formalism (if any)
[The equations or formal structures — simplified for Agent context]

## Agent Evolution Mapping
| Theory Concept | Agent Mapping |
|---------------|---------------|
| [e.g. Negative Feedback] | [e.g. Build/test verification after each step] |
| [e.g. Stability Margin] | [e.g. Agent tolerance for noisy/incorrect inputs] |

## Evolution Insight
[What this chapter teaches us about building/improving Agents]
```

**Critical mapping discipline:**
- Don't force weak analogies. If a chapter doesn't map well, state it plainly.
- Focus on *actionable* mappings — things that change how the Agent works.
- Include anti-patterns: what the theory says to *avoid*.

### Step 3: Create the Health Metric (The "V Function")

Inspired by Lyapunov stability theory, define a scalar health function:

```
V = Σ wᵢ × metricᵢ
```

Where:
- `wᵢ` sum to 1.0
- Each `metricᵢ` is bounded [0, 1]
- `V̇ = V(t) - V(t-1)` is the change rate

**Recommended default weights** (adjust per framework):
```python
V = 0.30 * task_success_rate      # Did tasks complete successfully?
    + 0.25 * user_satisfaction    # How often did user need to correct?
    + 0.20 * skill_coverage       # What fraction of task types have skills?
    + 0.15 * build_pass_rate      # Code/build verification pass rate
    + 0.10 * iteration_efficiency # 1 / average turns per task
```

**Evolution thresholds:**
- V̇ > 0.05  → Significant evolution ✓
- |V̇| < 0.03 → Stagnation ⚠️ (needs new stimulus)
- V̇ < -0.05 → Degradation ✗ (trigger strategic review)

**Implementation:**
Create `~/.hermes/scripts/agent-health-monitor.py` that:
1. Collects proxy metrics from available data sources
2. Computes V and V̇
3. Writes to `~/.hermes/notes/{topic}/health-history.jsonl`
4. Prints a terminal-readable report with alerts
5. Returns exit code: 0=OK, 1=warning, 2=critical

**Proxy data sources** (since clean metrics pipelines rarely exist):
- `~/.pua/feedback.jsonl` → satisfaction
- `~/.pua/builder-journal.md` → failure patterns
- `git log --oneline -20` → build quality (look for [verified] tags)
- `~/.hermes/skills/` count → coverage
- Session history → success/iteration metrics

### Step 4: Execution Plan

Create `~/.hermes/notes/{topic}/EVOLUTION-PLAN.md` with:

1. **Theory-to-Capability mapping table** (from Step 2)
2. **Health function definition** (from Step 3)
3. **Phased rollout**: Break into 2-4 week phases, each with:
   - Control theory source chapter(s)
   - Concrete Agent changes
   - Acceptance criteria
4. **Automation triggers**: Define what cronjobs/heartbeats to set up
5. **Success metrics**: Quantitative targets for 4/8/12 weeks

### Step 5: Automation Setup

**Daily heartbeat** — Health monitoring:
```python
cronjob_create(
    name="{topic} Daily Health",
    schedule="0 0 * * *",
    script="agent-health-monitor.py",
    prompt="Run health monitor, analyze V/V̇ trend, output daily report"
)
```

**Weekly analysis** — Pattern detection:
```python
cronjob_create(
    name="{topic} Weekly Analysis",
    schedule="0 9 * * 1",
    script="weekly-failure-analysis.py",
    prompt="Detect oscillation patterns, extract top failure modes, suggest skill updates"
)
```

**Quarterly review** — Strategic calibration:
```python
cronjob_create(
    name="{topic} Quarterly Review",
    schedule="0 9 1 */3 *",
    prompt="Review V trajectory over quarter, update reference model, plan next phase"
)
```

**Critical cronjob pitfall** (learned from experience):
The `script` parameter must be a **relative filename** under `~/.hermes/scripts/`, NOT a path.
- ❌ `script="~/.hermes/scripts/my-script.py"` → fails
- ✅ `script="my-script.py"` → works (resolves to `~/.hermes/scripts/my-script.py`)

## Variations by Framework Type

### Control Theory / Cybernetics (e.g. Qian Xuesen)
- Focus: Feedback loops, stability, adaptation, state estimation
- Health metric: Lyapunov-style V(x) with stability margins
- Key automation: Oscillation detection, adaptive sampling

### Systems Theory (e.g. von Bertalanffy)
- Focus: Emergence, boundaries, entropy, equifinality
- Health metric: System entropy (disorder) reduction rate
- Key automation: Boundary audit, emergent behavior detection

### Organizational Theory (e.g. Mintzberg, Drucker)
- Focus: Structure, coordination, strategy-execution gap
- Health metric: Alignment score between strategy and execution
- Key automation: Strategy drift detection, coordination friction audit

### Complexity Science (e.g. Santa Fe Institute)
- Focus: Agent-based modeling, phase transitions, fitness landscapes
- Health metric: Fitness landscape climbing velocity
- Key automation: Local optimum trap detection, exploration rate tuning

## Key Experiential Findings

### 1. No Clean Source? Reconstruct.
Older books, especially Chinese classics, often lack digital TOCs. Don't get stuck searching — reconstruct from domain knowledge. State clearly when reconstructed vs. directly sourced.

### 2. Theory Must Be Actionable
A chapter mapping that says "this is interesting" is worthless. Every mapping must answer: "What should the Agent do differently after reading this?"

### 3. Proxy Metrics Are Sufficient
Don't wait for a perfect metrics pipeline. Build the health monitor to work with whatever data exists — git logs, feedback files, skill counts. A rough V with V̇ trend is infinitely better than no V at all.

### 4. V̇ Is The Key Signal
The absolute value of V matters less than its derivative. A healthy Agent should have V̇ consistently positive (or at least non-negative). Negative V̇ is the canary in the coal mine.

### 5. Automation Without Delivery
Set `deliver="local"` for cronjobs that just write reports to disk. Only use chat delivery for jobs that actually need human attention (e.g., V̇ < -0.05 alerts).

## Theory-to-Impact Architecture Propagation

When a single slice improves because of a theory/principle, do not stop at the local fix. Bind the change to a canonical `Theory Point ID`, scan Same-theory propagation targets, build a Layer Impact Map across L0-L5/LX plus skills/cron/gateway as applicable, and require operational smoothing gates (rollback/regression/evidence/selfcheck/health/diff) before claiming architecture-wide optimization.

Hermes-native verifier:

```bash
HERMES_BRAIN_VAULT=/Users/charles/Documents/brain \
  python3 ~/.hermes/scripts/architecture_theory_impact_ratchet.py --json
```

Expected closeout shape: theories `8/8`, surfaces `9/9`, gate_checks `100%`, failed_checks `[]`. If this fails, the optimization is still a local candidate or quarantined advisory, not a stable architecture rule.

Canonical artifacts:
- `~/Documents/brain/05-实践与项目/实践方案/08-理论到影响全架构传播矩阵.md`
- `~/Documents/brain/04-知识原子/atoms/theory-impact-propagation.md`
- `multi-model-thinking:references/theory-impact-propagation.md`

## Systems-Engineering Control-Plane Overlay

When the user says the agent lacks a skill tree, project-specific working memory, reusable frontend closure standards, or asks to apply Qian Xuesen / systems engineering to the agent itself, treat it as a missing semantic control-plane layer rather than a simple memory update. Use `references/systems-engineering-control-plane-overlay.md`.

Required pattern:
- Audit current brain/skill graph/search coverage before creating new artifacts.
- Separate four stores: persistent memory for durable user facts; skill tree for class-level routes; project workpad for project-specific north star/anchors/red lines/evidence; session todo for temporary state.
- Land reversible local-brain overlays first: skill route matrix, project work-memory template, frontend closure playbook, systems-engineering atom, review/proof log, and self-check script.
- Verify with `brainctl sync`, `brainctl reindex`, and a self-check that tests both file existence and search hits.
- Watch for `brainctl search` mixed Chinese+English query misses; patch self-check queries to exact titles/frontmatter keywords and record the verifier fix.

## Local Brain Theory Foundation Fill

When the user identifies that a local-brain theory/category folder exists but lacks real content (for example `01-控制论基础/` exists but has no theory notes), treat it as a content-governance gap, not just a writing task. Use `references/local-brain-theory-foundation-fill.md`.

Required pattern:
- Audit the folder and related existing notes first.
- Create a MOC/index, core concept cards, bibliography/evidence-boundary note, task proof log, and optional evolution log.
- Include English concept keywords in frontmatter so `brainctl search` works even when the folder/title is Chinese.
- Run `brainctl sync`, `brainctl reindex`, and multiple `brainctl search` queries; write the observed results back into the proof log.
- If `~/.hermes` is a git repo, commit only scoped brain/log artifacts with a local commit; do not push unless explicitly requested.

## Definition of Done

- [ ] **Outcome**: 8-20 chapter notes generated, each with theory→Agent mapping
- [ ] **Health metric**: V(x) defined with weights, components, thresholds
- [ ] **Monitor script**: `agent-health-monitor.py` runs and produces readable output
- [ ] **Execution plan**: Phased rollout with concrete tasks and acceptance criteria
- [ ] **Automation**: At least daily heartbeat cronjob scheduled and running
- [ ] **Baseline**: Initial V value recorded, V̇ computable

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] The Definition of Done items above were explicitly checked, not assumed.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

