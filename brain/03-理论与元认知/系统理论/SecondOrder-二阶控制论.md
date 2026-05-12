# Second-Order Cybernetics：二阶控制论

> Heinz von Foerster, *Observing Systems* (1981)
> 联系：[[03-理论与元认知/控制论基础/01-反馈回路与稳定性|反馈回路]] ｜ [[03-理论与元认知/治理理论/Conway-逆定律-组织决定系统|Conway 逆]]

## 核心命题

**一阶控制论**研究"观察者的系统"——观察者站在系统外部。
**二阶控制论**研究"观察者参与的系统"——观察者自身是系统的一部分。

问题："谁治理治理者？" (Quis custodiet ipsos custodes?)

## 应用：Steward 的自审计

当前 steward 是**一阶观察者**——它在审计 skills，但它的规则是硬编码的。

二阶要求 steward 必须审计自己的审计：

```python
# 一阶: steward → audits → skills
# 二阶: steward → audits → (skills + steward's own rules)

# 具体实现：
def self_audit(rule_history):
    """Steward 审计自己的治理规则"""
    # 规则 A 在过去 30 天导致了 N 次标记
    # 规则 B 在过去 30 天导致了 M 次标记
    # 如果某个规则从未被触发 → 规则可能已过时
    # 如果某个规则被触发但立即被手动撤销 → 规则可能与用户意图冲突

    for rule, stats in rule_history.items():
        if stats["triggers"] == 0 and rule_age > 90:
            mark_dormant(rule)
        if stats["reverts"] / stats["triggers"] > 0.3:
            mark_contested(rule)
```

## 实现

在 steward 的每日审计中增加 self-audit 节：

### 1. 规则活性检测
- 哪些规则在最近 30 天被触发过？
- 未触发的规则 → DORMANT → 建议移除或合并

### 2. 规则冲突检测
- 规则 A 和规则 B 是否总是同时触发？
- 是 → 它们可能描述了同一件事的不同方面 → 合并

### 3. 规则效果追踪
- 应用规则后，技能生态是否变好？
- 用 V_health 指标追踪：生效前的 7 天 vs 生效后的 7 天

## 引用

> von Foerster, H. (1981). *Observing Systems*. Intersystems Publications.
> Glanville, R. (2002). "Second-order cybernetics". In *Systems Science and Cybernetics*, UNESCO.

## 多模型自观察 / multi-model self-observation

second-order cybernetics 在多模型系统中的关键不是“更多模型同意”，而是观察 observer：谁选择了模型？谁定义了证据门？谁把 timeout/dissent 写入 issue ledger？谁审计 audit rules？

对应 atom：[[04-知识原子/atoms/second-order-cybernetic-self-observation]]。
对应 playbook：[[05-实践与项目/实践方案/06-一阶二阶控制论多模型介入Playbook]]。

## Evidence Boundary

- 来源支持什么：该卡仅记录理论概念、经典解释或本地大脑已引用的工程化映射。
- Hermes 映射边界：Agent/多模型/技能治理映射是工程类比与设计启发，不等同于原理论在数学或社会科学意义上的严格证明。
- 不应过度推出什么：不得仅凭该理论卡宣称某项代码、流程或策略已经正确；仍需工具证据、原文证据、审计输出或运行验证。
