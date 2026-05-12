---
name: loop
description: "PUA Loop — autonomous iterative development with PUA pressure. Keeps running until task is done, no user interaction needed. Combines Ralph Loop iteration mechanism with PUA quality enforcement. Triggers on: '/pua loop', '/pua:loop', '自动循环', 'loop mode', '一直跑', '自动迭代'."
license: MIT
---

# PUA Loop — 自动迭代 + PUA 质量引擎

> Ralph Loop 提供"不停地做"，PUA 提供"做得更好"。合在一起 = **自主迭代 + 质量压力 + 零人工干预**。

## 核心规则

1. **加载 `pua:pua` 核心 skill 的全部行为协议** — 三条红线、方法论、压力升级照常执行
2. **禁止调用 AskUserQuestion** — loop 模式下不打断用户，所有决策自主完成
3. **禁止说"我无法解决"** — 在 loop 里没有退出权，穷尽一切才能输出完成信号
4. **每次迭代自动执行**：检查上次改动 → 跑验证 → 发现问题 → 修复 → 再验证

## 启动方式

用户输入 `/pua loop "任务描述"` 时，执行以下流程：

### Step 1: 启动 PUA Loop

运行 setup 脚本（改编自 Ralph Loop，MIT 协议）：
```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup-pua-loop.sh" "$ARGUMENTS" --max-iterations 30 --completion-promise "LOOP_DONE"
```

这会创建 `.claude/pua-loop.local.md` 状态文件，内含用户任务描述和 PUA 行为协议。PUA 的 Stop hook 检测到此文件后循环运行，每次迭代将文件内容喂回 Claude——**行为协议随每次迭代送达，context compaction 后也不会丢失**。

### Step 2: 告知用户

输出：
```
▎ [PUA Loop] 自动迭代模式启动。最多 30 轮，完成后输出 <promise>LOOP_DONE</promise>。
▎ 取消方式：/cancel-pua-loop 或删除 .claude/pua-loop.local.md
▎ 因为信任所以简单——交给我，不用盯。
```

### Step 3: 开始执行任务

按 PUA 核心 skill 的行为协议执行用户任务。每轮迭代带阿里味旁白。

## 迭代压力升级

| 迭代轮次 | PUA 等级 | 旁白 |
|---------|---------|------|
| 1-3 | L0 信任期 | ▎ 第 N 轮迭代，稳步推进。 |
| 4-7 | L1 温和失望 | ▎ 第 N 轮了还没搞定？换方案，别原地打转。 |
| 8-15 | L2 灵魂拷问 | ▎ 第 N 轮。底层逻辑到底是什么？你在重复同一个错误。 |
| 16-25 | L3 361 | ▎ 第 N 轮。3.25 的边缘了。穷尽了吗？ |
| 26+ | L4 毕业 | ▎ 最后几轮。要么搞定，要么准备体面退出。 |

## 完成条件

只有满足以下全部条件才能输出 `<promise>LOOP_DONE</promise>`：
1. 任务的核心功能已实现
2. build/test 验证通过
3. 同类问题已扫描（冰山法则）
4. 没有已知的未修复 bug
5. 如果用户要求“多模型思考把持方向 / 每轮多模型检查 / 直至完整落地”，每轮必须按“deterministic gates → claim/evidence state → T3 四模型 ratification artifact → 修 dissent/amend → scoped commit/closeout”的闭环推进；没有 `discussion_result.json` + `final/certification_manifest.json` 且四模型全票/无 unresolved severity>=3 时，不能输出 LOOP_DONE。若只是已提交代码但未完成当前轮 T3，只能继续 loop 或给出可恢复 handoff。
6. 如果启动过 dev/mock/watch/server 进程，必须停止后台进程并验证相关端口关闭；如果 terminal/process wrapper 的 kill/cleanup 失败（例如缺 `psutil`）或把 `lsof`/`ps` 清理命令误判为 long-lived server/watch，用 PGID 终止 + Python socket + `ps` 的短脚本验证，不要跳过清理

