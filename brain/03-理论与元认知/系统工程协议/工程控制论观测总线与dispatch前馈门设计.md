---
title: 工程控制论观测总线与 dispatch 前馈门设计 v1
created: 2026-05-19
status: design-v1-warn-only
capability_delta: cybernetic_control_plane_v1
related:
  - brain/03-理论与元认知/钱学森核心著作系统吸收索引.md
  - hermes/scripts/cybernetic_control_plane.py
---

# 工程控制论观测总线与 dispatch 前馈门设计 v1

## 目标

把《工程控制论》的反馈/前馈思想落到 Hermes 多脑任务池，但第一阶段只做 warn-only，不引入新的硬阻塞。

## 控制环

1. 观测：读取任务 note、协议字段、handback 字段、source/evidence 字段。
2. 过滤：把噪声型文本与结构化风险分开，避免把“运行时表述”误判为阻塞。
3. 前馈：dispatch 前给出风险 warning：source 缺失、dev handback 缺失、模型意见替代证据、隐藏硬阻塞。
4. 执行：warn-only；`blocks_dispatch=false`。
5. 反馈：完成后由 proof/selfcheck/evidence-spine 复核，决定是否升级为治理规则。

## 风险分类

| signal | 含义 | 初始权重 | 动作 |
|---|---|---:|---|
| missing_acceptance_evidence | 缺少验收证据字段 | 2 | 提醒补齐 |
| model_only_truth_risk | 多模型意见被当事实 | 3 | 要求 source_packet/falsifier |
| dev_boundary_risk | dev 任务缺 handback/return_to_brain | 2 | 要求交还契约 |
| hard_gate_risk | 可能出现未批准硬阻塞 | 3 | 保持 warn-only 并升级复核 |
| runtime_surface | 涉及 dispatch/taskpool/autorun | 1 | 增加保守提示 |

## 参考实现

`hermes/scripts/cybernetic_control_plane.py --demo --json`

示例验收：高风险输入应输出 `risk_level=high` 且 `blocks_dispatch=false`。

## 推进边界

- Gate2 只证明可观测、可分类、不会误阻塞。
- 后续如要接入 `dispatch-dry-run`，必须单独任务和回归测试。
- 不允许直接把 warning 变成 hard gate，除非 main ratification + regression proof 通过。
