---
name: framework-audit
description: Use when evaluating whether to adopt, reject, or selectively extract ideas from an external AI framework, GitHub repo, package, or CLI. Produces evidence-first adoption analysis, integration risk assessment, and Hermes-native selective-adoption recommendations.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - framework-audit
    - third-party
    - evaluation
    - adoption
    - integration
    - decision-framework
    related_skills:
    - multi-model-thinking
    - private-fork-evolution-governance
    - workflow-ecosystem-audit
---

# Framework Audit — 第三方 AI 系统评估与引入决策

## Overview


> 不要因为一个工具流行就引入。评估 → 决策 → 选择性借鉴 → 集成。

## When to Use

- Evaluating whether to adopt, reject, or selectively extract ideas from an external AI framework, GitHub repo, package, or CLI. Produces evidence-first adoption analysis, integration risk assessment, and Hermes-native selective-adoption recommendations

## 核心流程

```
[1] 信息收集    → [2] 多维度分析    → [3] 引入决策    → [4] 选择性借鉴    → [5] 集成与验证
```

---

## Phase 1: 信息收集

### 1.1 仓库结构分析

```bash
# 快速了解项目规模
git clone --depth 1 <repo-url> /tmp/<repo-name>
find /tmp/<repo-name> -type f | wc -l          # 文件总数
du -sh /tmp/<repo-name>                         # 总大小
ls /tmp/<repo-name>                             # 根目录结构
```

关键观察点：
- 总文件数 > 500 → 大型项目，引入成本高
- 包含 hooks/SDK/CLI → 深度绑定特定运行时
- 多语言 README → 社区活跃度高
- 有 IDE 配置文件 → IDE 深度集成

### 1.2 核心理念理解

阅读以下文件（按优先级）：
1. `README.md` 前 200 行（解决的问题 + 核心卖点）
2. `package.json`（依赖、脚本、bin 命令）
3. 核心工作流文件（通常是 `workflows/` 或 `commands/`）
4. 一个代表性 agent/skill 的完整定义

**关键问题清单**：
- 这个工具解决什么问题？
- 它的核心理念是什么？（spec-driven? context-engineering? wave-execution?）
- 它与现有体系的关系是什么？替代/补充/冲突？
- 它的运行环境要求是什么？

### 1.3 AI Memory / RAG / Agent-Memory Benchmark 审计

当目标仓库是 AI memory、RAG、长期记忆、conversation memory、local-first memory、MCP memory server，且 README 发布 recall/benchmark/SOTA 数字时，必须做 evidence-first benchmark audit，而不是只复述 README。

最小审计步骤：
1. 固定 commit SHA、branch、package version、CLI/MCP entry points。
2. 阅读 README benchmark 表后，定位 `benchmarks/` 下的 result JSON/JSONL、split 文件、methodology 文档和 benchmark scripts。
3. 用脚本重算 headline 数字：records、hit/recall/ndcg、category breakdown、held-out/dev split overlap。注意很多 JSONL 把指标藏在 `retrieval_results.metrics.session.recall_any@5` 这类嵌套字段里，不要只找顶层 `hit`。
4. 读取 metric 定义，明确是 retrieval recall / evidence hit / session hit，还是 end-to-end QA accuracy。
5. 对竞品比较做公平性检查：不同 split、不同 top-k、retrieval recall vs QA accuracy、LLM rerank vs no-LLM 不得混同。
6. 检查 local-first/privacy 边界：默认 provider、external API consent、auto hooks、MCP write/delete tools、WAL/audit。
7. 给 adoption 结论时优先区分：canonical memory、evidence archive、secondary search index、agent diary、KG supplement。
8. 若用户问“对本地大脑层级是否有帮助”，先审计当前 `~/Documents/brain` 结构和 MOC，再判断该仓库是改善知识层级、检索召回、证据边界、还是只增加第二记忆栈。详细流程见 `references/local-brain-memory-repo-adoption.md`。

