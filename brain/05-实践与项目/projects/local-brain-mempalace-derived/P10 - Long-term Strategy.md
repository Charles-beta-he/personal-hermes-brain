---
type: strategy
layer: L2
status: active
created: 2026-05-06T18:07:23+08:00
project: local-brain-mempalace-derived
p10_status: no_blocker_after_deterministic_gate
---

# P10 - Long-term Strategy: MemPalace-derived Local Brain

## Strategic thesis

Markdown vault remains the canonical source of truth。

MemPalace is a derived retrieval layer, not the brain hierarchy。

本地大脑的主层级继续由 `00-索引 / 01-10 理论与实践 / 20-projects / 30-tasks / 40-skills / 50-prefs / 60-reviews / 99-hermes-notes` 承担。MemPalace 的价值只被吸收为四个架构原语：

1. L0-L3 唤醒分层：把始终加载、当前状态、按需 MOC、深度全文检索分离。
2. Drawer / Closet：原文证据与有损摘要/索引分离。
3. Tunnel / graph：目录树之外的横向联系。
4. Temporal facts：事实有效期、来源指针、置信度，降低 ghost memory。

## Architecture principles

### P0 invariants

- Canonical: `/Users/charles/Documents/brain`。
- Derived indexes: `~/.hermes/memory/`、未来 SQLite/Chroma/closet cache 均可重建。
- do not run mempalace init on the canonical vault。
- local-first：默认不用外部 LLM，不外发 brain 内容。
- 摘要不可替代原文；任何 summary/closet/atom 必须能回指 evidence/source。

### Layer mapping

| MemPalace idea | Hermes local-brain mapping | Authority |
|---|---|---|
| L0 Identity | `50-prefs` + stable system constraints | stable but editable preference/evidence note |
| L1 Essential Story | `00-索引/00-大脑索引.md` + `06-仪表盘` | MOC summary, not fact source |
| L2 On-demand | each folder `00-...索引.md` | topic router |
| L3 Deep Search | `brainctl search/evidence` + full Markdown | original evidence |
| Drawer | `09-引用原文` / logs / source excerpts | highest local evidence |
| Closet | `00-索引` / derived cards / short pointers | lossy index only |
| Temporal KG | future SQLite facts table with valid_from/valid_to/source | derived governance layer |

## P10 stop gate

P10 策略判定为无 blocker 需要满足：

1. 主系统权威边界明确：Markdown vault remains source of truth。
2. MemPalace runtime 不进入生产路径；如试验只能隔离样本 + independent palace path。
3. P9 backlog 和 playbook 覆盖 P0/P1/P2，且每项有验收命令。
4. review note 记录多模型结果 caveat；model agreement is not evidence。
5. self-check、sync、reindex、search、structural audit 均通过。

## Phases

### P0: Contract landing / no runtime adoption

本轮已落地项目、策略、backlog、playbook、review、task ledger、evolution、atoms、自检脚本。

### P1: Optional isolated experiment

只复制 5-20 篇非敏感样本，使用：

```bash
mempalace --palace /tmp/brain-palace init /tmp/brain-sample --no-llm --yes
mempalace --palace /tmp/brain-palace mine /tmp/brain-sample --mode projects
```

验收只比较检索质量，不把 palace 写回 canonical vault。

### P2: Hermes-native derived index

若 P1 有净收益，优先实现 `brainctl derived-index`，而不是长期依赖 MemPalace runtime。

## Top risks and mitigations

| Risk | Severity | Mitigation |
|---|---:|---|
| 第二事实源导致旧内容被误召回 | 5 | canonical vault invariant + rebuildable derived cache |
| 有损摘要被误当证据 | 4 | Drawer/Closet rule + evidence-boundary atom |
| 外部 LLM 泄露本地脑内容 | 4 | local-first default, no external calls in self-check |
| 中文/中英 embedding 效果不稳定 | 3 | isolated query benchmark only, no production dependency |
| 多模型认证超时/格式失败被误宣传 | 3 | review note 标注 not_certified，P10 只以 deterministic gate 收敛 |

## Decision log

- 选择 Hermes-native landing，不整体引入 MemPalace runtime。
- 选择文档 + 自检脚本 + proof ledger 先落地，避免一上来建新数据库造成双源漂移。
- 选择保留未认证 caveat，因为本轮 `consult_models.py --discussion` 超时，DeepSeek seed JSON 解析失败。
