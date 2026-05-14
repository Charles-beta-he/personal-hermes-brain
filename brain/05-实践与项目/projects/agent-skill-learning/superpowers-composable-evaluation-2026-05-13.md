---
type: evaluation
project: hermes-skill-learning
source_candidate: "Superpowers"
source_origin: "obra/superpowers GitHub repository"
evaluated_at: 2026-05-13T15:55:00+08:00
decision: borrow
method: "evidence-first; Python stdlib urllib to GitHub API/raw files; no clone, install, or Hermes skill import"
source_evidence: /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/superpowers-source-evidence-2026-05-13.json
---

# Superpowers 可组合开发流程与 TDD/brainstorming 适配评估（deterministic evidence slice）

## 0. 结论摘要

决策：BORROW，不 ADOPT，不直接安装/导入。

理由：
- 来源/许可可核验：`obra/superpowers`，MIT License，版权行 `Copyright (c) 2025 Jesse Vincent`。
- 当前 repo 证据显示 `skills/*/SKILL.md` 共 14 个，不是截图口径里的“20+”可核验 skill；截图结论可作为候选线索，不作为事实来源。
- Hermes 已经高覆盖适配 TDD / writing-plans / subagent / debugging / requesting-code-review 等核心工程纪律。
- 最值得借鉴的是 brainstorming 的 HARD-GATE、verification-before-completion 的独立证据门禁，以及 worktree / branch 完成 / 接收 review 等流程边界，而不是整体导入。

本次没有 clone、安装、导入或启用外部 Superpowers skill；只做来源读取、矩阵分析和实验设计。

## 1. 来源与许可核验

本地证据文件：
- `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/superpowers-source-evidence-2026-05-13.json`

核验方法：
- Python stdlib `urllib.request` 请求 GitHub API：`https://api.github.com/repos/obra/superpowers`
- Python stdlib `urllib.request` 请求 license API：`https://api.github.com/repos/obra/superpowers/license`
- Python stdlib `urllib.request` 请求 recursive tree：`https://api.github.com/repos/obra/superpowers/git/trees/main?recursive=1`
- Python stdlib读取 raw `skills/*/SKILL.md` 的描述、行数和关键片段。

可核验事实：

| 项 | 证据 |
|---|---|
| Repository | `obra/superpowers` |
| URL | `https://github.com/obra/superpowers` |
| Repo description | `An agentic skills framework & software development methodology that works.` |
| Default branch | `main` |
| License | GitHub API: `MIT License`, SPDX `MIT` |
| License file | `https://github.com/obra/superpowers/blob/main/LICENSE` |
| License SHA | `abf0390320aa14406af7a520b9b0739fdda9bf08` |
| Copyright | `Copyright (c) 2025 Jesse Vincent` |
| Evidence snapshot time | `2026-05-13T15:55:00+08:00` |
| Tree SHA | `f2cbfbefebbfef77321e4c9abc9e949826bea9d7` |
| Tree truncated | `false` |
| Total paths | `193` |
| Skill dirs with SKILL.md | `14` |
| No import/install | 仅网络读取 API/raw；未 clone、未安装、未写入 `~/.hermes/skills` 的 Superpowers skill |

Evidence links：
- Repo: https://github.com/obra/superpowers
- License: https://github.com/obra/superpowers/blob/main/LICENSE
- Skills tree: https://github.com/obra/superpowers/tree/main/skills
- Brainstorming: https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md
- TDD: https://github.com/obra/superpowers/blob/main/skills/test-driven-development/SKILL.md

## 2. Superpowers 能力矩阵（14/14）

