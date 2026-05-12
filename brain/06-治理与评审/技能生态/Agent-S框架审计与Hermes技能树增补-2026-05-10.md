---
type: framework-audit
status: truth-grounded-advisory
created: 2026-05-10T15:19:24+08:00
source_repo: https://github.com/simular-ai/Agent-S
source_commit: 5caa76cb19c6a6b947a524f74995c45848c2efbc
license_observed: Apache-2.0
project: hermes-skill-tree
concepts: [Agent-S, GUI agent, computer-use, framework-audit, Hermes skills]
---

# Agent-S 框架审计与 Hermes 技能树增补（2026-05-10）

## 结论

- **决策**：选择性借鉴，不整体引入运行时。
- **评分**：68/100（B-/C+ 边界）。理念互补性高，但运行时安全面和本机 GUI/代码执行权限太大，默认不适合纳入 Hermes core executor。
- **认证状态**：truth-grounded advisory / **not fully certified**。已完成 repo evidence-first 审计、语法门禁与 Hermes skill-tree 小补丁；`consult_models.py --tier T3 --quorum 4 --discussion` 产出 `/Users/charles/.hermes/tick-20260510-072219/discussion_result.json`，truth gate 为 grounded（4/4 claims, coverage=1.0），但 MiMo discussion adapter 返回 `Not supported model xiaomi`，缺少 `best_within_constraints` signature，因此最终 `status=not_certified`，不得升级为完整四模型认证。

## 固定证据

- 仓库：`https://github.com/simular-ai/Agent-S`
- 固定 commit：`5caa76cb19c6a6b947a524f74995c45848c2efbc`
- 规模：约 126 个非 `.git` 文件，clone 后约 8.4M。
- License：仓库根 `LICENSE` 为 Apache License 2.0（`LICENSE:1-3`）。
- Python package：`gui-agents` v0.3.2；console entry point `agent_s=gui_agents.s3.cli_app:main`（`setup.py:3-5`, `setup.py:36-39`）。
- CI：仅观察到 black check（`black --check gui_agents`），未见常规 pytest gate（`.github/workflows/lint.yml:35-42`）。

## 核心架构摘录

- README 定位：Agent-S 是 autonomous GUI agent，通过 Agent-Computer Interface 操作电脑 GUI（`README.md:82-85`）。
- S3 入口：`AgentS3` 是薄 wrapper，把 `Worker` 和 grounding `ACI` 组合，`predict()` 调用 `Worker.generate_next_action()`（`gui_agents/s3/agents/agent_s.py:48-94`）。
- Worker 路线：
  - 构造 procedural memory prompt，并按平台/环境隐藏不可用 action（`worker.py:63-79`）。
  - 每步可调用 reflection agent 检查轨迹（`worker.py:125-178`）。
  - 主生成器把 task、reflection、text buffer、code-agent 结果和 screenshot 组合后输出 action plan（`worker.py:180-320`）。
  - 计划最后被解析成代码并经 grounding agent eval 成 pyautogui 代码（`worker.py:321-355`, `common_utils.py:15-32`）。
- Grounding/ACI：`OSWorldACI` 同时包含视觉 grounding model、OCR/text grounding、code agent 和多个 `@agent_action` GUI primitive（`grounding.py:178-245`, `grounding.py:390-599`）。
- bBoN/行为评估：S3 包含 BehaviorNarrator 对 action 前后截图做 fact caption，并用 ComparativeJudge 对多条轨迹做选择（`behavior_narrator.py:172-260`, `comparative_judge.py:62-149`）。
- OpenClaw integration 是外部 shell wrapper：拼 `agent_s` 命令、读取 grounding env、10 分钟 timeout（`integrations/openclaw/agent_s_wrapper.py:17-84`）。

## 高价值可借鉴能力（Hermes-native，不复制运行时）

1. **Computer-use capability doctor / preflight**
   - Agent-S 明确要求单显示器、安全提醒、grounding model、Tesseract、GUI permission（`README.md:100-138`）。
   - Hermes 可借鉴为 `macos-computer-use` / browser-harness 的 preflight：屏幕权限、OCR、模型/grounding endpoint、单屏/分辨率、危险权限确认。

