---
name: incident-response
description: "事故响应与复盘 — 线上问题发现、止血、根因分析、修复、复盘的标准流程。Use when production issues are detected: errors, outages, data corruption, performance degradation."
license: MIT
tags: [incident, on-call, postmortem, reliability, sre]
---

# Incident Response — 事故响应与复盘

> 线上出问题不可怕，怕的是没有 SOP。止血要快，复盘要深。

## 响应阶段

### Phase 1: 发现与通报 (0-5 min)

- [ ] 确认问题真实存在（非误报）
- [ ] 评估影响范围（用户/功能/数据）
- [ ] 在 Lark/Slack 通报：问题现象 + 影响 + 正在处理

### Phase 2: 止血 (5-30 min)

**目标：先恢复服务，再查根因。**

可选止血手段（按优先级）：
1. 回滚到上一个稳定版本
2. 关闭故障功能开关
3. 降级到备用方案
4. 限流/熔断

```bash
# Cloudflare Pages 回滚示例
npx wrangler pages deployment list --project-name <project>
npx wrangler pages deployment tail --project-name <project> --deployment-id <stable-id>
```

### Phase 3: 根因分析

止血后，使用 systematic-debugging skill 进行根因分析：

1. 读取错误日志
2. 复现问题
3. 定位代码变更
4. 找到根本原因

### Phase 4: 修复与验证

- [ ] 编写修复代码
- [ ] 写回归测试
- [ ] 本地验证
- [ ] staging 验证
- [ ] 部署到生产
- [ ] 生产验证（使用 post-deploy-verification skill）

### Phase 5: 复盘

产出 `.claude/incidents/{date}-{issue}.md`：

```markdown
# 事故复盘 — [标题]

## 时间线
- 发现时间: [ ]
- 止血时间: [ ]
- 恢复时间: [ ]
- 总时长: [ ]

## 影响
- 影响用户: [ ]
- 影响功能: [ ]
- 数据影响: [ ]

## 根因
[5 Whys 分析]

## 止血措施
[做了什么来恢复]

## 改进措施
- [ ] 短期（本周）: [ ]
- [ ] 中期（本月）: [ ]
- [ ] 长期（本季）: [ ]

## 经验教训
[可复用的认知]
```

## 复盘四步法

1. **回顾目标**：当时要达成什么？
2. **评估结果**：实际发生了什么？差距在哪？
3. **分析原因**：为什么会出这个问题？
4. **沉淀规律**：下次怎么避免？产出 SOP 或工具改进。

## 与 PUA 体系的集成

- P10: 决定是否启动事故响应，分配 P9 负责
- P9: 协调 P8/P7 执行止血和修复
- P8/P7: 执行技术修复和回归测试

## 反模式

- ❌ 先查根因再止血——用户等不起
- ❌ 修复后不写回归测试——同样的问题会再来
- ❌ 不复盘——浪费了一次成长机会
- ❌ 复盘时追责——复盘是为了改进，不是批斗