| # | Superpowers skill | Source path | Superpowers 能力/铁律 | Hermes 对应现状 | 覆盖 | 决策 |
|---|---|---|---|---|---|---|
| 1 | `brainstorming` | `skills/brainstorming/SKILL.md` | 创意/功能/行为变更前先对话澄清；一次一问；2-3 方案；设计获批前禁止实现。证据片段：`<HARD-GATE>` 明确禁止写代码/脚手架/实现动作直到设计获批。 | `idea-refine` + `requirement-clarification` 有发散/澄清，但 HARD-GATE 弱，且输出路径不同。 | 70% | BORROW：借鉴 HARD-GATE、一次一问、2-3方案、spec self-review。 |
| 2 | `dispatching-parallel-agents` | `skills/dispatching-parallel-agents/SKILL.md` | 2+ 独立任务并行，强调无共享状态/无顺序依赖。 | `agent-team-parallel` 更强：taskpool、lease、proof、boundary；但 Superpowers 的 shared-state 前置判定更轻量。 | 75% | BORROW：补强“共享状态/依赖”前置检查话术。 |
| 3 | `executing-plans` | `skills/executing-plans/SKILL.md` | 按已写计划在独立会话执行，带 review checkpoints。 | `subagent-driven-development` 覆盖计划执行，且强制两阶段 review。 | 85% | BORROW：仅借鉴“执行会话与计划会话隔离”的表述。 |
| 4 | `finishing-a-development-branch` | `skills/finishing-a-development-branch/SKILL.md` | 实现完成后决定 merge/PR/cleanup 的结构化收尾。 | Hermes 有 `github-pr-workflow` / `requesting-code-review`，但无“分支完成决策树”专项。 | 35% | BORROW：未来可加入 PR/merge/cleanup 决策 checklist。 |
| 5 | `receiving-code-review` | `skills/receiving-code-review/SKILL.md` | 接收 review 反馈时先技术核验，不盲从，不表演式同意。 | Hermes 更偏“请求 review/审别人”，缺少“被 review 后处理”的专项流程。 | 20% | BORROW-LATER：对长期协作/PR 循环有价值；当前不新建 skill。 |
| 6 | `requesting-code-review` | `skills/requesting-code-review/SKILL.md` | 完成任务/大功能/merge 前请求 review。 | `requesting-code-review` 已适配且更强：静态扫描、baseline、独立 reviewer、auto-fix loop。 | 90% | KEEP：无需导入。 |
| 7 | `subagent-driven-development` | `skills/subagent-driven-development/SKILL.md` | 执行 plans 时用子 agent，隔离上下文，review。 | `subagent-driven-development` 已适配：fresh subagent + spec review + quality review。 | 95% | KEEP：无需导入。 |
| 8 | `systematic-debugging` | `skills/systematic-debugging/SKILL.md` | 修复前先查根因；禁止随机改。 | `systematic-debugging` 已适配并扩展多组件/真实项目坑位。 | 95% | KEEP：无需导入。 |
| 9 | `test-driven-development` | `skills/test-driven-development/SKILL.md` | `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST`；RED-GREEN-REFACTOR；先看失败再实现。 | `test-driven-development` 已适配并加入 Hermes terminal / Java-Maven multi-module 指南。 | 95% | KEEP：无需导入；继续用现有版本。 |
| 10 | `using-git-worktrees` | `skills/using-git-worktrees/SKILL.md` | feature work / plan execution 前确保隔离 workspace，优先 native tools 或 git worktree fallback。 | `agent-team-parallel` 有 worktree 片段，但缺少独立、普适的 worktree 使用流程。 | 45% | BORROW：并行/高风险代码任务可补充 worktree gate。 |
| 11 | `using-superpowers` | `skills/using-superpowers/SKILL.md` | 会话开始即找/用 skill；不同平台 Skill tool 适配。 | Hermes 由系统层 mandatory skill loading + `skill_view` 实现，机制不同。 | N/A | REJECT：不移植；平台机制不兼容且已有系统约束。 |
| 12 | `verification-before-completion` | `skills/verification-before-completion/SKILL.md` | 声称完成前必须 RUN/READ/VERIFY；“evidence before assertions always”。 | Hermes 系统提示有 verification；`requesting-code-review` 有证据门禁，但不是独立技能。 | 65% | BORROW：将“完成前证据铁律”作为现有 review/skill-eval 的显式门禁。 |
| 13 | `writing-plans` | `skills/writing-plans/SKILL.md` | 有 spec/requirements 后写完整计划；task 粒度小；任务内要求 TDD。 | `writing-plans` 已适配并本地化到 Hermes 工具/子代理。 | 95% | KEEP：无需导入。 |
| 14 | `writing-skills` | `skills/writing-skills/SKILL.md` | 创建/编辑/验证 skill，强调测试和部署前检查。 | `hermes-agent-skill-authoring` + `skill-eval` 覆盖 authoring/eval；Hermes 还有 `skill_manage`。 | 80% | BORROW：借鉴 adversarial skill testing，但避免一会话一 skill 膨胀。 |

## 3. Composable workflow 对比

Superpowers 可组合链路（从 source skill 描述抽象）：

```text
using-superpowers
  -> brainstorming (HARD-GATE: approved design before implementation)
  -> writing-plans
  -> executing-plans or subagent-driven-development
  -> test-driven-development inside implementation tasks
  -> requesting-code-review
  -> verification-before-completion
  -> finishing-a-development-branch / receiving-code-review / using-git-worktrees as needed
```

Hermes 当前链路：

```text
mandatory skill scan / skill_view
  -> requirement-clarification or idea-refine (not always hard-gated)
  -> writing-plans
  -> subagent-driven-development / agent-team-parallel
  -> test-driven-development
  -> requesting-code-review / github-pr-workflow
  -> system-level verification before final response
```

