---
title: 系统工程四环Agent映射
created: 2026-05-08
type: atom
concepts: [Qian Xuesen, systems engineering, feedback loop, human-machine integration, agent architecture]
source_boundary: reconstructed_from_domain_knowledge_not_verbatim_quote
status: current
---

# 系统工程四环Agent映射

## 概念边界

此卡不是《论系统工程》逐字摘录，而是将钱学森系统工程思想中的常见核心原则重构为 Agent 控制面：总体设计、系统分解、综合集成、人机结合、反馈闭环、定性到定量、知识沉淀。

## 四环

### 1. 目标/总体设计环

- 问题：Agent 容易直接执行，缺少 north star。
- 落点：P10、Project Workpad、Non-goals、Red Lines。

### 2. 分解/协调环

- 问题：skills 很多但缺少语义调度。
- 落点：Skill Route Matrix、P9 task tree、domain workflow。

### 3. 反馈/验证环

- 问题：会话中觉得完成，但缺少可复现验收。
- 落点：build/test/browser-harness/Playwright/truth gate/evidence ledger。

### 4. 综合/沉淀环

- 问题：经验散落在会话压缩里，下次无法准确复用。
- 落点：brain atoms/templates/playbooks/project workpad/skill patch。

## 反模式

- 把项目状态写入全局 memory。
- 用多模型同意代替工具证据。
- 只建目录不填内容。
- 只写计划不写验收脚本。
- 只解决当前 bug，不沉淀闭环标准。