详细清单见 `references/ai-memory-repo-benchmark-audit.md`；本地大脑适配见 `references/local-brain-memory-repo-adoption.md`。

### 1.4 Agent Orchestration / Swarm Framework 深度扫描

当目标仓库宣称 agent orchestration、swarm coordination、AI 军团协作、Claude Code/Codex integration、MCP tool hub、agent federation、self-learning agent platform 时，必须把“宣传的群智能”拆成三类证据：真实执行路径、协作状态账本、安全/供应链边界。

最低要求：固定 commit；统计 repo/代码/skills/commands/plugins/MCP surface；阅读 README、STATUS/USERGUIDE、verification/witness docs、install/postinstall scripts、CLAUDE.md/AGENTS.md/.agents/.claude；检查 `agent_spawn`/`task_assign`/swarm/consensus/federation 是否真的执行、跨进程/跨节点，还是只写本地 metadata/EventEmitter/stub。

默认三视角评审：
- Architecture: runtime topology、CLI/MCP/tool registry、agent lifecycle、memory/source-of-truth、provider/router/cost、与 Hermes memory/multi-model/cron/skills/gateway 的重叠。
- Security/supply-chain: `curl|bash`、`npx @latest`、global install、postinstall/native deps、terminal/browser/GitHub/auto-install tool surface、secret forwarding、remote MCP auth、federation crypto/trust 是否真实现。
- Product/workflow: named agents、typed mailbox、lead-authoritative plan、complexity routing、budget preflight、local brain learning loop、hook lifecycle、tool group gating。

结论优先选择 Hermes-native selective extraction，而不是整体安装。P0 借鉴通常是 capability witness、claim/lease/handoff ledger、budget/hop circuit breaker；P1 才是 typed SendMessage、AIDefence-lite、lazy-load/tool inventory；federation 和第二记忆栈默认暂缓。

详细 checklist 和 ruvnet/ruflo 审计经验见 `references/agent-orchestration-repo-audit.md`。

Agent Reach 这类“互联网能力 installer + doctor + routing skill”仓库的 Hermes 对照案例见 `references/agent-reach-hermes-selective-adoption.md`。默认姿态：不安装第二套栈；选择性借鉴 capability doctor、intent-to-tool routing matrix、setup dry-run/safe-mode UX、secret permission doctor、docs/capability drift lint。

### 1.5 Agentic Development Environment / AI IDE 深度扫描

当目标仓库是 AI IDE、agentic terminal、coding agent、自动化开发平台，或用户问“对 Hermes 自身有什么提升”时，除 README/package/核心代码外，必须额外检查这些信号源：

```bash
# Agent-readable context / repo-local skills / workflows / specs
git ls-files 'AGENTS.md' 'WARP.md' 'CLAUDE.md' '.agents/**' '.claude/**' '.warp/**' 'specs/**' '.github/**'

# GitHub automation and agent loops
find .github/workflows -maxdepth 1 -type f 2>/dev/null | sort
grep -RIn "ready-to-spec\|ready-to-implement\|plan-approved\|agent\|review.json\|triage\|spec" .github .agents .warp specs 2>/dev/null | head -200

# Ownership/routing and release gates
git ls-files '.github/STAKEHOLDERS' 'CODEOWNERS' 'resources/channel-gated-skills/**' 2>/dev/null
```