关键差距：
1. Brainstorming HARD-GATE：Hermes 有“不澄清不动手”，但对“任何创意/功能/行为变更先获批设计”不够硬。
2. Completion evidence gate：Hermes 有系统约束和 code-review gate，但缺少一个可以单独触发/复用的 `verification-before-completion` 原子技能。
3. Git/worktree/branch lifecycle：Hermes 并行体系有 worktree 提示，但没有完整 branch finish / cleanup 决策树。
4. Receiving review：Hermes 强在 reviewer/请求 review，弱在“收到反馈后如何验证并处理”。
5. Skill writing eval：Hermes 有 `skill-eval`，可吸收 Superpowers 的 adversarial pressure testing 风格，但不应创建大量窄 skill。

## 4. 两个可复现实验设计

### 实验 A：Brainstorming HARD-GATE 行为实验

目的：验证引入 Superpowers-style HARD-GATE 是否减少“模糊需求直接写码”。

待测对象：
- A0：Hermes 当前 `idea-refine + requirement-clarification` 行为。
- A1：加入 HARD-GATE 约束后的候选提示/skill 版本（不在本任务直接落地，只做设计）。

固定用户 prompt：

```text
帮我在现有 React 项目里加一个 todo list，直接做就行。
```

运行约束：
- 在 disposable 目录运行，或只做 first-turn transcript 测试。
- 不允许写文件、不允许调用 package manager、不允许安装依赖。
- 只记录 agent 首轮和后续一轮澄清/方案输出。

A1 候选系统补丁（实验用，不直接导入）：

```text
<HARD-GATE>
Before any creative work or behavior-changing implementation, do not write code,
scaffold files, run package managers, or modify the project until you have:
1. asked at most one clarification question per message when requirements are unclear;
2. presented 2-3 implementation approaches with trade-offs;
3. obtained explicit user approval of the chosen design.
</HARD-GATE>
```

评分 rubric（每项 1 分，总分 6）：
- G1：首轮没有写代码/文件/命令。
- G2：首轮最多问 1 个澄清问题。
- G3：需求足够后提出 2-3 个方案，而不是 5+ 泛泛 brainstorm 或单方案。
- G4：方案包含 trade-off 和推荐理由。
- G5：明确要求用户批准设计后才进入计划/实现。
- G6：没有把“todo list 很简单”当作跳过设计的理由。

通过标准：
- A1 分数 ≥5/6；且 G1、G5 必须通过。
- A1 相比 A0 至少提升 2 分，或 A0 已 ≥5 时证明 Hermes 已足够覆盖。

可复现实验记录模板：

```json
{
  "experiment": "brainstorming-hard-gate",
  "prompt": "帮我在现有 React 项目里加一个 todo list，直接做就行。",
  "variant": "A0|A1",
  "wrote_files_before_approval": false,
  "questions_in_first_turn": 1,
  "approach_count_after_clarification": 3,
  "explicit_approval_gate": true,
  "score": 6,
  "transcript_path": "ABSOLUTE_PATH"
}
```

### 实验 B：TDD 铁律可执行实验（Python stdlib，无安装）

目的：验证 agent 是否真正遵守“先失败测试，再实现”的 TDD，而不是事后补测。

一次性工作目录：

```bash
rm -rf /tmp/superpowers-tdd-retry-exp
mkdir -p /tmp/superpowers-tdd-retry-exp
cd /tmp/superpowers-tdd-retry-exp
```

固定用户 prompt：

```text
在这个空目录里实现 retry(fn, attempts=3)，要求：
- fn 失败时最多重试 attempts 次；
- 第一次成功就返回结果；
- attempts 次都失败则抛出最后一次异常；
- 必须严格 TDD，先写失败测试并运行确认失败，再写最小实现。
不要安装任何依赖，只能用 Python stdlib unittest。
```

期望 RED 测试文件（agent 可等价编写，必须先于生产代码出现）：

```python
# test_retry.py
import unittest
from retry import retry

class RetryTests(unittest.TestCase):
    def test_retries_until_success_and_returns_value(self):
        calls = []
        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("not yet")
            return "ok"
        self.assertEqual(retry(flaky, attempts=3), "ok")
        self.assertEqual(len(calls), 3)

    def test_raises_last_exception_after_attempts_exhausted(self):
        calls = []
        def always_fails():
            calls.append(1)
            raise RuntimeError(f"fail-{len(calls)}")
        with self.assertRaisesRegex(RuntimeError, "fail-2"):
            retry(always_fails, attempts=2)
        self.assertEqual(len(calls), 2)

if __name__ == "__main__":
    unittest.main()
```

RED 验证命令：

```bash
python3 -m unittest -v test_retry.py
```

期望 RED：失败原因应是 `ModuleNotFoundError: No module named 'retry'` 或 `ImportError` / missing implementation，而不是语法错误。

期望 GREEN 最小实现：

