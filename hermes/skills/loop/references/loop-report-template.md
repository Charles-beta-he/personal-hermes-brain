# Loop Report Template — 标准化迭代报告

> ch04 观测器: 每次 loop 输出标准化报告

## 报告头部

```
═══════════════════════════════════════════════════════════════════════════════
                      Loop Report #{N} — {task_name}
═══════════════════════════════════════════════════════════════════════════════
Timestamp: {ISO8601}
Duration: {X} turns / {Y} minutes
PUA Level: L{N} ({trust|disappointment|soul-search|361|graduation})
```

## 一、本轮变更摘要

| 文件 | 操作 | 原因 |
|------|------|------|
| `path/to/file` | add/modify/delete | 一句话说明 |

## 二、验证结果

| 验证项 | 状态 | 输出摘要 |
|--------|------|---------|
| test | ✅ pass / ❌ fail | {关键信息} |
| build | ✅ pass / ❌ fail | {关键信息} |
| browser | ✅ pass / ❌ fail / ⏭ skip | {关键信息} |
| lint | ✅ pass / ❌ fail | {关键信息} |

**整体状态**: ✅ 全部通过 / ❌ 存在失败 / ⚠️ 部分跳过

## 三、健康度贡献

```
本轮 V 贡献:
  - 任务成功率: +{Δ}
  - 构建通过率: +{Δ}
  - 迭代效率: +{Δ}
  - 其他: +{Δ}
本轮 V̇: {value} ({evolving|stagnant|degrading})
```

## 四、问题与发现

- [ ] 新问题: {描述}
- [ ] 已知问题持续: {描述} (第 {N} 次出现)
- [ ] 极限环风险: {是/否}

## 五、下一轮计划

- [ ] 待修复: {issue}
- [ ] 待验证: {check}
- [ ] 待补充: {task}

## 六、是否需要人类介入

- [ ] 否，继续自主迭代
- [ ] 是，原因: {reason}
  - 决策点: {decision_needed}
  - 选项: A) ... B) ... C) ...
