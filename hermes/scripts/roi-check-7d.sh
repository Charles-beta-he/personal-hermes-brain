#!/usr/bin/env bash
# 7天ROI评估 — 双脑自进化 vs 旧 pipeline
# 在双脑跑满 7 次后执行, 判断是否值得保留
#
# Usage: bash ~/.hermes/scripts/roi-check-7d.sh
set -euo pipefail

EVOLVE_LOG=~/.hermes/logs/evolve.log
echo "=========================================="
echo "  双脑自进化 — 7天 ROI 评估"
echo "  生成: $(date '+%Y-%m-%d %H:%M')"
echo "=========================================="

# 1. 统计 evolve.log 中双脑模式的记录
echo ""
echo "── 双脑运行统计 ──"

if [ ! -f "$EVOLVE_LOG" ] || [ ! -s "$EVOLVE_LOG" ]; then
    echo "  evolve.log 不存在或为空"
    echo ""
    echo "建议: 等双脑跑满 7 次后再执行本脚本"
    exit 0
fi

TOTAL=$(wc -l < "$EVOLVE_LOG")
echo "  Total evolve ticks: $TOTAL"

# 统计结果分布
KEPT=$(grep -c '"eval_result":"kept"' "$EVOLVE_LOG" 2>/dev/null || echo 0)
ROLLBACK=$(grep -c '"eval_result":"rolled_back"' "$EVOLVE_LOG" 2>/dev/null || echo 0)
DEGRADED=$(grep -c '"eval_result":"kept_degraded"' "$EVOLVE_LOG" 2>/dev/null || echo 0)
echo "  Kept:        $KEPT"
echo "  Rolled back: $ROLLBACK"
echo "  Degraded:    $DEGRADED"
echo "  Unknown:     $((TOTAL - KEPT - ROLLBACK - DEGRADED))"

# 统计 delta 平均值
echo ""
echo "── pass_rate delta 统计 ──"
DELTAS=$(grep '"delta":' "$EVOLVE_LOG" 2>/dev/null | grep -oP '"delta":[-+]?[0-9.]+' | grep -oP '[-+]?[0-9.]+' || echo "")

if [ -n "$DELTAS" ]; then
    echo "$DELTAS" | python3 -c "
import sys
vals = [float(l) for l in sys.stdin if l.strip()]
if vals:
    avg = sum(vals) / len(vals)
    pos = sum(1 for v in vals if v > 0)
    neg = sum(1 for v in vals if v < 0)
    print(f'  Count:     {len(vals)}')
    print(f'  Average:   {avg:+.4f}')
    print(f'  Positive:  {pos}')
    print(f'  Negative:  {neg}')
    print(f'  Min:       {min(vals):+.4f}')
    print(f'  Max:       {max(vals):+.4f}')
else:
    print('  No delta data found')
"

# 2. 当前 route_outcomes pass_rate (近期)
echo ""
echo "── 当前系统健康度 (7天) ──"
python3 ~/.hermes/scripts/route_store.py stats --hours 168 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(f'  pass_rate: {d.get(\"pass_rate\", \"N/A\")}')
    print(f'  total traces: {d.get(\"total\", 0)}')
    print(f'  avg duration: {d.get(\"avg_duration\", \"N/A\")}s')
except:
    print('  (route_store stats unavailable)')
" 2>/dev/null || echo "  (route_store unavailable)"

# 3. 结论
echo ""
echo "── 结论 ──"

SUCCESS_RATE=0
[ "$TOTAL" -gt 0 ] && SUCCESS_RATE=$(python3 -c "print(round(($KEPT + $DEGRADED) / $TOTAL, 3))" 2>/dev/null || echo 0)

if [ "$TOTAL" -lt 3 ]; then
    echo "  数据不足 (仅 $TOTAL 次 tick), 继续观察"
    echo "  建议: 跑满 7 次后再来"
elif python3 -c "exit(0 if float('$SUCCESS_RATE') < 0.3 else 1)" 2>/dev/null; then
    echo "  ⛔ SUCCESS RATE ${SUCCESS_RATE}% — 低于 30%"
    echo "  建议: 检查 consult-claude.sh 的 degrade 次数"
    echo "  考虑关掉双脑, 回到旧 self-improvement-pipeline"
elif python3 -c "exit(0 if float('$SUCCESS_RATE') < 0.7 else 1)" 2>/dev/null; then
    echo "  ⚠️  SUCCESS RATE ${SUCCESS_RATE}% — 中等"
    echo "  建议: 看具体失败原因, 是否有 schema 问题"
elif python3 -c "exit(0 if float('$SUCCESS_RATE') > 0.9 else 1)" 2>/dev/null; then
    echo "  ✅ SUCCESS RATE ${SUCCESS_RATE}% — 优秀"
    echo "  建议: 保留双脑, 考虑加 L5 canary"
else
    echo "  ✅ SUCCESS RATE ${SUCCESS_RATE}% — 良好"
fi

echo ""
echo "=========================================="
echo "  评估完成"
echo "=========================================="
