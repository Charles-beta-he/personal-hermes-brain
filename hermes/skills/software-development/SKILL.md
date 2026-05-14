---
name: software-development
description: Use when you need guidance on meta-skill for software development workflows.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - software
    - development
    - umbrella
    - routing
    related_skills:
    - agent-team-parallel
    - arc-dispatch-executor
    - architecture-optimization-loop
    - auto-optimize-loop
    - browser-harness-integration
    - code-simplifier
---

# Software Development — 软件开发工作流集合

## Overview

This umbrella skill is the routing surface for software development — 软件开发工作流集合. Use it to choose the most specific child skill, reference, or workflow instead of treating the category name as a one-size-fits-all procedure.

## When to Use

- You need help somewhere inside software development — 软件开发工作流集合 and want the quickest route to the right child skill.
- You are not yet sure which software development — 软件开发工作流集合 sub-workflow best matches the request.
- You want a compact map of the software development — 软件开发工作流集合 skill family before loading a more specific procedure.
- Don't use for: a request that already clearly matches one specific software development — 软件开发工作流集合 child skill; load that child skill directly.

## Routing Guide

- `agent-team-parallel` — the task falls under Agent Team Parallel — 并行任务执行控制器.
- `arc-dispatch-executor` — the task falls under arc-dispatch 任务执行规范.
- `architecture-optimization-loop` — you need guidance on p9/P10/Loop architecture optimization workflow - systematic iterative improvement with management layers.
- `auto-optimize-loop` — you need guidance on execute self-contained optimization loops on a codebase — scan for issues, generate proposals, prune risky ones, execute safe changes, commit per round, and re....
- `browser-harness-integration` — you need guidance on integrate comprehensive browser-based verification into automated task pipelines - combines dogfood testing, visual regression, and UIMax audit with project-ty....
- `code-simplifier` — you need guidance on merge duplicate logic and perform safe refactoring with risk assessment.
- `color-contrast-checker` — the task falls under Color Contrast Checker — WCAG 文字对比度自动验证.
- `debugging-hermes-tui-commands` — you need to debug Hermes TUI slash commands: Python, gateway, Ink UI.
- `hermes-agent-skill-authoring` — creating, rehabilitating, or structurally improving Hermes SKILL.md files, including trigger design, frontmatter normalization, mode selection, and peer-shape validation.
- `hermes-warning-governance` — Hermes p10-health, cron, memory, or skill-count warnings persist but may be stale/noisy. Safely distinguish true defects from ghost memory and governed large-skill-library false po....
- `hermes-workflow-orchestrator` — the task falls under Hermes Workflow Orchestrator.
- `incident-response` — production issues are detected: errors, outages, data corruption, performance degradation.
- `lark-task-reading` — adding, debugging, or operating Lark task collection.
- `mcp-server-from-scratch` — the task falls under MCP Server From Scratch.
- `multi-agent-code-review` — the task falls under Multi-Agent Parallel Code Review with Confidence Filtering.
- `multi-model-agent-orchestration` — you need guidance on multi-model agent orchestration patterns inspired by rowboatlabs/rowboat — event-sourced runs, agent-as-sub-flow, model-per-agent, lazy skill loading, knowledg....
- `multi-model-architecture` — the task falls under Multi-Model Architecture — 多模型全栈架构.
- `multi-model-thinking` — a task needs true multi-model deliberation, cross-critique, evidence-linked ratification, or high-risk final certification rather than a single-model answer or a simple cross-check.
- `node-inspect-debugger` — you need to debug Node.js via --inspect + Chrome DevTools Protocol CLI.
- `plan` — you need to plan mode for Hermes — inspect context, write a markdown plan into the active workspace's `.hermes/plans/` directory, and do not execute the work.
- `planning-with-files` — a task is multi-step, may span context compressions, or needs cross-session persistence. Writes plans, progress, and decisions to files so they survive context window compression a....
- `post-deploy-verification` — the task falls under Post-Deploy Verification — 部署后验证.
- `post-update-patch-healing` — you need to create self-healing patches that survive `hermes update` (or any git-pull-based update).
- `private-fork-evolution-governance` — governing a private Hermes fork, recording evolution events, analyzing external projects for methodology migration, or verifying that local artifacts survive upstream upgrades.
- `python-debugpy` — you need to debug Python: pdb REPL + debugpy remote (DAP).
- `python-multiline-grep-engine` — you need to build a Python-native multiline grep engine to replace shell `grep -rn`.
- `react-architecture-migration` — you need to migrate React app from hardcoded mock data to production architecture: API client → Services → Zustand stores → Mock server.
- `requesting-code-review` — you need guidance on pre-commit verification pipeline — static security scan, baseline-aware quality gates, independent reviewer subagent, and auto-fix loop.
- `requirement-clarification` — a new task, feature request, or bug report arrives and you must clarify goals, acceptance criteria, scope, risks, and priorities before execution.
- `router` — selecting an execution route from historical route_outcomes data, task class, and e-greedy exploration/exploitation instead of routing ad hoc.
- `self-evolve-via-claude` — the task falls under Self-Evolve via Claude Code — 双脑自进化.
- `self-improvement-pipeline` — the task falls under Self-Improvement Pipeline — 自进化优先调度层 (L0-L5).
- `skill-ecosystem-diagnosis` — Use when: 'skill生态审计', '自检', '健康检查', '五大硬伤', '只能涨不能减', '系统熵增', 'ecosystem health', 'skill governance audit'.
- `skill-ecosystem-governance` — the task falls under Skill Ecosystem Governance — 技能生态系统治理.
- `skill-eval` — creating, updating, or auditing Hermes skills and you need to test trigger accuracy, behavior correctness, and regression risk with explicit eval cases.
- `spike` — you need guidance on throwaway experiments to validate an idea before build.
- `stuck-diagnosis` — the task falls under 卡顿诊断三板斧.
- `subagent-driven-development` — executing implementation plans with independent tasks. Dispatches fresh delegate_task per task with two-stage review (spec compliance then code quality).
- `systematic-debugging` — encountering any bug, test failure, or unexpected behavior. 4-phase root cause investigation — NO fixes without understanding the problem first.
- `test-driven-development` — implementing any feature or bugfix, before writing implementation code. Enforces RED-GREEN-REFACTOR cycle with test-first approach.
- `theory-driven-evolution` — you need guidance on study a theoretical framework (book, theory, system) and operationalize it into Agent self-evolution infrastructure: chapter-by-chapter notes, capability mappi....
- `uimax-audit` — you need guidance on uIMax — Systematic UI quality audit with A-F grading.
- `visual-regression` — the task falls under Visual Regression — browser_vision 截图 diff 对比.
- `workflow-ecosystem-audit` — asked to '梳理工作流', 'review workflow', 'skill gaps', '缺省流程', or when setting up a new project workspace.
- `writing-plans` — you have a spec or requirements for a multi-step task. Creates comprehensive implementation plans with bite-sized tasks, exact file paths, and complete code examples.

## Selection Rules

- Prefer the narrowest child skill that matches the user request, platform, and desired artifact.
- Stay at the umbrella level only for routing, taxonomy, or category-wide orientation.
- If the request spans multiple subskills, use this umbrella to map the lane first, then hand off to the specific workflow that will do the real work.

## References

- `references/fullstack-verification-workflow.md` — 前后端一体化项目的本地全栈验证工作流（验证脚本、失败分类、taskpool 集成、项目画像配置）

## Common Pitfalls

1. Using the software development — 软件开发工作流集合 umbrella as the full procedure even though a more specific child skill already fits.
2. Reading the routing map but never loading the referenced child skill or support material that contains the actual execution steps.
3. Choosing a child skill without checking that its platform, tools, and expected artifacts match the current task.

## Verification Checklist

- [ ] The request was mapped to the best-fitting child skill or explicitly kept at umbrella level for routing only.
- [ ] The selected child skill descriptions, references, and prerequisites were checked before substantive execution.
- [ ] Any claimed handoff, output, or route decision was read back against the specific child workflow before completion.