重点识别并映射到 Hermes 原生能力：
- **Spec-first 链路**: `PRODUCT.md` + `TECH.md` + implementation 同 PR 同步 → 映射到 Hermes `specs/<feature>/` 与 P10/P9/Loop。
- **Issue → spec → plan-approved → implementation → review**: GitHub labels + workflows + human approval gates → 映射到 Hermes cron/webhook/GitHub skills。
- **Structured review artifacts**: `review.json`、annotated diff、禁止 agent 直接发布评论 → 映射到 Hermes 多模型 review/cross-patch 的可审计输出。
- **Repo-local skill specialization**: `specializes:` 或项目覆盖层 → 映射到 Hermes core skill + project-local overlay，避免复制整套 skill。
- **Agent-readable repo context**: `WARP.md`/`AGENTS.md`/`.agents/skills` → 映射到 Hermes repo 根上下文与 contributor guide。
- **Feature/channel gating**: dogfood/preview/stable、channel-gated skills、flag lifecycle → 映射到 Hermes tools/skills/gateway adapters 的灰度发布。
- **Ownership routing**: `.github/STAKEHOLDERS` 或 CODEOWNERS 扩展 → 映射到 Hermes issue/PR triage 的 SME 路由。
- **External CLI agent registry**: Claude/Codex/Gemini/OpenCode/Copilot/Cursor 等检测与 skill provider 兼容 → 映射到 Hermes delegation/external-agent registry。
- **Verification artifacts**: integration test screenshots/videos/traces/transcripts → 映射到 Hermes gateway/browser/TUI/cron 的 replayable artifacts。
- **Telemetry/privacy rules**: UGC/secrets 标记、payload 最小化 → 映射到 Hermes tool/gateway/memory telemetry 边界。

这类评估的默认结论通常是“选择性借鉴方法论，不复制代码”：大型 AI IDE 往往深度绑定语言、UI runtime、云端服务和许可证；高价值部分多在工作流、治理、review artifact、发布门禁和 agent-readable context。

### 1.6 GUI / Computer-Use Agent 深度扫描

当目标仓库是 desktop GUI agent、computer-use agent、visual grounding agent、pyautogui/Accessibility 自动化框架，或像 Agent-S 一样提供 `agent_s` / OpenClaw wrapper / GUI skill 时，必须使用 `references/gui-computer-use-agent-audit.md`。默认结论优先是 Hermes-native selective extraction，不整体引入运行时：先固定 commit/license/package entry point，再读 README、CLI/wrapper、grounding/ACI、action primitive、local code/bash env、trajectory/judge/bBoN、CI/benchmark 证据。

重点证据字段：screen/OCR/grounding preflight、单显示器/分辨率假设、Accessibility/Input Monitoring/clipboard 权限、shell/Python/code execution 是否 default-off、有无 `eval`/free-form action code、日志是否持久化 screenshot/command/API key、timeout/step budget/interrupt、fact-caption/trajectory/judge artifact 是否可复核。

可借鉴方向：capability doctor、typed GUI action contract、trajectory reflection/drift reviewer、behavior best-of-N evidence schema、多轨迹 comparative judge。禁止在未做 sandbox/permission/log-redaction certification 前，把外部 GUI agent 作为 Hermes 自动执行器直接安装或调用。

### 1.7 Agent Proxy / Quota Router 深度扫描

当目标仓库是 local AI proxy、multi-account/token manager、provider router、quota/rate-limit manager、model remapper、OAuth/token pool、协议兼容层，或用户问“对 Hermes 多模型/路由/额度/gateway 自身有什么优化”时，必须把它和 Hermes 现有 `quorum.yaml`、`consult_models.py`、`model_quota.py`、`model_health.py` 对照，而不是只看 README。

最低要求：固定 commit 和 license；阅读 proxy config、token/account manager、rate_limit、monitor/stats、sticky/session、model mapping、auth/API docs；搜索 `quota|rate_limit|retry-after|reset|sticky|health_score|remaining_quota|mapped_model|token|account|oauth|monitor|circuit`；运行或检查 Hermes consult status / quota snapshot。

默认结论优先是 Hermes-native selective extraction：
- P0: quota confidence-gated routing、reset-aware provider/model lockouts、routing decision ledger。
- P1: capability-aware model mapping、known-exhausted quorum skip、conversation/model affinity。
- P2: protocol compatibility regression suite、config/gateway sync selfcheck、license firewall。

如果多模型 consult 给出 weak consensus / truth_not_certified，只能作为建议池；最终报告必须引用已读文件证据。对非商业/share-alike license 的仓库，默认 clean-room 提炼模式，禁止复制源码进入 Hermes，除非单独 license review。