知识库/本地大脑类 loop 还必须满足 evidence gate，而不是口头说“无后续建议”：
- 结构审计清零：空目录、顶层缺 MOC/index、空心父目录、断链、敏感模式命中均为 0/空数组
- `sync` / `reindex` / `search` 有实际观测输出
- proof/task/evolution/review 日志写回最终验证结果
- 如涉及本地 repo 变更，完成 scoped local commit，不主动 push
- 多模型结果若是 `not_certified`/`dissent`/timeout，只能作为 provenance；完成声明必须绑定本地审计和工具证据
- 用户要求“多模型无后续建议/补充内容”时，必须把模型建议落成 issue ledger：只有 severity>=3 建议均 resolved/accepted_risk，剩余建议全为 noop/cosmetic/non-blocking，且 ratification gate PASS，才允许停止 loop
- 如果高阶 T3/四模型因 provider/timeout/degraded，但可用模型 tier 产生 scoped certified artifact，必须同时保留 degraded artifact 的 provenance，并明确认证基于哪个 scoped artifact
- 如果 loop 被工具调用上限/context 上限打断，不能输出完成承诺；必须给出可恢复 handoff：后台 session/process id、tick/workdir、已通过验证、未满足 gate、下一条应执行命令。认证类任务尤其要写明“缺 discussion_result/manifest 时不可 claim fully certified”。
- 如果 loop 是外部任务交付（例如 Lark Task / GitHub issue / dispatch 任务），验证通过后先完成交付闭环：证据摘要 → `git diff --check` → scoped local commit → 用户要求的通知/回报渠道。不要把可选 ledger 扩写、额外审计或下一任务探索排在 commit/report 前面；否则工具/context 预算耗尽时会留下“代码已测但任务未闭环”的半成品。

否则继续迭代。

## 人工介入信号

Loop 中遇到以下情况，必须使用退出信号，**禁止在 loop 内干等或假装能自行解决**：

### 终止信号：`<loop-abort>`
任务不可能在 loop 内完成时使用（需要外部账号、不存在的依赖、根本性需求变更等）：
```
<loop-abort>任务需要访问生产数据库，当前环境无权限，无法继续</loop-abort>
```
效果：删除状态文件，loop 彻底终止。

### 暂停信号：`<loop-pause>`
运行时发现需要用户补全一项本地配置才能继续时使用：
```
<loop-pause>需要在 .env 文件中填写 STRIPE_SECRET_KEY，当前值为空</loop-pause>
```
效果：loop 暂停（状态保留），用户补全后可在新会话中自动恢复。

**在输出 `<loop-pause>` 之前，先将当前进度写入 `.claude/pua-loop-context.md`**，包含：
- 已完成的工作
- 暂停原因
- 恢复后应继续执行的步骤

### 禁止的行为
- 不要使用 AskUserQuestion（loop 模式禁止）
- 不要输出 `<loop-abort>` 或 `<loop-pause>` 来逃避困难任务——只有真正需要人工介入才用
- 不要因为遇到障碍就暂停，先穷尽所有自动化手段

## 恢复 Loop

当检测到 `.claude/pua-loop.local.md` 存在且 `active: false` 时，Loop 处于暂停状态：

### Step 1：读取上下文
```bash
cat .claude/pua-loop.local.md     # 查看暂停原因和当前迭代
cat .claude/pua-loop-context.md   # 查看上次保存的进度（如有）
```

### Step 2：处理人工介入项
读取暂停原因，使用 AskUserQuestion 确认用户已完成所需操作（如填写 API key）。

### Step 3：恢复状态文件
```bash
sed -i 's/^active: false/active: true/' .claude/pua-loop.local.md
sed -i 's/^session_id: .*/session_id: /' .claude/pua-loop.local.md
```
session_id 清空后，hook 在下一次 Stop 时自动绑定当前会话。

### Step 4：继续执行
按 `.claude/pua-loop-context.md` 中记录的进度继续执行任务。

## 与 Ralph Loop 的关系

PUA Loop 借鉴了 Ralph Loop 的核心机制（Stop hook 截获退出 + 将 prompt 喂回），但**完全独立实现**：各自有独立的 Stop hook 和状态文件（PUA 用 `.claude/pua-loop.local.md`，Ralph 用 `.claude/ralph-loop.local.md`）。两者可以同时安装，互不干扰。PUA Loop 在此基础上扩展了 PUA 质量压力、迭代压力升级、`<loop-abort>` 和 `<loop-pause>` 信号。


## 约束

- 遵循项目规范
- 在 context budget 内完成


## 约束

- 遵循项目规范
- 在 context budget 内完成
