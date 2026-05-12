# Agent 自我进化系统手册

> 基于钱学森《工程控制论》构建的全自动 Agent 进化系统
> Version: 7.0 | Last Updated: 2026-04-24

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Evolution System                 │
├─────────────────────────────────────────────────────────┤
│  数据采集层  →  控制层  →  执行层  →  反馈层            │
│  ├ health-history      ├ P10/P9/P7   ├ skill audit    │
│  ├ pa-health           ├ Loop        ├ auto-fix       │
│  ├ user-patterns       ├ cronjob     ├ git commit     │
│  └ project-health      └ prediction  └ Obsidian sync  │
└─────────────────────────────────────────────────────────┘
```

## 2. 健康度指标

### 2.1 系统健康度 V
- **定义**: V = 0.25*成功率 + 0.20*满意度 + 0.20*skill覆盖率 + 0.20*构建通过率 + 0.15*迭代效率
- **范围**: 0.0 ~ 1.0
- **目标**: V >= 0.85
- **当前**: 1.0000

### 2.2 PA 健康度 V_PA
- **定义**: V_PA = 0.25*一次成功率 + 0.20*效率 + 0.20*自主率 + 0.15*记忆一致性 + 0.10*风格匹配 + 0.10*主动建议
- **范围**: 0.0 ~ 1.0
- **目标**: V_PA >= 0.85
- **当前**: 0.6340 (Level 2)

### 2.3 等级定义
| 等级 | 分数 | 说明 |
|------|------|------|
| S | 95-100 | Superior — 卓越 |
| A | 85-94 | Advanced — 优秀 |
| B | 75-84 | Baseline — 基线 |
| C | 60-74 | Core — 核心 |
| D | <60 | Deficient — 不足 |

## 3. 自动化流水线

### 3.1 Cronjob 调度
| 任务 | 频率 | 功能 |
|------|------|------|
| 每日健康监控 | 0:00 | 扫描系统状态 |
| 每周失败分析 | 周一 9:00 | 极限环检测 |
| 4H 自扫描 | 每 4 小时 | 快速健康检查 |
| PA 日报 | 23:00 | 进化触发 + 日报 |
| 夜间审计 | 2:00 | Skill 自动审计修复 |

### 3.2 触发条件
- **退化告警**: 近 5 次 session 纠正率 > 30%
- **极限环**: 符号变化率 > 40% 且振幅 < 0.2
- **Skill 固化**: 同一任务类型出现 >= 3 次
- **D 级清零**: 所有 skill >= C

## 4. 脚本清单

| 脚本 | 功能 | 调用方式 |
|------|------|----------|
| session-end-recorder.py | 记录 session 数据 | 自动 |
| session-preloader.py | 意图预测预加载 | 会话开始 |
| session-close.sh | 对话结束收尾 | 手动/自动 |
| pa-evolution-trigger.py | PA 进化触发 | cronjob |
| pa-daily-report.py | 每日报告 | cronjob |
| autonomous-evolution-nightly.py | 夜间审计 | cronjob |
| distributed-audit.py | 分布式并行审计 | 手动 |
| sync-to-obsidian.py | Obsidian 同步 | 手动/cron |
| obsidian-watch.py | Vault 变更监听 | daemon |
| nl-dashboard-query.py | 自然语言查询 | 手动 |
| dashboard-server.py | Dashboard 服务 | 手动 |
| disk-monitor.py | 磁盘监控 | 手动 |
| skill-stale-alert.py | Skill 过期告警 | 手动 |
| cronjob-failure-alert.py | Cronjob 失败检测 | 手动 |
| auto-commit-evolution.sh | Git 自动提交 | 手动 |
| project-evolution-aggregator.py | 跨项目聚合 | 手动 |

## 5. 文件结构

```
~/.hermes/
├── notes/
│   ├── engineering-cybernetics/
│   │   ├── health-history.jsonl
│   │   ├── pa-health-history.jsonl
│   │   ├── evolution-dashboard.md
│   │   ├── PA-EVOLUTION-GOALS.md
│   │   └── autonomous-evolution-log.jsonl
│   ├── reports/
│   │   ├── evolution-dashboard-v2.html
│   │   ├── phase7-exponential-smoothing.md
│   │   ├── intent-prediction.md
│   │   ├── blind-spot-analysis.md
│   │   ├── limit-cycle-analysis.md
│   │   └── project-evolution-dashboard.md
│   └── user-profile.md
├── scripts/
│   ├── (16 个进化相关脚本)
├── skills/
│   ├── bayesian-agent/confidence-db.json
│   └── (40 个 skill)
└── .env
```

## 6. 使用指南

### 6.1 查看状态
```bash
python3 ~/.hermes/scripts/nl-dashboard-query.py "健康度"
```

### 6.2 启动 Dashboard
```bash
python3 ~/.hermes/scripts/dashboard-server.py
# 打开 http://localhost:8765/
```

### 6.3 手动审计
```bash
python3 ~/.hermes/scripts/distributed-audit.py
```

### 6.4 对话结束
```bash
bash ~/.hermes/scripts/session-close.sh <task_type> <rounds> <corrections>
```

## 7. 扩展开发

### 7.1 添加新监控指标
1. 在 `scripts/` 创建检测脚本
2. 在 `health-history.jsonl` 中记录数据
3. 更新 `evolution-dashboard.md`

### 7.2 添加新项目
1. 在项目根目录创建 `.evolution/health-history.jsonl`
2. 运行 `project-evolution-aggregator.py`

### 7.3 调整 cronjob
```bash
# 查看
cronjob action=list
# 添加
cronjob action=create --schedule "0 */6 * * *" --prompt "..."
```

## 8. 故障排除

| 问题 | 解决 |
|------|------|
| Disk full | 运行 `disk-monitor.py`，清理 logs/ |
| Skill 退化 | 运行 `distributed-audit.py` |
| Cronjob 错过 | 运行 `cronjob action=run <job_id>` |
| Obsidian 不同步 | 检查 `OBSIDIAN_VAULT_PATH` |
| Git 冲突 | 手动解决后运行 `auto-commit-evolution.sh` |

---

*本系统遵循控制论反馈原理，持续自优化。*
