---
type: evaluation
project: hermes-skill-learning
source_candidate: "Perplexity article: Designing, Refining, and Maintaining Agent Skills"
evaluated_at: 2026-05-13T23:41:14+08:00
decision: borrow
status: deterministic-evidence-slice-complete
source_url: https://research.perplexity.ai/articles/designing-refining-and-maintaining-agent-skills-at-perplexity
---

# Perplexity Agent Skills 文章评估与 Hermes 自优化落点

## 0. 结论

决策：**BORROW**，不平移复制整套 Perplexity 机制，而是把其中高杠杆原则映射到 Hermes 现有 skill authoring / skill eval / skill graph / umbrella 治理链路。

这篇文章对 Hermes 最有价值的不是“再造一个新技能体系”，而是把已有治理从“会写 skill”推进到“按上下文预算、路由精度、gotcha 飞轮、负例 eval、渐进加载”系统化执行。

## 1. 原文高信号结论（可直接迁移）

1. **Skill 是目录，不只是 `SKILL.md`**  
   根文件只放高密度入口契约；重逻辑放 `references/`、`scripts/`、`assets/`，按需渐进加载。
2. **Description 是路由触发器，不是功能说明**  
   好描述回答“什么时候该 load”，而不是“这个 skill 能做什么”。
3. **三层上下文成本必须分层治理**  
   - index：所有 skill 的 name/description，人人每会话都付费  
   - load：Skill body，被加载后持续占上下文  
   - runtime：references/scripts/assets，仅在需要时再读
4. **不要把人类 README 直接当 Skill**  
   模型通常已知通用命令；Skill 应保留“判断、边界、gotcha、负例、质量门”。
5. **Gotchas 是最高价值内容，且应 append-mostly**  
   失败一次，加一条负例/坑点，远比泛化加长 workflow 更有收益。
6. **先写 eval，再写/改 skill**  
   至少要覆盖：正向触发、负向不触发、邻域混淆、附件文件是否被正确渐进读取。
7. **新增 skill 会远距离破坏其他 skill**  
   技能生态要看 graph / routing regression，而不是单 skill 局部正确即可。

## 2. 与 Hermes 当前体系的对照

### 已有基础

- `hermes-agent-skill-authoring`：已覆盖 frontmatter、结构、in-repo vs user-local 路径、mode 选择。
- `skill-eval`：已覆盖 3 正 + 2 负 prompt、deterministic check、rubric、回归跟踪。
- `workflow-ecosystem-audit`：已覆盖技能生态梳理、broken references、工作流缺口扫描。
- 用户脑内治理：已明确“优先 patch umbrella/class-level skill，细节放 references，避免一会话一 skill”。

### 当前缺口

1. **三层上下文预算还未被明确写成 skill authoring contract**  
   现在有“尽量精简”的共识，但缺少 index/load/runtime 的预算语言与分层迁移规则。
2. **描述质量评估更多停留在格式层，尚未形成 routing trigger 审核清单**  
   还需要显式检查：是否写成用户意图、是否回答“何时 load”、是否避免 workflow 摘要化。
3. **Gotcha 飞轮虽有实践，但缺少统一 append-mostly 维护协议**  
   出错后应优先补 gotcha/负例，而不是直接把主文档写长。
4. **渐进加载策略尚未被系统化要求**  
   对复杂 skill，仍需明确：什么必须留在 root body，什么必须挪到 `references/`。
5. **图级回归门还可更前置**  
   新 skill / 改 description 后，需要把 graph-check、trigger eval、off-target 风险审计写成强门禁，而不是建议项。

## 3. Hermes 建议落点（最小高杠杆）

### A. `hermes-agent-skill-authoring`

补强四个点：

1. 增加 **context budget contract**：
   - description = index layer，必须极短、触发导向、全局付费；
   - root SKILL body = load layer，只保留高密度判断与关键流程；
   - references/scripts/assets = runtime layer，条件触发再读。
2. 增加 **description 审核清单**：
   - 是否以 `Use when ...` / `Load when ...` 表达用户意图；
   - 是否避免解释 workflow；
   - 是否包含邻域区分词，减少 off-target load。
3. 增加 **gotcha append-mostly 原则**：
   skill 失败后优先补 gotcha 或负例，不优先膨胀正文。
4. 增加 **progressive disclosure 迁移规则**：
   body > 8-15k 字符或出现条件分支/大文档时，拆到 `references/`。

### B. `skill-eval`

补强四个点：

1. 把 **routing precision/recall** 提升为第一类验收，而不仅是“有没有触发”。
2. 增加 **negative/neighbor confusion** 的强调：负例比正例更值钱。
3. 增加 **accessory file read eval**：skill load 后是否真的读了 `references/*.md` / `FORMATTING.md`。
4. 增加 **multi-model routing variance** 提醒：同一 skill 在不同编排模型下触发行为可能不同。

### C. skill graph / steward / ecosystem audit

1. 把“新增 skill 可能破坏旧 skill”写成显式 graph-risk 结论。
2. description 变化后默认要求 graph-check / warn-only 审计。
3. 对 placeholder / 泛描述 / workflow-summary 式 description 进行集中排查。

## 4. 建议执行拆片（供任务池继续派发）

### Slice 1 — 合同层补丁（低风险）

- patch `hermes-agent-skill-authoring`
- patch `skill-eval`
- 如有需要，补一份 `references/perplexity-skill-lessons.md`

### Slice 2 — 审计层

- 扫描 skill library 中 description 是否偏“功能说明”而非“触发条件”
- 扫描哪些 skill 主体过长、应迁移到 `references/`
- 扫描哪些 skill 缺少 gotchas / negative controls / verification shell

### Slice 3 — 回归门

- description/graph 变更后运行 `skill-steward.py --graph-check --json`
- 为关键治理 skill 补 3 正 + 2 负 prompt 集
- 记录 read-back 证据：`skill_view(name)` 与 linked reference read-back

## 5. Adopt / Borrow / Reject

- **Adopt**：无。Perplexity 的成本模型与运行时设计不能机械照搬。
- **Borrow**：三层上下文预算、description=trigger、gotcha 飞轮、negative eval、progressive disclosure。
- **Reject**：把 skill 当 README/命令清单写；为了“好解释”而重复模型本就知道的内容。

## 6. 推荐任务池目标

将后续执行目标定义为：

1. 用最小补丁把 Perplexity 方法论并入 Hermes 的 **authoring + eval + graph governance**。  
2. 不新建平行元技能，优先 patch 现有 umbrella/class-level skills。  
3. 产出可验证 evidence：skill 补丁、reference、graph-check、read-back、taskpool proof。

## 7. Acceptance mapping

- 原文已读并提炼结构化原则：PASS
- 已对照 Hermes 现有 `hermes-agent-skill-authoring` / `skill-eval` / workflow audit：PASS
- 已形成最小高杠杆落点与执行拆片：PASS
- 未宣称已完成技能补丁或全库审计：PASS
