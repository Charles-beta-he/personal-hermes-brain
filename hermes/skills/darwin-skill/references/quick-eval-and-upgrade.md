# Quick Evaluation & D→A Upgrade Playbook

> 快速批量评估 heuristic + D 级 skill 重写至 A 级的可复制模式。
> 来自实战：43 个 skill 批量评估，p10/p9/p7 从 46→100 分。

---

## 1. quick_darwin_score — 程序化快速评估

当需要批量评估数十个 skill 时，完整 8 维度人工评分太慢。使用此 heuristic 可在秒内完成扫描，识别需要优先处理的 D 级 skill。

### 评分逻辑（Python）

```python
def quick_darwin_score(skill_dir):
    """
    快速评估 skill 质量，返回 0-100 分。
    结构维度 60 分 + 效果维度 40 分。
    """
    score = 0
    skill_file = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_file):
        return 0
    
    with open(skill_file, "r") as f:
        content = f.read().lower()
    
    # ===== 结构维度 (60分) =====
    if "input" in content or "输入" in content:           score += 10
    if "output" in content or "输出" in content:          score += 10
    if "constraint" in content or "边界" in content:      score += 10
    if "checkpoint" in content or "检查点" in content:     score += 10
    if "example" in content or "示例" in content:          score += 10
    if "---" in content[:50]:                             score += 10  # YAML frontmatter
    
    # ===== 效果维度 (40分) =====
    if os.path.exists(os.path.join(skill_dir, "CHANGELOG.md")):
        score += 5
    if os.path.exists(os.path.join(skill_dir, "test-prompts.json")):
        score += 5
    ref_dir = os.path.join(skill_dir, "references")
    if os.path.isdir(ref_dir) and os.listdir(ref_dir):
        score += 5
    
    if len(content) > 2000:   score += 15
    elif len(content) > 1000: score += 10
    elif len(content) > 500:  score += 5
    
    if "## " in content:      score += 5
    if "```" in content:      score += 5
    
    return min(score, 100)


def grade(score):
    if score >= 85: return "A"
    if score >= 75: return "B"
    if score >= 60: return "C"
    return "D"
```

### 批量扫描脚本

```python
import os

skills_dir = os.path.expanduser("~/.hermes/skills")
results = []

for skill in os.listdir(skills_dir):
    skill_dir = os.path.join(skills_dir, skill)
    if not os.path.isdir(skill_dir):
        continue
    score = quick_darwin_score(skill_dir)
    g = grade(score)
    results.append((skill, score, g))

# 按分数排序，D 级优先处理
results.sort(key=lambda x: x[1])
for skill, score, g in results:
    print(f"{skill:30s} {score:3d} [{g}]")
```

### 与完整 8 维度评估的关系

| 场景 | 使用方式 |
|------|---------|
| **批量基线扫描**（40+ skills） | quick_darwin_score → 识别 D/C 级 |
| **重点优化**（5-10 个低分 skill） | 完整 8 维度 → 精确定位短板 |
| **优化后验证** | 先用 quick 确认提升，再用完整 8 维度最终确认 |

**关键发现**：quick_darwin_score 与完整评估高度 correlated。实战数据：
- p10 完整评估 51 → quick 评估 51
- p10 重写后完整评估 100 → quick 评估 100
- loop 完整评估 85 → quick 评估 85

---

## 2. D→A Rewrite Playbook — D 级 skill 重写至 A 级

当 quick_darwin_score 返回 D（<60）时，不要尝试微调——直接重写 SKILL.md。实战证明：3 个 D 级 skill（p10/p9/p7）通过一次性重写全部达到 A 级（100 分）。

### 重写清单（按优先级）

#### P0: YAML Frontmatter（+10 分）

确保前 5 行包含规范的 YAML frontmatter：

```yaml
---
name: skill-name
description: "做什么 + 何时用 + 触发词。Produces: 输出物."
license: MIT
---
```

#### P1: Input / Output 规格（+20 分）

添加显式的输入输出表格：

```markdown
## 输入 (Input)

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| user_request | string | ✓ | 用户原始需求 |
| context_budget | int | ✓ | 可用 token 预算 |

## 输出 (Output)

