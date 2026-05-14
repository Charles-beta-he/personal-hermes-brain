---
name: post-deploy-verification
description: Use when the task falls under Post-Deploy Verification — 部署后验证.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - deployment
    - verification
    - monitoring
    - qa
    - post-deploy
    related_skills:
    - software-development
---

# Post-Deploy Verification — 部署后验证

## Overview

上线不是终点，验证通过才是。. In practice, load it when the task falls under Post-Deploy Verification — 部署后验证. It defines the expected execution lane, scope boundaries, and verification shape for this class of work.
## When to Use

- 代码部署到生产/预发布环境后
- CI/CD pipeline 的部署阶段完成后
- 热修复/回滚后
- Don't use for: requests that do not need the task falls under Post-Deploy Verification — 部署后验证; choose a more specific child skill or a broader routing skill that actually matches the task.
## 验证清单

### 1. 构建验证

```bash
# Cloudflare Pages
npx wrangler pages deployment list --project-name <project>
# 确认最新部署状态为 Success
```

### 2. 线上功能验证

使用 browser 工具访问生产环境：

```
1. browser_navigate 到生产 URL
2. browser_vision 截图检查首页是否正常渲染
3. browser_console 检查 JS 错误
4. 测试核心用户链路（登录 → 主要功能 → 退出）
```

### 3. 性能基线检查

```bash
# Lighthouse CI (如配置)
npx lighthouse <url> --only-categories=performance,accessibility,best-practices,seo
```

### 4. 关键指标确认

- [ ] 页面加载时间 < 3s
- [ ] 无 JS 报错
- [ ] 核心 API 响应正常
- [ ] 移动端显示正常

### 5. 回滚准备

确认可以快速回滚：

```bash
# Cloudflare Pages
npx wrangler pages deployment list --project-name <project>
# 记录上一个稳定版本的 deployment ID
```

## 输出物

部署验证完成后，产出 `.claude/deploy-verification/{timestamp}.md`：

```markdown
# 部署验证报告 — [版本号]

## 部署信息
- 版本: [ ]
- 环境: [production/staging]
- 部署时间: [ ]

## 验证结果
- [ ] 构建成功
- [ ] 首页渲染正常
- [ ] 控制台无报错
- [ ] 核心链路通过
- [ ] 移动端正常

## 发现的问题
- [ ] 无 / [列表]

## 回滚方案
- 上一个稳定版本: [deployment ID]
- 回滚命令: [ ]
```

## 失败处理

如果验证失败：
1. 立即评估影响范围
2. 决定是否回滚
3. 通知相关人员
4. 记录问题并创建修复任务

## 与 semantic-release 集成

semantic-release 发布新版本后自动触发：
- GitHub Actions 中添加上线验证步骤
- 验证失败时阻止发布完成标记

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

