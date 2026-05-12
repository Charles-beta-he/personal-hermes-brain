---
type: playbook
layer: L4
status: active
created: 2026-05-06T18:29:31+08:00
concepts: [cybernetic multi-model intervention, first-order gate, second-order gate, observer]
---

# 一阶二阶控制论多模型介入 Playbook

## Core idea

cybernetic multi-model intervention = 用控制论组织多模型思考。

- First-order gate：控制 object task。
- Second-order gate：控制 observer/controller 本身。

## First-order gate

Use when the task is external to the agent: codebase, local brain folder, architecture decision, repo audit, API integration。

Steps:

1. Frame object task: what system is being controlled?
2. Collect source/tool evidence before asking models。
3. Run multi-model fanout to generate hypotheses, plans, risks, experiments。
4. Convert model output into issue ledger。
5. Execute deterministic verification: file read, build/test, brainctl search, source evidence, API response。
6. Accept only claims with tool evidence。

Pass criteria:

- tool evidence exists。
- issue ledger has no unresolved severity>=4。
- model agreement is not evidence is explicitly enforced。

Fail criteria:

- only model agreement supports the claim。
- evidence request is unanswered。
- deterministic gate fails。

## Second-order gate

Use when the agent itself is part of the controlled system: skill selection, route choice, memory write, self-check, eval rule, cron, multi-model judge。

Steps:

1. Identify observer/controller: model router, skill trigger, memory policy, verifier, P10/P9 frame。
2. Ask: what did the observer assume?
3. Audit audit rules: are verification criteria stable, stale, circular, or self-serving?
4. Audit route choice: did quorum/model selection omit important variety?
5. Audit memory: could this create ghost context?
6. Audit certification: did timeout/dissent become fake approval?
7. Record not_certified / dissent / timeout honestly。

Pass criteria:

- second-order self-audit is recorded。
- timeout/dissent caveat is present when applicable。
- observer assumptions are visible。
- verification rule itself is checkable。

Fail criteria:

- self-check only praises outcome。
- no audit of audit rules。
- no record of model/router limitations。

## Combined double-loop protocol

```text
Outer loop: Object task control
  evidence -> multi-model hypotheses -> implementation -> deterministic verification

Inner loop: Observer control
  inspect route/skill/memory/verifier -> issue ledger -> self-check -> caveat/provenance
```

## Output routing

- Source evidence: `02-证据与原文/evidence/` or original project files。
- Stable concepts: `04-知识原子/atoms/`。
- Strategy/project: `05-实践与项目/projects/`。
- Proof ledger: `05-实践与项目/tasks/`。
- Multi-model provenance: `06-治理与评审/reviews/`。

## Stop condition

Do not stop until:

```bash
python3 ~/.hermes/scripts/cybernetic_multimodel_selfcheck.py --json
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "cybernetic multi-model intervention first-order second-order observer" --limit 8
```

All must pass or produce recorded caveats。

## 中文检索别名

一阶控制论 二阶控制论 多模型介入 控制论 多模型 观察者 自观察 审计规则 证据门
