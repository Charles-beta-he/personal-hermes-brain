# Cross-Patch 脚本内真实 producer/reviewer 落地报告 — 2026-04-27

## 结论

PASS。cross-patch.py 已从单一 orchestration framework 扩展为双模式：

- execute：保留原安全编排模式，不直接调用模型，actual_model_calls=false。
- run：新增脚本内真实执行模式，直接调用 producer/reviewer，actual_model_calls=true；默认 dry-run，只生成 diff；显式 --apply 才写文件；可配 --verify，验证失败自动回滚。

## 改动文件

1. /Users/charles/.hermes/scripts/cross-patch.py

新增能力：

- run_cross_patch_actual()
- call_model()
- model_provider()
- extract_json_object()
- apply_file_patches()
- build_actual_producer_prompt()
- build_actual_reviewer_prompt()
- CLI 子命令：cross-patch.py run

安全边界：

- 默认 dry-run，不写文件。
- --apply 才写文件。
- patch 必须 exact-string match。
- patch 文件路径必须在 workdir 内，阻止 path traversal。
- min_confidence 默认读取 config，也可 --min-confidence 覆盖。
- --verify 仅在 --apply 后执行；失败会恢复备份内容。

2. /Users/charles/.hermes/scripts/test_cross_patch_real_execution.py

新增回归测试：

- dry-run 会真实调用 producer/reviewer 的注入 caller，但不修改文件。
- --apply 路径会写入 reviewer 审核后的 patch。

3. /Users/charles/.hermes/skills/software-development/multi-model-architecture/SKILL.md

更新 cross-patch 双模式说明：

- execute = orchestration framework
- run = script_actual

## 新 CLI 用法

Dry-run，真实双模型调用但不写文件：

python3 /Users/charles/.hermes/scripts/cross-patch.py run \
  --task 'In demo.py replace old with new in the greeting string. Return exact-string patch only.' \
  --workdir /path/to/repo \
  --files demo.py \
  --producer gpt-5.5 \
  --reviewer mimo-v2.5-pro \
  --min-confidence 0.7

Apply，并在写入后验证，失败自动回滚：

python3 /Users/charles/.hermes/scripts/cross-patch.py run \
  --task 'Fix bug in src/a.ts' \
  --workdir /path/to/repo \
  --files src/a.ts \
  --producer gpt-5.5 \
  --reviewer mimo-v2.5-pro \
  --apply \
  --verify 'pnpm test && pnpm build'

保留原编排模式：

python3 /Users/charles/.hermes/scripts/cross-patch.py execute \
  --task '...' \
  --workdir /path/to/repo

## 验证结果

### TDD RED

新增测试后先运行，按预期失败：

- AttributeError: module 'cross_patch' has no attribute 'run_cross_patch_actual'

### GREEN

实现后测试通过：

- test_run_actual_apply_writes_file_after_review_approval ... ok
- test_run_actual_dry_run_calls_two_models_and_does_not_modify_file ... ok

### 真实双模型 smoke

执行真实 producer/reviewer dry-run：

- producer=gpt-5.5
- producer_provider=openai-codex
- reviewer=mimo-v2.5-pro
- reviewer_provider=xiaomi
- execution_mode=script_actual
- actual_model_calls=true
- applied=false
- verdict=pass
- stats:
  - total_patches=1
  - accepted=1
  - applied=1
  - conflicts=0
  - rejected_low_conf=0

说明：applied=1 在 stats 中表示 dry-run 计划可应用；顶层 applied=false 表示没有真实写文件。

### 兼容性 smoke

原 execute 编排模式仍正常：

- execution_mode=orchestration_framework
- actual_model_calls=false

### 系统验证

通过：

- py_compile:
  - cross-patch.py
  - test_cross_patch_real_execution.py
  - agent_protocol.py
- unittest:
  - 2/2 passed
- Hermes self-test:
  - 24/24 passed
- P10 health:
  - V=0.967
  - Grade=A
  - warnings=2

## 当前真实边界

已落地：

- 脚本内真实调用 producer/reviewer。
- provider-aware hermes chat 调用。
- reviewer 审核后的 patch 合并。
- dry-run diff。
- --apply 写文件。
- --verify 失败回滚。
- L2 agent_protocol 记录 cross_patch_actual。

未做/后续可优化：

- fuzzy patch matching。
- 多文件大上下文自动截断策略增强。
- reviewer 输出 approved_patch_ids 与 producer patch id 交叉校验。
- 路由器自动选择 reviewer，而不是 CLI 手填。
- 将 test_cross_patch_real_execution.py 纳入 self-test.py 主测试列表。