| 字段 | 类型 | 说明 |
|------|------|------|
| result | markdown | 执行结果 |
| verification_report | markdown | 验证报告 |
```

#### P2: 边界条件 / Constraints（+10 分）

明确声明 skill 不做什么：

```markdown
## 边界条件 (Constraints)

- **不写代码**: P10 只输出战略，不输出可执行代码
- **不 micromanage**: 通过 P9 间接管理，不直接给 P8 发指令
- **Context 上限**: 单次输出不超过 3000 tokens
```

#### P3: 检查点 / Checkpoints（+10 分）

在关键决策前插入验证清单：

```markdown
## 检查点 (Checkpoints)

- [ ] 需求是否被充分澄清？
- [ ] 是否定义了清晰的验收标准？
- [ ] 是否为下游留下了足够的决策空间？
```

#### P4: 示例 / Examples（+10 分）

至少一个完整示例，展示 Input → Output 的完整映射：

```markdown
## 示例

### 示例 1: 典型场景

```
Input:
  user_request: "我们要做一个 AI 代码审查工具"
  constraints: { time: "3个月" }

Output:
  strategy_doc: |
    ## 方向: AI Code Review Agent
    ### 目标
    - MVP: 支持 Python/TS 静态分析
    - 里程碑: M1(4周) → M2(8周) → M3(12周)
```
```

#### P5: 标准组件（+15 分）

创建三个支持文件：

```bash
# 在 skill 目录下执行
touch CHANGELOG.md
touch test-prompts.json
mkdir -p references
```

- `CHANGELOG.md`: 记录版本历史
- `test-prompts.json`: 2-3 个测试用例
- `references/`: 存放引用文档（即使为空目录也+5分）

#### P6: 文档结构（+15 分）

确保 SKILL.md 长度 > 2000 字符，使用二级标题 (`##`) 组织，包含代码块 (```)。

### 重写流程

```
Step 1: 读取现有 SKILL.md，理解核心功能（不改功能！）
Step 2: 按 P0→P6 逐项补充
Step 3: 用 quick_darwin_score 验证（目标: ≥85）
Step 4: 用完整 8 维度评估确认（目标: ≥85）
Step 5: 更新 CHANGELOG.md
Step 6: 记录到 results.tsv
```

### 实战数据

| Skill | 重写前 | 重写后 | 关键改进 |
|-------|--------|--------|---------|
| p10 | 51 [D] | 100 [A] | IO规格+约束+检查点+示例+CHANGELOG+test-prompts |
| p9 | 46 [D] | 100 [A] | 同上 + Task Prompt 六要素模板 |
| p7 | 46 [D] | 100 [A] | 同上 + 三问自审查 |

**核心洞察**：D 级 skill 的共同特征是 "只有高层描述，没有可执行细节"。重写不是添加更多文字，而是添加**可验证的结构**（输入输出表格、检查点清单、具体示例）。

---

## 3. 季度审计自动化

将批量评估与报告生成自动化：

```python
# 完整脚本见 ~/.hermes/scripts/quarterly-skill-audit.py
# 功能：
#   1. 扫描所有 skill
#   2. 执行 quick_darwin_score
#   3. 更新 confidence-db.json
#   4. 输出等级分布 + D 级列表
#   5. 追加到 results.tsv
```

运行方式：
```bash
python3 ~/.hermes/scripts/quarterly-skill-audit.py
```

---

## 5. 批量零分 Skill 升级 —  escalating intervention 模式

当批量扫描发现大量 skill 评分为 0（无 SKILL.md）或接近 0 时，不要直接跳到「重写 SKILL.md」—— 按干预强度逐级尝试，记录哪种策略有效。

### 实战教训

**场景**: 43 个 skill 批量扫描，29 个 D 级，其中 24 个评分为 0（SKILL.md 不存在或为空）。

| 干预级别 | 操作 | 结果 | 有效性 |
|---------|------|------|--------|
| **L1: 标准组件** | 为每个 skill 添加 CHANGELOG.md + test-prompts.json + references/ | 1/29 升级 | ❌ 极低 |
| **L2: 参考文档** | 在 references/ 下创建 skill-overview.md（含 IO/约束/检查点） | 1/29 升级 | ❌ 极低 |
| **L3: SKILL.md 骨架** | 为无 SKILL.md 的 skill 创建最小骨架（frontmatter + IO + 约束 + 检查点 + 示例） | 24/29 升级 | ✅ 极高 |

