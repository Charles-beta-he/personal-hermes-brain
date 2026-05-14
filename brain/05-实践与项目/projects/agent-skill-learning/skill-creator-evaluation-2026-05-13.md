---
type: evaluation
project: hermes-skill-learning
source_candidate: "skill-creator / writing-skills"
evaluated_at: 2026-05-13T16:32:33+08:00
decision: borrow
status: deterministic-evidence-slice-complete
source_evidence: /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/superpowers-source-evidence-2026-05-13.json
---

# Skill Creator 官方元技能与 eval 测试框架适配评估

## 0. 结论

决策：BORROW，不 ADOPT，不批量导入。

来源核验复用本轮已生成的 `superpowers-source-evidence-2026-05-13.json`：可验证上游为 `obra/superpowers`，repo license 为 MIT，source tree 中包含 `writing-skills` 元技能。它对 Hermes 的价值不是“创建一个新的 skill-creator”，而是补强现有 `hermes-agent-skill-authoring` + `skill-eval` 的创建门禁、正负 prompt eval、read-back 验证和反漂移治理。

## 1. 来源与许可核验

本地证据：`/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/superpowers-source-evidence-2026-05-13.json`

| 项 | 值 |
|---|---|
| Repository | `obra/superpowers` |
| URL | `https://github.com/obra/superpowers` |
| License | `MIT` |
| License first line | `MIT License` |
| Copyright | `Copyright (c) 2025 Jesse Vincent` |
| Skill count in source tree | `14` |
| Includes meta skill | `writing-skills` |
| Method | GitHub API + raw files via Python stdlib urllib; no clone/install/import |

## 2. 元技能结构与 eval 框架抽象

从 `writing-skills` / Superpowers 方法论抽象出的可借鉴结构：

1. 先判断是否真的需要新 skill：优先 patch umbrella skill，避免一会话一 skill。
2. 明确触发条件与反触发条件：什么时候用，什么时候不要用。
3. 结构必须包含 overview / workflow / pitfalls / verification checklist。
4. 新 skill 必须能被测试：正向 prompt、负向 prompt、deterministic artifact check。
5. 写完后必须 read-back：确认 frontmatter、description、body、references 链接存在。
6. 发布/启用前必须验证不会与现有 skill graph 重复或冲突。

## 3. Hermes 现状对比

| Hermes surface | 已覆盖 | 缺口 | 本轮建议 |
|---|---|---|---|
| `hermes-agent-skill-authoring` | frontmatter、目录、validator、结构、commit | 创建前的“是否应创建”门禁不够显式 | 加 creation gate：先 patch umbrella / references |
| `skill-eval` | eval prompts、deterministic checks、report template | 与 authoring 的强绑定可更明确 | 增加 skill authoring gate reference |
| Skill Graph steward | cycle/depth/type violation 审计 | 新 skill 创建后必须跑 graph-check 的门禁需要写入流程 | 将 graph-check 作为创建/修改后的 gate |
| `skill_manage` | 本地技能创建/patch/write_file | 对 in-repo 与 user-local 差异易混淆 | 保持 authoring skill 中的路径规则 |

## 4. Creation gates / 创建门禁与回归测试增强方案

新增 artifact：

- `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/skill-authoring-creation-gates-2026-05-13.md`

最小 gate：

1. Need gate：证明现有 umbrella skill 不能覆盖；否则 patch umbrella + reference。
2. Shape gate：frontmatter + description <=1024 + body non-empty + peer structure。
3. Trigger gate：至少 3 正向 + 2 负向 prompt。
4. Behavior gate：有 deterministic artifact/read-back check。
5. Graph gate：`skill-steward.py --graph-check --json` 或 warn-only 报告。
6. Regression gate：修改后 `skill_view(name)` + linked reference read-back；必要时跑 eval prompts。

## 5. Acceptance mapping

| Acceptance | Evidence | Status |
|---|---|---|
| 确认来源与许可 | source evidence JSON；repo MIT；`writing-skills` present | PASS |
| 梳理元技能结构与 eval 框架 | Section 2 | PASS |
| 对比 hermes-agent-skill-authoring / skill-eval | Section 3 | PASS |
| 提出创建门禁与回归测试增强方案 | Section 4 + creation gates artifact | PASS |
| 不安装/不导入 | 复用已有 evidence；无 clone/install/import | PASS |

## 6. Decision

BORROW。

优先落点：`skill-eval` 增加 authoring gate reference；`hermes-agent-skill-authoring` 保留 in-repo/user-local 路径细节。不要创建单独 `skill-creator`，避免与现有 authoring/eval/steward 三件套重复。
