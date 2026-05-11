---
title: "采纳 GenericAgent 三大模式"
priority: P1
lane: evolution
status: pending
created_at: 2026-05-11T01:30:00+08:00
ratification: 4_model_certified
source: https://github.com/lsdefine/GenericAgent
---

# 采纳 GenericAgent 三大模式

## 多模型认证: 4/4 通过

## 模式 1: 5 层记忆密度分层

参照 GenericAgent L0-L4:
- L0 元规则: memory_management_sop.md (何时写记忆)
- L1 索引: ≤30行, 场景→知识路由索引
- L2 事实: 稳定环境事实/配置
- L3 技能: 可复用workflow/SOP/脚本
- L4 存档: 压缩历史session

映射到 Hermes:
- L0: memory rules (已有, 需强化)
- L1: 索引待建 (当前 MEMORY.md 充当)
- L2: config/ + environment/ (已有)
- L3: skills/ + scripts/ (已有)
- L4: session_search + archive (已有)

## 模式 2: 任务后 SOP/Skill 结晶

每个任务完成后:
1. 提取执行路径中的关键决策
2. 识别可复用的模式
3. 自动生成/更新 skill 文件
4. 关联到 memory 中

实现: envelope_executor DONE 后触发结晶流程

## 模式 3: 文件 IPC 子代理

参照 GenericAgent:
- input.txt → worker → output.txt → supervisor
- _stop / _keyinfo / _intervene 干预文件
- 零共享状态, 完全可调试

映射到 Hermes:
- delegate_task 已有隔离 context
- 需要添加: 文件-based handoff artifact
- 需要添加: 干预文件机制

## 验证标准
- [ ] L1 索引层建立 (≤30行路由)
- [ ] 至少 1 个任务产出 skill 结晶
- [ ] 文件IPC子代理原型可用
- [ ] 4/4 模型认证
