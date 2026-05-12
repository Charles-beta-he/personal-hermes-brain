# FDIR Degradation Strategy — 故障隔离、诊断与恢复

> ch15 可靠性: 出问题时降级 gracefully；故障隔离防止级联崩溃

## 故障等级

| 等级 | 症状 | 响应 | 降级策略 |
|------|------|------|---------|
| **L1 轻微** | 单次验证失败，其他正常 | 立即重试 | 同策略重试 1 次 |
| **L2 中度** | 同任务连续 2 次失败 | 切换策略 | 换 skill / 简化任务 |
| **L3 严重** | 同任务 3 次失败（极限环） | 暂停 + 告警 | 人工介入或 P10 战略 review |
| **L4 致命** | 核心系统故障（cron/mcp/memory） | 紧急模式 | 最小可用集运行 |

## 故障隔离

```
隔离原则:
  - 一个 skill 失败不波及其他 skill
  - 一个 session 失败不影响历史数据
  - 一个 cronjob 失败不阻塞其他 cronjob

实现:
  - 每个 skill 调用 try/except + fallback
  - session 数据写入前验证完整性
  - cronjob 独立调度，互不依赖
```

## 诊断流程

```
1. 收集症状
   - 错误类型 (syntax/logic/timeout/resource)
   - 影响范围 (单文件/多文件/全局)
   - 最近变更 (git diff)

2. 根因定位
   - 是否为新引入的变更？
   - 是否为环境问题？
   - 是否为 skill 本身缺陷？

3. 恢复决策
   - 可自动修复？→ 执行修复
   - 需人工决策？→ 暂停并通知
   - 需长期解决？→ 创建 GitHub issue
```

## 降级 gracefully

```
全功能不可用时的最小集:
  - terminal (命令执行)
  - read_file / write_file (文件操作)
  - memory (持久记忆)
  - todo (任务管理)

禁用:
  - 复杂 multi-skill 协作
  - 自动 cronjob 调度
  - browser 自动化
  - 视觉分析

恢复顺序:
  1. 修复核心依赖 (mcp, cronjob)
  2. 验证健康度脚本
  3. 逐步启用 Layer 1 技能
  4. 最后恢复 Layer 3-4 应用
```
