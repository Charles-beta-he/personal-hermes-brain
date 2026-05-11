# Optimal Control Modes — 任务级性能指标动态权重

> ch09 最优控制: 不同任务类型切换性能指标权重（紧急/常规/探索）

## 三种运行模式

### 模式 A: 紧急模式 (Emergency)

触发条件: 线上故障、安全漏洞、数据丢失

```
权重分配:
  速度        0.40  ← 最高优先级
  正确性      0.30
  代码质量    0.10
  可维护性    0.10
  测试覆盖    0.10

行为调整:
  - 跳过非关键验证（仅保留安全相关）
  - 允许技术债，事后补票
  - P10 直接介入（跳过 P9 拆解）
  - 最大 token 预算解锁
```

### 模式 B: 常规模式 (Normal) — 默认

触发条件: 标准 feature / bugfix / refactor

```
权重分配:
  正确性      0.30  ← 最高优先级
  代码质量    0.25
  可维护性    0.20
  测试覆盖    0.15
  速度        0.10

行为调整:
  - 标准 P10→P9→P8 流程
  - 完整验证链（test + build + browser）
  - 遵循 reference-model
```

### 模式 C: 探索模式 (Exploration)

触发条件: 新技术调研、原型验证、架构探索

```
权重分配:
  可维护性    0.35  ← 最高优先级（易废弃/重构）
  正确性      0.25
  学习价值    0.20  ← 独特指标
  速度        0.15
  测试覆盖    0.05

行为调整:
  - 允许快速试错
  - 最小验证（核心路径即可）
  - 重点记录 learnings（入 memory，λ=0.95）
  - 产出物标记为 [EXPERIMENTAL]
```

## 模式切换决策

```python
def select_mode(task_spec):
    keywords = task_spec.lower()
    
    if any(w in keywords for w in ["紧急", "线上", "故障", "安全", "cve", "hotfix"]):
        return "EMERGENCY"
    elif any(w in keywords for w in ["调研", "探索", "原型", "poc", "spike", "experiment"]):
        return "EXPLORATION"
    else:
        return "NORMAL"
```

## 与 V(x) 的协同

```
紧急模式: V 计算中速度权重临时提升，但允许 V 短期下降（事后补偿）
常规模式: V 标准计算
探索模式: V 中学习价值纳入计算（临时维度）
```
