# Self-evolving agent architecture: memory + harness + bad-case benchmark

Use this reference when asked to design or critique an Agent system that should improve from production failures. It condenses a session analyzing how to apply Hermes-style memory to OpenClaw-style agents, with execution harness constraints and dynamic benchmarks.

## Core thesis

Do not treat memory as "add a vector database". A self-improving agent needs four coupled subsystems:

1. Layered memory: what to remember, retrieve, inject, update, expire, and audit.
2. Harness runtime: make execution a constrained, observable state machine instead of free-form chat.
3. Case-to-capability pipeline: convert production bad cases into root causes, generalized patterns, fixes, and regression tests.
4. Dynamic benchmark: measure whether each memory/skill/tool/harness update actually improves capability without regressions.

Loop:

```text
production task / bad case
→ trace + evidence
→ root-cause taxonomy
→ memory / skill / tool / prompt / harness patch
→ generalized + synthetic benchmark items
→ train/dev/holdout regression
→ canary/shadow rollout
→ production feedback
```

## Memory architecture

Recommended layers:

- Working memory: current task goal, plan, observations, verification state. Ephemeral by default.
- Episodic memory: historical sessions, tool traces, decisions, outcomes. Retrieved on demand, not always injected.
- Semantic memory: stable facts, user preferences, project conventions, environment facts. Requires write gate.
- Procedural memory: reusable workflows/skills/SOPs. Workflows belong here, not in generic memory.
- Case memory: production failures, root causes, fixes, generalizations, linked benchmarks.
- Benchmark memory: dynamic eval items, splits, pass/fail history, cost, regressions.

Memory write gate:

- Save only durable, future-useful facts or procedures.
- Do not save WIP, temporary task progress, raw logs, or stale session-local state.
- Require scope: global/user/project/workspace/task.
- Track evidence, confidence, expiry/staleness, usage, and status.

## Harness runtime architecture

Harness should enforce the agent loop:

```text
Observe → Plan → Act → Verify → Reflect → Decide next
```

Core modules:

- Loop engine: controls step sequencing.
- Context manager: selects, compresses, orders, and redacts memory for prompt injection.
- Tool registry: capability, schema, side-effect level, retry, verification requirement.
- Permission/safety layer: side-effect gating and evidence capture.
- State machine: created → classified → planned → executing → verifying → completed/reflected, with blocked/diagnosed/fallback/escalated failure states.
- Verification gate: task-specific checks before completion.
- Reflection gate: after success/failure, propose memory/skill/harness/benchmark updates.
- Subagent manager: planner, executor, critic, verifier, synthesizer, arbiter.
- Lifecycle hooks: before/after task, tool, side-effect, memory write, and benchmark regression events.

## Bad-case taxonomy

Classify failures before fixing:

- Memory failure: missing preference, stale memory, wrong retrieval, project collision, temporary state saved as fact.
- Planning failure: bad decomposition, wrong order, dependency omitted, premature action.
- Tool-use failure: tool not called, wrong tool, wrong args, no retry, no verification.
- Context failure: key info compressed away, too much noise, wrong injection order.
- Verification failure: no tests/build/browser/API/schema check, trusted model output without evidence.
- Safety failure: uncontrolled side effect, permission gap, leakage.
- Capability failure: missing tool/skill/model capability; may justify training only after repeated evidence.

For each bad case generate:

- original reproduction test
- 3–5 same-family generalized tests
- at least one holdout variant not exposed to the agent prompt/skill

Fix priority:

1. Harness constraint if a rule can prevent the class.
2. Skill/procedural memory update if a workflow was missing.
3. Semantic memory update if a durable fact was missing.
4. Tool improvement if capability/schema/retry/verification was missing.
5. Prompt update for global defaults.
6. Model training/fine-tuning only for repeated capability failures.

## Dynamic benchmark design

Benchmark suites:

- Memory: preference recall, stale-memory rejection, project isolation, session retrieval.
- Tool-use: correct tool choice, parameter correctness, retry/fallback, side-effect control.
- Planning: decomposition, dependency ordering, risk handling.
- Verification: test/build/browser/API/schema evidence.
- Bad-case regression: previous production failures.
- Long-horizon: multi-step, multi-tool, multi-context tasks.

Splits:

- train-like: can inform reflection, prompt, skill, tool, or harness updates.
- dev: used to judge the current update.
- holdout: never injected into prompts/skills/training; only aggregate scores are visible.
- shadow production: real task replay/parallel eval without affecting user outcome.

Key metrics:

- Self-evolution efficiency = ΔBenchmarkScore / EvolutionCost.
- Bad-case fix rate.
- Generalization gain.
- Regression rate.
- Memory precision/recall/staleness.
- Tool-use correctness.
- Verification coverage.
- First-pass success rate.
- Human intervention rate.
- Capability half-life.

## Core papers to cite

Memory / agent architecture:

- MemGPT: Towards LLMs as Operating Systems, 2023 — https://arxiv.org/abs/2310.08560
- Generative Agents: Interactive Simulacra of Human Behavior, 2023 — https://arxiv.org/abs/2304.03442
- MemoryBank: Enhancing Large Language Models with Long-Term Memory, 2023 — https://arxiv.org/abs/2305.10250
- Cognitive Architectures for Language Agents, 2023 — https://arxiv.org/abs/2309.02427
- Voyager: An Open-Ended Embodied Agent with Large Language Models, 2023 — https://arxiv.org/abs/2305.16291

Execution / reflection / tool use:

- ReAct: Synergizing Reasoning and Acting in Language Models, 2022 — https://arxiv.org/abs/2210.03629
- Reflexion: Language Agents with Verbal Reinforcement Learning, 2023 — https://arxiv.org/abs/2303.11366
- Self-Refine: Iterative Refinement with Self-Feedback, 2023 — https://arxiv.org/abs/2303.17651
- Language Agent Tree Search, 2023 — https://arxiv.org/abs/2310.04406
- Toolformer: Language Models Can Teach Themselves to Use Tools, 2023 — https://arxiv.org/abs/2302.04761

Benchmarks:

- SWE-bench: Can Language Models Resolve Real-World GitHub Issues?, 2023 — https://arxiv.org/abs/2310.06770
- AgentBench: Evaluating LLMs as Agents, 2023 — https://arxiv.org/abs/2308.03688
- ToolLLM / ToolBench: Facilitating Large Language Models to Master 16000+ Real-world APIs, 2023 — https://arxiv.org/abs/2307.16789
- WebArena: A Realistic Web Environment for Building Autonomous Agents, 2023 — https://arxiv.org/abs/2307.13854
- LiveCodeBench: Holistic and Contamination Free Evaluation of Large Language Models for Code, 2024 — https://arxiv.org/abs/2403.07974

## MVP rollout

1. Week 1: memory schema, write gate, retrieval/injection policy, audit.
2. Week 2: task harness state machine, tool registry, permission and verification gates.
3. Week 3: bad-case schema, root-cause classification, regression item generation.
4. Week 4: benchmark registry/runner, daily regression, score dashboard.
5. Later: multi-model planner/executor/critic/verifier/synthesizer/arbiter with evidence gates.