详细 checklist 见 `references/agent-proxy-quota-router-audit.md`。

### 1.8 Official API/Admin CLI 深度扫描

当目标是官方 API CLI、admin CLI、provider usage/quota CLI，或用户问“这个 CLI 是否能补齐 Hermes/provider 自动化”时，不要把它当普通 agent 框架处理。先确认它是 API/admin CLI、coding-agent CLI、SDK bin，还是同名旧包；固定 repo/release/checksum；解析源码 command registry；检查 admin key、org/project scope、debug body logging、base-url/proxy、PATH binary 冲突；默认先沙箱评估，不安装、不写全局密钥。详细 checklist 见 `references/official-api-cli-audit.md`。

### 1.9 Provider Usage Telemetry / Token Accounting 深度扫描

当目标仓库是 token usage tracker、本地 JSONL 用量解析器、pricing/cost estimator、quota/statusline/live usage 工具，或用户问“能不能补齐 Hermes provider-quota / model routing 可观测性”时，使用 `references/provider-usage-telemetry-repo-audit.md`。重点不是整体引入 CLI/TUI/GUI，而是 clean-room 提取：redaction gate、本地 usage parser、增量 cache、pricing cache、默认关闭的 official quota probe、consult routing decision ledger。任何 credential/auth/official quota 表面都必须 redaction-first，且 not-certified 多模型产物只能进 taskpool advisory，不能直接授权实现。

### 1.10 兼容性检查

| 检查项 | 方法 | 不兼容处理 |
|--------|------|-----------|
| 运行时兼容性 | 检查是否绑定特定 IDE/CLI | 评估适配成本 |
| 路径硬编码 | 搜索 `.claude/` 等特定路径 | 批量替换为 Hermes 路径 |
| 依赖项 | `package.json` dependencies | 检查本地是否已安装 |
| Node 版本 | `engines.node` | 确认 >= 系统版本 |
| 术语冲突 | 检查与现有 skill 的重叠命名 | 统一术语或保留原名 |

---

## Phase 2: 多维度分析

### 2.1 对比分析矩阵

| 维度 | 当前工作流 | 新框架 | 差异评估 |
|------|-----------|--------|---------|
| 目标场景 | | | |
| 架构模式 | | | |
| 规模 | | | |
| 运行时 | | | |
| 验证体系 | | | |
| 迭代模式 | | | |
| 社区/维护 | | | |
| 引入成本 | — | — | 高/中/低 |

### 2.2 引入价值评估

**评分制（1-10）**：

| 维度 | 权重 | 评分标准 |
|------|------|---------|
| 理念互补性 | 25% | 是否填补了现有体系的空白 |
| 技术可集成性 | 20% | 能否与现有 skill 协同工作 |
| 维护成本 | 20% | 引入后的持续维护工作量 |
| 运行时兼容性 | 15% | 是否需要改变现有工作方式 |
| 社区活跃度 | 10% | Star 数、更新频率、贡献者 |
| 文档质量 | 10% | 是否易于理解和使用 |

**总分 = Σ(维度分 × 权重) / 10**，满分 100

**决策阈值**：
- >= 80: 值得整体引入（但需分阶段）
- 60-79: 选择性借鉴组件
- < 60: 仅做参考，不引入

### 2.3 冲突分析

**常见冲突类型**：

1. **运行时冲突** — 框架依赖特定 CLI/IDE
   - 处理: 评估适配成本，或使用兼容层

2. **理念冲突** — 框架是"一套系统统治所有" vs 现有是"自由组合"
   - 处理: 提取可复用组件，放弃整体架构

3. **规模冲突** — 框架 9MB+ vs 现有轻量级生态
   - 处理: 只引入核心文件，忽略示例/文档/测试

4. **目标冲突** — 框架为"构建项目"设计 vs 现有为"进化 Agent"
   - 处理: 明确分工，不重叠使用

---

## Phase 3: 引入决策

### 3.1 决策树

