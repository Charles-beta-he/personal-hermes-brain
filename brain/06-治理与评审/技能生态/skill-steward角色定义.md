# Skill Steward 角色定义

> 基于 Conway 逆定律
> 联系：[[03-理论与元认知/治理理论/Conway-逆定律-组织决定系统|Conway 逆]] ｜ [[03-理论与元认知/治理理论/Ostrom-公地治理8原则|Ostrom]]

## 角色定位

Skill Steward 不是一个人，是一个 **cronjob 驱动的自治角色**。它的存在改变了"组织"的沟通结构，而 Conway 保证系统结构会随之改变。

## 职责矩阵

| 职责         | 频率  | 理论依据         | 工具                             |
| ---------- | --- | ------------ | ------------------------------ |
| 检测僵尸 skill | 每日  | Prigogine 熵债 | `skill-steward.py`             |
| 检测同名冲突     | 每日  | Parnas 分解    | `skill-steward.py`             |
| 更新健康仪表盘    | 每日  | Ostrom 监控    | `skill-steward.py --dashboard` |
| 执行梯度制裁     | 每周  | Ostrom 制裁    | `skill-steward.py --cleanup`   |
| 报告违规       | 每日  | Ostrom 原则4   | 输出到 Obsidian                   |
| 同步 brain   | 每小时 | Conway 逆     | `sync-brain.py`                |

## Cron 配置

```yaml
# Steward 每日审计
- schedule: "0 2 * * *"
  prompt: |
    Run ~/.hermes/scripts/skill-steward.py and check output.
    If any FAIL indicators, report them.
    Then run ~/.hermes/scripts/sync-brain.py --push
  name: skill-steward-daily-audit

# Steward 每周清理
- schedule: "0 3 * * 0"
  prompt: |
    Run ~/.hermes/scripts/skill-steward.py --cleanup
    Execute all suggested ARCHIVE operations.
    Then run ~/.hermes/scripts/sync-brain.py --push
  name: skill-steward-weekly-cleanup

# Brain 同步（与 Steward 解耦，高频率）
- schedule: "0 * * * *"
  prompt: "Run ~/.hermes/scripts/sync-brain.py"
  name: brain-hourly-sync
```

## 自治权限

Steward 被授权：
- 标记技能状态（ACTIVE → DEPRECATED → ARCHIVED）
- 生成并发布合规报告
- 提议合并/重组方案
- 阻塞超过 200 个技能以上的新创建

Steward **不可以**：
- 修改技能内容（只能标记状态）
- 删除未经过 DEPRECATED → ARCHIVED 流程的技能
- 覆盖用户的显式配置

## 收益

- 生态健康度从"人治"变成"法治"
- Conway 逆保证：每次 cronjob 运行，都在重塑系统结构
- 用户看到的技能列表从 162 降为 ≤ 50