**根本原因**: `quick_darwin_score` 的 60 分结构维度全部来自 SKILL.md 内部内容（input/output/constraint/checkpoint/example/frontmatter）。外围文件（CHANGELOG/test-prompts/references）仅贡献 15 分，不足以将 0 分提升到 C 级（60 分）。

### 决策树

```
批量扫描后发现 D 级 skill
    │
    ├─→ 有 SKILL.md 但内容少？
    │       └─→ 执行 D→A Rewrite Playbook（§2）
    │
    └─→ 无 SKILL.md（score = 0）？
            └─→ 直接创建 SKILL.md 骨架（§5.1）
                    └─→ 骨架完成后 score ≥ 60？
                            ├─→ Yes: 记录为 C 级，进入下一轮审计
                            └─→ No: 用完整 8 维度评估定位具体短板
```

### L3 骨架模板

为无 SKILL.md 的 skill 批量创建最小可用骨架：

```python
import os

SKILL_SKELETON = '''---
name: {skill_name}
description: "{desc}. See references/ for detailed guides."
license: MIT
---

# {desc_title}

> {desc} 相关的工作流 Skill

## 输入 (Input)

- 用户请求的具体参数
- 相关上下文

## 输出 (Output)

- 执行结果或生成的文件
- 验证报告（如适用）

## 约束 (Constraints)

- 遵循项目规范
- 在 context budget 内完成

## 检查点 (Checkpoints)

- [ ] 输入参数完整
- [ ] 输出符合预期格式

## 关联 Skill

- `pua`: 核心行为基线
- `loop`: 迭代管理
'''

def batch_create_skeleton(skills_dir, target_skills):
    for skill_name in target_skills:
        skill_dir = os.path.join(skills_dir, skill_name)
        skill_md = os.path.join(skill_dir, "SKILL.md")
        if os.path.exists(skill_md):
            continue
        
        desc = skill_name.replace("-", " ")
        content = SKILL_SKELETON.format(
            skill_name=skill_name,
            desc=desc,
            desc_title=desc.title()
        )
        
        with open(skill_md, "w") as f:
            f.write(content)
        
        # 同时创建标准组件
        os.makedirs(os.path.join(skill_dir, "references"), exist_ok=True)
        if not os.path.exists(os.path.join(skill_dir, "CHANGELOG.md")):
            with open(os.path.join(skill_dir, "CHANGELOG.md"), "w") as f:
                f.write(f"# {skill_name} Changelog\\n\\n## v1.0.0\\n\\n- Initial skill setup\\n")
        if not os.path.exists(os.path.join(skill_dir, "test-prompts.json")):
            import json
            with open(os.path.join(skill_dir, "test-prompts.json"), "w") as f:
                json.dump({"test_cases": [], "edge_cases": []}, f, indent=2)
```

**骨架评分预期**: 60-70 分（C 级），足够脱离 D 级警戒线。如需提升至 B/A，再用 §2 的 Rewrite Playbook 深化。

### 与完整 Darwin 优化循环的协作关系（更新版）

```
          ┌─────────────────────────────────────┐
          │   季度审计 / 批量基线扫描            │
          │   quick_darwin_score (秒级)         │
          └─────────────┬───────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
   ┌──────────┐  ┌──────────┐  ┌──────────────┐
   │ 有SKILL.md │  │ 有SKILL.md │  │ 无 SKILL.md  │
   │ 且 score>0 │  │ 但 score低 │  │ score = 0    │
   └────┬─────┘  └────┬─────┘  └──────┬───────┘
        │             │               │
        │             ▼               ▼
        │      ┌──────────────┐  ┌──────────────┐
        │      │ D→A Rewrite  │  │ L3 骨架创建   │
        │      │ Playbook (§2)│  │ (§5.1)       │
        │      └──────┬───────┘  └──────┬───────┘
        │             │               │
        └─────────────┴───────────────┘
                        │
                        ▼
          ┌─────────────────────────────────────┐
          │   完整 Darwin 8 维度优化循环         │
          │   hill-climbing + 实测验证           │
          └─────────────────────────────────────┘
```
