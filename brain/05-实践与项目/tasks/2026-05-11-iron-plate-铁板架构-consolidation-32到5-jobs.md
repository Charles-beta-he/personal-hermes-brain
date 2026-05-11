---
title: "铁板架构: 32→5 cron jobs 整合"
priority: P1
lane: work
status: pending
created_at: 2026-05-11T01:30:00+08:00
ratification: 4_model_certified (Claude+GPT+DeepSeek+MiMo)
source: complex-giant-systems + GenericAgent analysis
---

# 铁板架构: 32→5 Cron Jobs 整合

## 多模型认证: 4/4 通过

## 目标
将 32 个独立 cron job 整合为 5 层统一调度，消除冗余，补齐缺口。

## 5 层架构

### Layer 1: Ops (every 30min)
整合: pipeline_tick + controller + executor + bridge + orchestrator selfcheck
脚本: iron_plate_ops.py --tick
消除: R1 (orchestrator selfcheck 重复)

### Layer 2: Health (every 6h)
整合: V(x) + self-scan + smoke + usage + memory selfcheck
脚本: iron_plate_health.py
消除: R2 (进化监控重叠), R4 (smoke重叠)

### Layer 3: Evolve (daily 02:00)
整合: skill-steward + self-improvement + pa-evolution + failure-taxonomy + planner-triage
脚本: iron_plate_evolve.py
消除: R3 (失败分析重叠), G8 (PA进化孤立)

### Layer 4: Watchdog (every 10min)
整合: cron-health + missed-run + trace-ratio + dead-man-switch
脚本: iron_plate_watchdog.py
补齐: G3 (dead man's switch)

### Layer 5: Report (daily 08:00)
整合: daily-digest + GC + eval-audit + canary
脚本: iron_plate_report.py
补齐: G2 (集中仪表盘), G10 (统一日志)

## 需修复
- G1: 6个job的script参数空格bug → wrapper脚本
- G5: 依赖排序 (Layer 1 先于 Layer 2)
- G7: retry/escalation (失败自动重试)
- G6: model规格统一

## 从 GenericAgent 采纳
1. 5层记忆密度分层 (L0-L4)
2. 任务后SOP/skill结晶
3. 文件IPC子代理隔离

## 验证标准
- [ ] 32→5 cron jobs
- [ ] 0 冗余
- [ ] 0 报错
- [ ] V(x) >= 0.95
- [ ] 4/4 模型认证
