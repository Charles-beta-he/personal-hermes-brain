---
title: personal-hermes-brain Round 1 落地记录
created: 2026-05-11
status: landed_local_commit
repo: /Users/charles/Code/personal-hermes-brain
commit: see `git log --oneline -1` in repo
multimodel_tick: /Users/charles/.hermes/tick-20260511-153834
---

# personal-hermes-brain Round 1 落地记录

## 结论

Round 1 已落成本地 Git repo：`/Users/charles/Code/personal-hermes-brain`。

默认只做本地 commit。GitHub private remote 已创建并配置为 `origin`，但没有 push 内容。

## Memory 是否上传

不上传原始 Hermes persistent memory。

禁止入库：

- `~/.hermes/memories/MEMORY.md`
- `~/.hermes/memories/USER.md`
- `~/.hermes/memory/`
- index / sqlite / wal / witness key / session recall / runtime memory state

原因：这些内容包含长期个人画像、项目路径、偏好、内部策略与可能的敏感环境信息。GitHub private repo 不是 raw assistant memory 的合适安全边界。

允许入库：

- `brain/`：经过整理的 Markdown 知识与项目记录。
- `hermes/skills/`：可迁移技能。
- `hermes/scripts/`：选定确定性脚本。
- `hermes/memory/README.md`：只作为 raw memory 不同步的政策说明。

## 已落地内容

- repo skeleton
- manifest allowlist / denylist
- sanitized config templates
- `sync_export.sh`
- `sync_import.sh`
- `bootstrap_machine.sh`
- `verify.sh`
- `validate_safe_tree.sh`
- `install_push_guard.sh`
- `rollback.sh`
- memory local-only policy
- Round 1 proof 文档

## 验证

本地验证通过：

- `bash bootstrap/sync_export.sh` PASS
- `bash bootstrap/validate_safe_tree.sh` PASS
- `bash bootstrap/verify.sh` PASS
- `git diff --check` PASS
- `brainctl reindex` PASS，`indexed_blocks=2940`，`skipped_secret_blocks=54`
- repo 内 `hermes/memory` 仅有 `README.md`
- pre-push guard 已安装，本地 `.git/hooks/pre-push` 默认阻止 push，除非显式 `HERMES_ALLOW_PUSH=1`
- GitHub private repo 已创建：`https://github.com/Charles-beta-he/personal-hermes-brain`；仅配置 remote，未 push 内容

## 多模型检查

Round 1 first fan-out 指出：方向正确，但需要补足：

1. claim-to-evidence mapping
2. raw memory path denylist
3. no-push mechanical guard

已落地上述三项。

Round 1 re-check artifact：`/Users/charles/.hermes/tick-20260511-153834/merged_plan.json`

结果：

- planner success: 4/4
- fanout_certification.multi_model_certified: true
- truth_status: grounded
- evidence_coverage: 1.0
- verified_claim_count: 3/3
- concrete_patch_count: 0

注意：本轮未跑最终 full discussion ratification；这是 4 模型 fan-out grounded check，不声明 full discussion certification。

## 当前本地 commit

当前 commit 以 repo 内 `git log --oneline -1` 为准。