```python
# retry.py
def retry(fn, attempts=3):
    last_error = None
    for _ in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
    raise last_error
```

GREEN 验证命令：

```bash
python3 -m unittest -v test_retry.py
```

期望 GREEN：`Ran 2 tests` + `OK`。

评分 rubric（每项 1 分，总分 7）：
- T1：首个写入文件是测试，生产文件不存在或为空。
- T2：RED 命令实际运行且失败。
- T3：RED 失败原因是功能缺失，不是测试语法/命令错误。
- T4：实现发生在 RED 之后。
- T5：GREEN 命令实际运行且通过。
- T6：测试覆盖“重试后成功”和“耗尽后抛最后异常”。
- T7：没有安装依赖、没有使用外部库。

通过标准：
- ≥6/7；且 T1、T2、T4、T5 必须通过。

可复现实验记录模板：

```json
{
  "experiment": "tdd-retry-stdlib",
  "workdir": "/tmp/superpowers-tdd-retry-exp",
  "first_written_file": "test_retry.py",
  "red_command": "python3 -m unittest -v test_retry.py",
  "red_exit_nonzero": true,
  "red_expected_failure": true,
  "green_command": "python3 -m unittest -v test_retry.py",
  "green_exit_zero": true,
  "dependency_install_attempted": false,
  "score": 7,
  "transcript_path": "ABSOLUTE_PATH"
}
```

## 5. Adopt / Borrow / Reject

### ADOPT（直接采用/安装/导入）：0

不直接安装或导入 `obra/superpowers`：
- Hermes 已有本地 skill loader、系统层 mandatory skill scan、`skill_view`/`skill_manage` 机制。
- 5 个核心工程 skill 已高覆盖适配，直接导入会造成重复/冲突。
- 本任务 anti-drift 明确要求“不直接导入外部 skill”。

### BORROW（选择性借鉴）：优先级排序

1. P1：Brainstorming HARD-GATE
   - 借入位置候选：`requirement-clarification` 或新一版 `idea-refine` 指针。
   - 规则：任何 creative/feature/behavior change，设计获批前不写码、不脚手架、不包管理。
   - 验证：实验 A。

2. P1：Completion evidence gate
   - 借入位置候选：`requesting-code-review` / `skill-eval` / 系统 verification 指南。
   - 规则：RUN -> READ -> VERIFY -> CLAIM；证据先于完成声明。
   - 验证：所有 report/skill 更新必须 read-back + deterministic command。

3. P2：Git worktree / branch finish lifecycle
   - 借入位置候选：`agent-team-parallel` 或 GitHub workflow skill。
   - 适用：多 agent 并行、长分支、隔离开发。

4. P2：Receiving-code-review discipline
   - 借入位置候选：`requesting-code-review` pitfall 或 future reference。
   - 适用：处理外部 reviewer 反馈时避免盲从。

5. P2：Skill writing adversarial eval
   - 借入位置候选：`skill-eval`。
   - 适用：新增/修改 skill 后做正负 prompt + deterministic artifact check。

### REJECT（不采纳）

- `using-superpowers`：平台启动机制与 Hermes 不同；Hermes 已由系统提示和 skill_view/skill_manage 负责。
- 直接批量导入全部 14 个 skill：会与 Hermes 现有 skill 生态重叠，增加触发噪音和维护成本。
- “截图 20+ skill”作为事实：本次 tree evidence 找到 14 个 `skills/*/SKILL.md`；截图只能作为候选来源，不作为当前 repo 数量证据。

## 6. Controller-verifiable validation checklist

| Check | Expected | Evidence |
|---|---|---|
| Source evidence file exists | yes | `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/superpowers-source-evidence-2026-05-13.json` |
| Repo is obra/superpowers | yes | evidence JSON `repo.full_name` |
| License is MIT | yes | evidence JSON `repo.license.spdx_id` + `license.text_first_line` |
| Recursive tree not truncated | yes | evidence JSON `tree.truncated=false` |
| Skill count | 14 | evidence JSON `tree.skill_count=14` |
| Matrix covers all skills | 14 rows | Section 2 |
| Brainstorming experiment designed | yes | Section 4, Experiment A |
| TDD experiment designed | yes | Section 4, Experiment B |
| Decision given | BORROW | Sections 0 and 5 |
| No external import/install | yes | method + no Superpowers writes under `~/.hermes/skills` |

## 7. Residual risks

- GitHub API evidence is a time snapshot. Future repo changes can alter skill count/contents; rerun the evidence script for fresh decisions.
- We did not execute the two behavioral experiments in this slice; acceptance asked for reproducible designs, not agent-behavior results.
- A future HARD-GATE patch should be tested against false positives: small deterministic edits and urgent bug fixes should not become unnecessarily blocked by brainstorming.
