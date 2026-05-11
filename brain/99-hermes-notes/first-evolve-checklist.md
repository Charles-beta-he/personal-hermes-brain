# 今晚 03:00 首次双脑自进化 — 观察清单

首次运行最重要。以下是今晚要观察的 6 个关键点。

## 前置准备 (02:55)

```bash
# 清理上次的临时文件 (确保干净状态)
rm -f /tmp/hermes-state.json /tmp/hermes-state-full.json
rm -f /tmp/hermes-plan.json /tmp/hermes-plan.degraded
rm -f /tmp/hermes-last-snapshot /tmp/plan_local.txt

# 开两个终端:
# 终端1: 实时观察 evolve.log
tail -f ~/.hermes/logs/evolve.log

# 终端2: 看 cron 是否触发
watch -n 30 "hermes cron list | grep 双脑"
```

## 03:00 — 6 个观察点

### 1. self-describe.sh 能否顺利运行
```bash
# 检查 state.json
ls -la /tmp/hermes-state.json          # 应 < 10K
cat /tmp/hermes-state.json | wc -c     # 应 < 8000
```
**如果失败**: state.json 没生成 → cron 报错, 进日志查原因

### 2. claude -p 是否可调用
```bash
# 检查 plan.json
ls -la /tmp/hermes-plan.json           # 应存在
jq -e .steps /tmp/hermes-plan.json     # 应输出 steps 数组
```
**如果失败**: plan.json 不存在 → consult-claude.sh 降级到本地规划
- 检查 `/tmp/hermes-plan.degraded` 是否存在
- 如果 degraded, 查 `claude -p` 是否装了: `which claude`

### 3. plan schema 校验
```bash
# 看 plan 内容
jq '.steps | length' /tmp/hermes-plan.json           # ≤ 5
jq '.steps | map(.risk)' /tmp/hermes-plan.json       # 全 ≤ med
jq '.steps | map(.reversible)' /tmp/hermes-plan.json # 全 true
```
**如果失败**: retry 3 次后降级本地, 查 `/tmp/hermes-plan.degraded`

### 4. apply drain 耗时
```bash
# 查看 snapshot
ls -la /tmp/hermes-last-snapshot
cat /tmp/hermes-last-snapshot
# 检查 snapshot 目录
ls ~/.hermes/snapshots/
```
**如果危险**: drain 超时 (600s) → apply 失败, 查 evolve.log 最后 5 行

### 5. eval gate 结果
```bash
# 看决定
tail -20 ~/.hermes/logs/evolve.log | grep '"eval_result"'
# 可能值: "kept" / "rolled_back" / "kept_degraded"
```
**如果 rolled_back**: 第一次就跑不通也不用慌 — evolve 就是试错。查 delta 数值:
```bash
tail -5 ~/.hermes/logs/evolve.log
```

### 6. 3 连败 kill switch
```bash
# 验证 cron 状态
hermes cron list | grep 双脑
# 如果 enabled=false → kill switch 生效了
```
**如果生效**: 手动 `hermes cron resume <job_id>` 前先排查失败根因

## 首次运行后的期望范围

| 指标 | 期望 | 警告 |
|------|------|------|
| claude -p 耗时 | < 60s | > 120s → 模型太慢, 考虑换模型 |
| plan steps | 1-3 个 | > 5 → schema 限制生效 |
| drain 耗时 | < 5s | > 60s → 有长期运行的 task |
| eval delta | > -0.05 | < -0.05 → eval gate 会回滚 |
| 总耗时 | < 10min | > 30min → 哪步卡住了 |

## 如果一切顺利
```bash
# 检查 evolve.log 最后一条
tail -1 ~/.hermes/logs/evolve.log | python3 -m json.tool

# 检查 route_outcomes 有变化
python3 ~/.hermes/scripts/route_store.py summary
```

## 如果不顺利 — 快速回滚

```bash
# 如果有 snapshot
SNAP=$(cat /tmp/hermes-last-snapshot 2>/dev/null)
if [ -n "$SNAP" ] && [ -f "$SNAP/hermes-backup.zip" ]; then
    hermes import "$SNAP/hermes-backup.zip"
fi

# 或者手动暂停 cron
JID=$(hermes cron list 2>/dev/null | grep -i 双脑)
hermes cron pause $JID
```
