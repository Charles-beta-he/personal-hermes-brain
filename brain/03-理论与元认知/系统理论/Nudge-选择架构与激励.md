# Nudge + Mechanism Design：选择架构与激励

> Richard Thaler & Cass Sunstein, *Nudge* (2008), Nobel 2017
> Leonid Hurwicz, Eric Maskin, Roger Myerson, Mechanism Design (Nobel 2007)
> 联系：[[03-理论与元认知/治理理论/Havel-无权力者的权力|Havel]] ｜ [[03-理论与元认知/治理理论/Ostrom-公地治理8原则|Ostrom]]

## 核心命题

**Nudge：** 好的选择架构让正确行为成为默认路径，不需要强制。
**Mechanism Design：** 设计规则使得参与者的自利行为自动产生系统想要的结果。

## 当前问题

Havel 提供了"创建摩擦"（惩罚错误行为），但无正向激励。

```
当前: 创建 = 3 秒操作 → 高频率
      测试 = 10 分钟操作 → 低频率
      维护 = 无即时回报 → 几乎无人做
```

## 三阶激励设计

### 第一阶：默认架构 (Nudge)

```python
# 当前默认: skill_view('create') → 直接创建
# 优化默认: skill_view('create') → 先显示搜索现有库结果

def skill_view_pre_create(keyword):
    """搜索现有库作为创建的前提"""
    results = search_existing(keyword)
    if results:
        print(f"⚠️ 已有 {len(results)} 个相关技能:")
        for r in results[:5]:
            print(f"  - {r['name']}: {r['description'][:60]}")
        print("按 Enter 继续创建, 或 Ctrl+C 取消")
```

### 第二阶：激励机制 (Mechanism Design)

```python
# 每个行为产生积分：
REWARDS = {
    "create_skill": 0,         # 创建不给分（防止滥建）
    "add_tests": 10,            # 加测试给高分
    "add_changelog": 5,         # 记录版本历史
    "mark_deprecated": 15,      # 标记废弃给最高分
    "merge_duplicates": 20,     # 合并重复给最高分
    "fix_broken_ref": 10,       # 修复断裂引用
    "audit_skill": 5,           # 审计给分
}

# 积分阈值机制：
# 100 分 → "维护达人"徽章
# 200 分 → 建议的新 skill 自动标记为 ACTIVE（跳过 BETA 期）
# 300 分 → 可豁免一次熵债要求
```

### 第三阶：选择架构 (Nudge cont.)

```
"易维护 > 易创建" 原则：

创建新 skill 的路径: 搜索 → 确认缺乏 → 填写（5个字段）→ 确认熵债
更新已有 skill 的路径: 打开 → 编辑 → 保存（2个操作）
```

## 在 steward 中的应用

```python
def nudge_before_create():
    """创建前的默认路径"""
    # 1. 自动搜索（替代空白输入）
    results = search_files(target="content", pattern=keyword, path="~/.hermes/skills")

    # 2. 如果已有 → 建议扩展
    if results["matches"]:
        print("已有 {N} 个匹配技能。建议扩展现有技能，而非创建新技能。")
        print("继续创建将产生熵债。请确认。")

    # 3. 如果需要创建，引导填写关键字段
    print("请提供：\n  - 触发词 (至少 3 个)")
    print("  - 至少 2 个测试用例")
    print("  - 需要标记的废弃技能")
```

## 引用

> Thaler, R. H., & Sunstein, C. R. (2008). *Nudge: Improving Decisions About Health, Wealth, and Happiness*. Yale University Press.
> Hurwicz, L., & Reiter, S. (2006). *Designing Economic Mechanisms*. Cambridge University Press.

## Evidence Boundary

- 来源支持什么：该卡仅记录理论概念、经典解释或本地大脑已引用的工程化映射。
- Hermes 映射边界：Agent/多模型/技能治理映射是工程类比与设计启发，不等同于原理论在数学或社会科学意义上的严格证明。
- 不应过度推出什么：不得仅凭该理论卡宣称某项代码、流程或策略已经正确；仍需工具证据、原文证据、审计输出或运行验证。
