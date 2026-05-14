---
name: stuck-diagnosis
description: Use when the task falls under 卡顿诊断三板斧.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - diagnosis
    - debug
    - gateway
    - troubleshooting
    related_skills:
    - hermes-agent
    - hermes-workflow-orchestrator
---

# 卡顿诊断三板斧

## Overview


> 标准化排查流程，避免"卡住了不知道怎么查"

## When to Use

- The task falls under 卡顿诊断三板斧

## Trigger

- Agent 卡住不动、响应慢、工具调用无返回
- 用户说"怎么不动了"、"卡住了"、"又超时了"

## Steps

### 1. 开日志

```bash
# 打开最详细的日志级别
/verbose all

# 在另一个终端看实时日志
tail -f ~/.hermes/logs/agent.log
tail -f ~/.hermes/logs/errors.log
# 如果运行 gateway
tail -f ~/.hermes/logs/gateway.log
```

### 2. 复现问题

- 用最简 prompt 复现卡顿
- 观察日志输出位置 — 是 waiting API? 工具 hang? 上下文溢出?

### 3. 打包诊断包

```bash
# 自动打包日志 + 配置 + 环境信息
hermes debug share
```

输出路径: `~/.hermes/hermes-agent/debug-*.tar.gz`

### 4. 检查 Cron 调度器 / Gateway

**Cron 全部未执行 (last_run_at 全 null)**:
```bash
# 1. 确认 scheduler 状态
hermes cron status

# 2. 检查 cron_mode (必须是 approve, 不是 deny)
grep cron_mode ~/.hermes/config.yaml

# 3. 检查 gateway
hermes gateway status

# 4. 安装/启动 gateway (如未运行)
hermes gateway install

# 注意: hermes cron tick 会跑全部到期 job, 可能超时
# 优先走自动调度而非手动 tick
```

**Gateway 超时**:

```yaml
# config.yaml 检查点:
gateway:
  timeout: 300           # 单次请求超时（默认 300s）
  notify_interval: 60    # 进度通知间隔
  session_reset:
    timeout: 1200        # 会话总超时
```

如果 timeouts 太小 → 改大

### 5. 检查上下文压缩

```yaml
# config.yaml 检查点:
compression:
  enabled: true
  threshold: 0.6         # 60% 上下文占用时压缩
  protect_last_n: 30     # 保留最近 30 条
```

## Common Pitfalls

- **不要**在卡顿时发多个请求 — 可能加剧拥堵
- 日志级别恢复: `/verbose default`
- debug share 可能包含敏感信息（API key），检查后再分享
- **"Script not found" 实际是超时**: Cron 报 `Script not found` 但文件存在时，通常是脚本内部阻塞（如 `hermes chat -q` 调用 300-600s timeout），cron runner 在超时后错误报告为"not found"。验证方法：`ls -la /path/to/script` + 单独跑 script 的 status 子命令。参见 `hermes-workflow-orchestrator` skill 的 `references/agent-team-controller-timeout-pattern.md`。
- **status 子命令 vs cycle 子命令**: 很多 orchestrator 脚本有快速只读命令（status/list/dashboard）和慢速写命令（cycle/dispatch/execute）。Cron 监控应该用 status，执行应该拆分成 fast claim + background execute 两阶段。
1. Skipping prerequisite checks and assuming the environment already matches the workflow.
2. Applying the workflow mechanically without confirming that the request still matches this skill's trigger class.
3. Reporting success before reading back the actual outputs, files, or external side-effects.
## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

