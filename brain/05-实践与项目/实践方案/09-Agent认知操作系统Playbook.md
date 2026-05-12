---
type: playbook
status: active
created: 2026-05-07T00:05:39+08:00
concepts: [agent-cos-playbook, pua-loop, local-brain-selfcheck]
---

# 09 - Agent 认知操作系统 Playbook

## Loop Protocol

每轮 PUA-loop 执行：

1. Observe：运行 `brainctl status`、读取 COS matrix、运行 `agent_cos_selfcheck.py --json`。
2. Orient：定位 `missing_pairs`、`below_a_plus`、`missing_domains`、`missing_files`。
3. Decide：只补 deterministic self-check 报出的 gap；若 gap 涉及 P10/canonical 规则，走 T3 多模型；否则 T0/T1/T2。
4. Act：写入 project/playbook/atom/review/task/evolution/dashboard 中的最小闭环 artifact。
5. Verify：`brainctl sync`、`brainctl reindex`、中英文 `brainctl search`、`local_brain_exhaustive_audit.py`、`agent_cos_selfcheck.py`。
6. Commit：若 `~/.hermes` 有 scoped brain mirror/script 变更，做本地 commit，不 push。

## Completion Gate

只有以下全过才能说 LOOP_DONE：

```bash
python3 ~/.hermes/scripts/agent_cos_selfcheck.py --json
python3 ~/.hermes/scripts/local_brain_exhaustive_audit.py
python3 ~/.hermes/scripts/brainctl.py --json search "Agent认知操作系统互补矩阵 无缺失配对 跨学科配对总表 全部A+" --limit 8
python3 ~/.hermes/scripts/brainctl.py --json search "cognitive operating system complementary matrix interdisciplinary A+ local brain selfcheck" --limit 8
```

## Anti-patterns

- 把历史 `A-`/`B+` 理论表强行改成“理论本身 A+”，但没有工具证据。
- 因为四个模型都同意就跳过本地审计。
- 为了“完整”重写主层级，破坏人类导航合同。
- 矩阵行数很多但没有 `missing_pairs=0` / `below_a_plus=0` 可解析契约。

## Search Aliases

PUA loop Agent COS 本地大脑自检 互补矩阵 A+ 配对 验证闭环 sync reindex search structural audit

## Ratification-first execution protocol (2026-05-07T00:54:55+08:00)

1. Run deterministic evidence gates: `agent_cos_selfcheck.py`, local brain audit, targeted search, tests.
2. Build top-level claims/evidence bundle with explicit `supports` links for every severity>=3 claim.
3. Run multi-model discussion against the evidence bundle.
4. Run `ratification_gate.py --discussion-result <scoped discussion_result.json>`.
5. Only if the gate passes may dashboard `final_integration_status` move to `FULLY_CERTIFIED`.
6. Timeout, SIGTERM, missing artifact, weak consensus, unsupported claims, or unresolved severity>=3 issues must remain `LOCAL_COMPLETE_UNRATIFIED` / `NOT_CERTIFIED_*`.
