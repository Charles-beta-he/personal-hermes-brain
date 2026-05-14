---
name: architecture-optimization-loop
description: Use when you need guidance on p9/P10/Loop architecture optimization workflow - systematic iterative improvement with management layers.
version: 1.0.0
author: Hermes Agent
license: MIT
triggers:
- 架构优化
- architecture
- p10 检查
- 迭代优化
metadata:
  hermes:
    tags:
    - software
    - development
    - architecture
    - optimization
    - loop
    related_skills:
    - software-development
---

# 架构优化 Loop 工作流

## Overview

三轮驱动的架构优化模式：P10 战略 → P9 执行 → UI 走查。. In practice, load it when you need guidance on p9/P10/Loop architecture optimization workflow - systematic iterative improvement with management layers. It defines the expected execution lane, scope boundaries, and verification shape for this class of work.
## When to Use

- 大规模代码重构
- 样式系统迁移（如 CSS-in-JS → Tailwind）
- 组件抽象层建设
- 性能优化系统性改造
- Don't use for: requests that do not need you need guidance on p9/P10/Loop architecture optimization workflow - systematic iterative improvement with management layers; choose a more specific child skill or a broader routing skill that actually matches the task.
## 工作流程

### 每轮迭代

```
P10 (战略审查)
  ↓ 发现问题，定义优先级
P9 (任务拆解 + 执行)
  ↓ 写 Task Prompt，P8 执行
UI 走查 (验证)
  ↓ 验证视觉一致性
提交 + 版本发布
```

### P10 审查维度

1. **代码架构** - 模块职责、依赖关系、重复代码
2. **技术栈** - 框架合理性、工具配置
3. **可扩展性** - 新功能接入成本
4. **开发体验** - 调试工具、文档

### P9 Task Prompt 六要素

```
## [任务标题]

### WHY - 为什么做
### WHAT - 交付物
### WHERE - 在哪里改
### HOW MUCH - 资源边界
### DONE - 完成定义
### DON'T - 禁区
```

## 实战案例：内联样式迁移

### 目标
将 CSS-in-JS 内联样式迁移到 Tailwind CSS 类

### 策略

1. **批量迁移** - 每轮迁移 3-5 个组件
2. **分类处理**
   - 颜色 → `text-theme-*`, `bg-theme-*`
   - 边框 → `border border-theme`
   - 布局 → Tailwind 工具类
3. **保留动态样式**
   - hover/click 处理器
   - 条件样式
   - color-mix() 值

### 迁移规则示例

```javascript
// Before
<div style={{ backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}>

// After
<div className="bg-theme-surface text-theme-primary">
```

### 验证清单

- [ ] pnpm test 通过
- [ ] pnpm build 成功
- [ ] 主题切换无闪烁
- [ ] 移动端显示正常

## 版本发布策略

使用 semantic-release 自动版本管理：

| 改动类型 | Commit 前缀 | 版本变化 |
|---------|------------|---------|
| 新功能 | `feat:` | minor |
| Bug 修复 | `fix:` | patch |
| 重构 | `refactor:` | patch |
| 文档 | `docs:` | 不变 |

## 成功指标

- 内联样式减少比例
- 组件重复代码减少比例
- 测试覆盖率
- 构建时间变化

## 注意事项

1. **不追求完美** - 80% 迁移即可，剩余动态样式合理保留
2. **小步快跑** - 每轮小改动，快速验证
3. **自动版本** - semantic-release 自动发布，不手动管理版本
4. **UI 走查** - 每轮必须验证视觉一致性

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

