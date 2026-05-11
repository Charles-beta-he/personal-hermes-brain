# 监控盲区分析与自动填补报告

生成时间: 2026-04-24T12:59:28.236309

## 发现的盲区

### 1. 磁盘空间
- **原因**: health-history.jsonl 持续增长，可能占满磁盘
- **解决方案**: disk-monitor.py: 监控 ~/.hermes/ 目录大小，超过 100MB 告警

### 2. Cronjob 失败
- **原因**: cronjob 错过执行后只在 dashboard 显示，无主动告警
- **解决方案**: cronjob-failure-alert.py: 扫描 cronjob 日志，发现失败时发送通知

### 3. Skill 过期
- **原因**: skill 长期未审计可能退化，但只在 nightly 处理一个
- **解决方案**: skill-stale-alert.py: 发现超过 7 天未审计的 skill 时告警

## 自动生成的监控脚本

| 脚本 | 功能 |
|------|------|
| disk-monitor.py | 监控磁盘空间 |
| cronjob-failure-alert.py | 监控 cronjob 失败 |
| skill-stale-alert.py | 监控 skill 过期 |

## 下一步

将这些脚本加入 cronjob，完成监控闭环。