2. **Reflection as trajectory drift guard**
   - Worker 的 reflection agent 专门检查轨迹是否循环或偏离（`worker.py:125-178`；prompt 在 procedural_memory 中体现）。
   - Hermes 可映射到现有 `multi-model-thinking` / `anti_drift_guard`：不直接复制 GUI agent，而提炼“每步以 screenshot/action/result 生成 reflection，并只反馈 drift，不给具体动作”的 reviewer 模式。

3. **Action formatter + grounding primitive contract**
   - `@agent_action` 暴露 typed primitives；生成器只能输出 action code，再转为 pyautogui 执行代码（`grounding.py:24-27`, `grounding.py:390-599`）。
   - Hermes 可借鉴为 GUI tool contract registry：action schema、平台适配、坐标 grounding、action rendering 分离。

4. **Behavior Best-of-N evidence pattern**
   - Agent-S S3 的 bBoN 不是简单投票；先把轨迹转成 fact captions，再用 initial/final screenshots + facts 做 comparative judge（`comparative_judge.py:73-149`）。
   - Hermes 可借鉴到 browser/TUI/GUI 任务的 multi-run evaluator：多条执行轨迹必须有截图/trace/fact caption，judge 仅选择证据最强轨迹，不替代 deterministic smoke。

5. **Local code environment must be explicit and bounded**
   - Agent-S local env 能运行 `/bin/bash -lc` 和 `python -c`，但 README 和代码都标注 warning/timeout（`README.md:164-180`, `local_env.py:6-20`, `code_agent.py:113-276`）。
   - Hermes 应保留当前 tool permission/contract gate，不引入 Agent-S 的默认 code-exec path；若借鉴，必须作为 default-off allowlist tool。

## 不采纳 / 风险边界

- **不整体安装为 Hermes executor**：Agent-S 可控制真实 GUI、pyautogui、剪贴板、shell、Python，权限面大（`README.md:101-103`, `README.md:179-180`, `local_env.py:13-20`, `local_env.py:48-63`）。
- **`eval()` 风险**：`create_pyautogui_code()` 对 LLM plan code 做 `eval(code)`，即使意图是 eval `agent.click(...)` 这类 primitive，也必须视为高风险运行时边界（`common_utils.py:15-32`）。
- **自动安装/系统修改风险**：`type()` action 在缺 `pyperclip` 时会运行 apt-get/pip install（`grounding.py:427-435`），不适合 Hermes default tool。
- **wrapper 会打印完整命令**：OpenClaw wrapper line 74-75 会打印 command；若 command 内含 `--ground_api_key`，存在日志暴露风险（`agent_s_wrapper.py:63-75`）。
- **测试门禁偏弱**：repo CI 只展示 black check，没有发现常规测试套件；本次只做了 `gui_agents/s3` + OpenClaw wrapper 的 `py_compile`。

## Hermes 技能树增补方案

- 已新增 framework-audit reference：`~/.hermes/skills/framework-audit/references/gui-computer-use-agent-audit.md`。
- 已更新 `framework-audit/SKILL.md`，新增 “GUI / Computer-Use Agent 深度扫描”分支，触发 Agent-S / GUI desktop agents / computer-use automation 时强制检查：权限边界、screen/OCR/grounding preflight、action schema、trajectory evidence、bBoN judge、安全日志与 license。
- 建议后续 P1：给 `apple/macos-computer-use` 或 `browser-harness-integration` 增加 `computer-use capability doctor` 小脚本；本 slice 仅沉淀方法论，不落地执行器。

## 验证

- `python3 -m py_compile` over `gui_agents/s3/**/*.py` + `integrations/openclaw/*.py`: **PASS**，21/21 compiled。
- `skill-steward.py` graph gate: 已运行；Skill Graph 2.0 gate 显示 cycles=0, excessive_depth=0, typed_violations=0，但全局 baseline 仍有既存告警（同名 impeccable、供应链扫描等），本 slice 未处理。

## 下一步

1. 若要 close 本任务到 done：需要检查 multi-model artifact 是否有 `discussion_result.json` 且无 severity>=3 unresolved；否则保持 review/advisory。
2. P1 可执行补丁：在 `macos-computer-use` 或 `browser-harness-integration` 增加 GUI capability preflight checklist/script。
3. P2：为 GUI/browser multi-run closure 定义 fact-caption evidence schema，避免截图证据散落。