```
总分 >= 80?
  ├─ 是 → 是否改变现有工作方式?
  │       ├─ 是 → 分阶段引入，先试点
  │       └─ 否 → 全局安装，逐步迁移
  └─ 否 → 总分 >= 60?
          ├─ 是 → 选择性借鉴（见 Phase 4）
          └─ 否 → 仅做参考，不引入
```

### 3.2 决策输出格式

```
═══════════════════════════════════════════════════════════════════
                    评估结论: {整体引入 / 选择性借鉴 / 不引入}
═══════════════════════════════════════════════════════════════════

评分: {X}/100 ({A/B/C/D} 级)

建议行动:
  1. {具体行动}
  2. {具体行动}

风险:
  - {风险1} → 缓解: {措施}
  - {风险2} → 缓解: {措施}

如果选择选择性借鉴，推荐组件:
  1. {组件1} → 引入方式: {方式} → 成本: {高/中/低}
  2. {组件2} → 引入方式: {方式} → 成本: {高/中/低}
```

---

## Phase 4: 选择性借鉴

当决定不整体引入时，从框架中提取高价值组件：

### 4.1 组件提取流程

```
Step 1: 识别核心组件
  → 列出框架的所有子系统（workflow/agent/command/hook）
  → 评估每个子系统的独立价值

Step 2: 评估可移植性
  → 该组件是否依赖框架的其他部分？
  → 提取后能否独立工作？
  → 与现有 skill 的集成成本？

Step 3: 设计集成方案
  → 直接引入为独立 skill
  → 融入现有 skill 的 references/ 目录
  → 作为方法论写入现有 skill

Step 4: 最小可行集成
  → 提取核心逻辑（通常 < 300 行）
  → 适配到 Hermes 环境
  → 保留原框架的引用和署名
```

### 4.2 常见借鉴模式

| 原框架组件 | 借鉴方式 | 集成目标 |
|-----------|---------|---------|
| Wave Execution | 修改 loop skill | 迭代并行化 |
| Context Engineering | 融入 cognitive-load-agent | Context 预算优化 |
| Verification Workflow | 增强 post-deploy-verification | 验证闭环 |
| Agent Routing | 新建 dispatcher skill | 智能命令路由 |
| Agent Design Pattern | 阅读借鉴 | Skill 升级参考 |

---

## Phase 5: 集成与验证

### 5.1 安装步骤

**全局安装**（适用于可独立运行的 CLI 工具）：
```bash
npx <package>@latest --<runtime> --global
# 或从源码构建
npm run build:sdk
node bin/install.js --<runtime> --global
```

**本地集成**（适用于 skill/agent 文件）：
```bash
# 1. 复制到 Hermes skill 目录
cp -r <repo>/agents/* ~/.hermes/skills/
# 2. 适配路径和术语
# 3. 初始化追踪文件
touch ~/.hermes/skills/<skill-name>/results.tsv
```

### 5.2 安装后验证

```bash
# 1. 检查文件是否到位
ls ~/.claude/skills/ | grep "<prefix>" | wc -l

# 2. 检查 SDK 是否可用
<sdk-command> --version

# 3. 检查配置文件是否正确加载
# 4. 执行一次完整工作流测试
```

### 5.3 常见安装问题

| 问题 | 原因 | 解决 |
|------|------|------|
| SDK dist 不存在 | 未运行 build:sdk | `cd sdk && npm ci && npm run build` |
| Hooks 缺失 | build:hooks 未执行 | `npm run build:hooks` |
| 路径权限拒绝 | MCP filesystem 沙盒 | 使用 terminal 工具替代 |
| 运行时找不到 | 未在 PATH 中 | `npm link` 或绝对路径调用 |
| 术语冲突 | 与现有 skill 命名重叠 | 重命名或添加命名空间 |

---

## 输入输出规范

### 输入

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `repo_url` | string | 是 | GitHub 仓库 URL 或 npm 包名 |
| `action` | enum | 是 | `analyze` / `decide` / `integrate` |
| `scope` | enum | 否 | `full` / `selective` / `reference-only` |
| `components` | string[] | 否 | 指定要分析的子系统（selective 时必填）|

### 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| `score` | float | 0-100 引入价值评分 |
| `grade` | enum | A/B/C/D |
| `decision` | enum | adopt / selective / reject |
| `components` | object[] | 各子系统的评分和建议 |
| `risks` | object[] | 风险列表 + 缓解措施 |
| `integration_plan` | string[] | 集成步骤（如 decision=adopt/selective）|

---

## 使用方式

### 评估一个 GitHub 仓库
```
用户: "分析 https://github.com/xxx/yyy 是否值得引入"
→ Phase 1-3 完整流程
→ 输出: 评分 + 决策 + 风险 + 建议行动
```

### 选择性借鉴组件
```
用户: "从 GSD 中提取 wave execution 概念"
→ Phase 1 (快速扫描) + Phase 4 (组件提取)
→ 输出: 提取方案 + 集成步骤 + 成本评估
```

### 技术选型对比
```
用户: "对比 GSD vs Taskmaster vs OpenSpec"
→ 对多个框架执行 Phase 1-2
→ 输出: 对比矩阵 + 推荐方案
```

---

## 与现有体系集成

### 与 darwin-skill 集成
- 引入价值评分中的 "理念互补性" 使用 Darwin 的 8 维度 rubric 评估
- 组件提取后的 skill 直接进入 Darwin 优化循环

### 与 bayesian-agent 集成
- 引入决策的置信度随实际使用效果更新
- 高评分但实际效果差 → beta 增加，降级决策

### 与 p10 集成
- 框架引入属于战略决策，需 P10 审查
- 大规模引入（>50 个文件）需单独规划

---

## 选择性借鉴 → Hermes 原生实现 (Phase 6)

当评分在 60-79 区间决定"选择性借鉴"时，不是直接 fork 代码，而是：

### 6.1 方法论提取
1. 阅读目标仓库的核心 SKILL.md / 提示词 / 工作流
2. 剥离其基础设施依赖（如 gstack 的 ~/.gstack, Claude Code preamble scripts）
3. 提取纯方法论：触发条件、分级标准、验证清单、工作流阶段
4. 识别 Hermes 现有工具的对应映射

### 6.2 双脑翻译
1. 将方法论描述 + Hermes 约束 封装为 state.json
2. 发送给 Claude Code：`claude -p "Design Hermes-native equivalent of <methodology>"`
3. Claude Code 产出完整的 SKILL.md（YAML frontmatter + markdown body）
4. 验证：仅用 Hermes 原生工具（browser_*, terminal, read_file, write_file, patch）

### 6.3 落地验证
1. 创建 ~/.hermes/skills/<name>/SKILL.md
2. 验证：触发词、model 推荐、步骤完整性、verification checklist
3. self-test 确认系统无回归
4. 对比原版：功能覆盖率、依赖数、模型绑定、许可证差异

### 案例: gstack 选择性借鉴
- 评分: 62/100 → 选择性借鉴
- 提取: browser-qa (QA 方法论), design-audit (视觉审查), ship (发布管线)
- 原版依赖: Claude Code + ~/.gstack + 95MB
- Hermes 版: 3 个 SKILL.md, 总共 8.8KB, 零新依赖, 10 模型通用
- 关键原则: 不复制代码, 不引入运行时依赖, 不绑定特定模型

## 输出物

- 评估报告（本次分析的结构化输出）
- 集成计划（如决定引入）
- 风险登记册
- 组件提取方案（如选择性借鉴）
- Hermes 原生 skill（如 Phase 6 触发）

如果本次评估产出了新的 Hermes 原生 artifact（skill / script / spec / workflow），后续治理与留痕应移交给 `private-fork-evolution-governance`：补 evolution note、verification 证据与 upgrade-survival 检查，而不是把评估报告当成完整闭环。

## 约束

- 遵循项目规范
- 在 context budget 内完成

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

