---
title: Hermes GitHub 个人助理同步方案
created: 2026-05-11
status: advisory_plan
source: hermes-cli
scope: local-brain + skills + selected scripts/config templates
multimodel_artifact: /Users/charles/.hermes/tick-20260511-144237/merged_plan.json
multimodel_status: fanout_advisory_not_full_ratification
models_consulted:
  - claude-opus-4-7
  - gpt-5.5
  - deepseek-v4-pro
  - mimo-v2.5-pro
truth_status: grounded
---

# Hermes GitHub 个人助理同步方案

## 结论

推荐建立一个新的 GitHub 私有仓库，例如：

`personal-hermes-brain` 或 `hermes-dotbrain`

不要直接把整个 `~/.hermes` 推到 GitHub。

正确架构是：

1. GitHub 私有仓库只管理“可复刻的源数据”。
2. `~/Documents/brain` 仍是本地大脑 Markdown 的 canonical source of truth。
3. `~/.hermes/skills`、部分 `~/.hermes/scripts`、非敏感配置模板进入仓库。
4. `~/.hermes/.env`、`auth.json`、OAuth token、sessions、logs、cache、checkpoints、tick、SQLite index、runtime state 全部禁止入库。
5. 其他电脑 clone 后，通过 bootstrap 脚本导入 brain/skills/scripts，再手动或通过密码管理器恢复 API keys/OAuth，最后运行验证门禁。

## 本地事实依据

- Hermes config path: `/Users/charles/.hermes/config.yaml`
- Hermes env path: `/Users/charles/.hermes/.env`
- Canonical brain: `/Users/charles/Documents/brain`
- Brain index: `/Users/charles/.hermes/memory/index.sqlite`，是 derived cache，不应提交。
- 当前 brainctl status PASS，indexed_blocks=2910。
- 当前 `~/Documents/brain`、`~/.hermes/skills`、`~/.hermes/scripts` 都不是独立 git repo。
- 当前 `~/.hermes` 虽然是 git repo，但已被大量 runtime/cache/session/secret 相关文件污染，不适合作为同步仓库根。
- 发现的禁止同步高危项包括：
  - `~/.hermes/.env`
  - `~/.hermes/auth.json`
  - `~/.hermes/auth/google_oauth.json`
  - `~/.hermes/memory/evolution/witness.key`
  - `~/.hermes/state-snapshots/*/.env`
  - `~/.hermes/state-snapshots/*/auth.json`
  - `~/.hermes/sessions/`
  - `~/.hermes/logs/`
  - `~/.hermes/cache/`
  - `~/.hermes/checkpoints/`
  - `~/.hermes/tick-*`
  - `~/.hermes/memory/*.sqlite`
  - `~/.hermes/state/*.db`

## 多模型 fan-out 结果

本轮使用 `consult_models.py` T2/quorum=4 fan-out：

- Claude: 主张新建 `hermes-dotbrain`，采用三层同步面：brain、Hermes portable assets、machine bootstrap。
- GPT/Codex: 强调 manifest + allowlist + validate-safe-tree + bootstrap 文档。
- DeepSeek: 强调这是 greenfield planning，需要生成 `.gitignore`、sync、bootstrap、verify、config template。
- MiMo: 强调不要放在 `~/.hermes` 内，secondary 机器默认应是 consumer，避免冲突扩散。

状态说明：

- `truth_status=grounded`
- `fanout_certification.multi_model_certified=true`
- 但未运行 full discussion/ratification，所以此文档是 `fanout_advisory_not_full_ratification`，不是 4/4 最终认证。
- artifact: `/Users/charles/.hermes/tick-20260511-144237/merged_plan.json`

## 推荐仓库结构

```text
personal-hermes-brain/
  README.md
  SECURITY.md
  CONFLICT_POLICY.md
  manifest.yaml
  .gitignore
  .gitattributes

  brain/
    ... mirror of ~/Documents/brain, Markdown-first

  hermes/
    skills/
      ... mirror of ~/.hermes/skills allowlisted content
    scripts/
      ... selected ~/.hermes/scripts only
    config/
      config.example.yaml
      env.example
      toolsets.example.md
      providers.example.md

  bootstrap/
    sync_export.sh
    sync_import.sh
    bootstrap_machine.sh
    verify.sh
    validate_safe_tree.sh
    rollback.sh

  docs/
    BOOTSTRAP.md
    RESTORE_CREDENTIALS.md
    SYNC_POLICY.md
    MACHINE_ROLES.md
```

## manifest.yaml 设计

核心原则：allowlist 优先，denylist 兜底。

```yaml
version: 1
repo_name: personal-hermes-brain
canonical:
  brain: ~/Documents/brain
  hermes_home: ~/.hermes

include:
  brain:
    source: ~/Documents/brain
    dest: brain
    allow:
      - "**/*.md"
      - "**/.obsidian/**"
    deny:
      - "**/.trash/**"
      - "**/*.tmp"

  skills:
    source: ~/.hermes/skills
    dest: hermes/skills
    allow:
      - "**/SKILL.md"
      - "**/references/**"
      - "**/templates/**"
      - "**/scripts/**"
      - "**/assets/**"
    deny:
      - "**/.usage.json"
      - "**/.curator_state"
      - "**/__pycache__/**"
      - "**/*.pyc"

  scripts:
    source: ~/.hermes/scripts
    dest: hermes/scripts
    allow:
      - "*.py"
      - "*.sh"
      - "*.json"
      - "*.yaml"
    deny:
      - "**/__pycache__/**"
      - "**/*.pyc"
      - "**/*secret*"
      - "**/*token*"
      - "**/*oauth*"

  config_templates:
    source: ~/.hermes/config.yaml
    dest: hermes/config/config.example.yaml
    sanitize: true

exclude_always:
  - "**/.env"
  - "**/.env.*"
  - "**/auth.json"
  - "**/auth/**"
  - "**/*token*"
  - "**/*secret*"
  - "**/*credential*"
  - "**/*.key"
  - "**/witness.key"
  - "**/sessions/**"
  - "**/logs/**"
  - "**/cache/**"
  - "**/checkpoints/**"
  - "**/tick-*"
  - "**/state-snapshots/**"
  - "**/*.sqlite"
  - "**/*.db"
  - "**/*.db-wal"
  - "**/*.db-shm"
  - "**/*.pid"
  - "**/*.lock"
```

## .gitignore 最低规则

```gitignore
# secrets
.env
.env.*
**/.env
**/.env.*
**/auth.json
**/auth/**
**/*token*
**/*secret*
**/*credential*
**/*.key
**/witness.key

# Hermes runtime / derived
**/sessions/**
**/logs/**
**/cache/**
**/audio_cache/**
**/image_cache/**
**/checkpoints/**
**/tick-*/**
**/state-snapshots/**
**/rate_limits/**
**/sandboxes/**
**/tmp/**
**/*.sqlite
**/*.db
**/*.db-wal
**/*.db-shm
**/*.pid
**/*.lock

# Python/runtime noise
**/__pycache__/**
**/*.pyc
.DS_Store
```

## sync_export.sh 行为

从主电脑导出到 repo：

1. 读取 `manifest.yaml`。
2. rsync `~/Documents/brain` 到 `repo/brain`，默认 Markdown-first。
3. rsync `~/.hermes/skills` 到 `repo/hermes/skills`。
4. rsync allowlisted `~/.hermes/scripts` 到 `repo/hermes/scripts`。
5. 生成 sanitized `hermes/config/config.example.yaml`。
6. 生成 `hermes/config/env.example`，只保留变量名，不保留值。
7. 运行 `validate_safe_tree.sh`。
8. 运行 `git diff --check`。
9. 由用户决定 commit/push。

重要：不建议脚本默认自动 push。默认只 export + validate + 提示下一步。

## sync_import.sh 行为

从 repo 导入到新电脑：

1. 检查 Hermes 是否安装：`hermes doctor`。
2. 检查目标目录是否已有内容：
   - `~/Documents/brain`
   - `~/.hermes/skills`
   - `~/.hermes/scripts`
3. 如果已有内容，先创建 timestamped backup：
   - `~/Documents/brain.backup-YYYYMMDD-HHMMSS`
   - `~/.hermes/skills.backup-YYYYMMDD-HHMMSS`
   - `~/.hermes/scripts.backup-YYYYMMDD-HHMMSS`
4. 默认 copy，不默认 symlink。
5. 导入完成后运行：
   - `python3 ~/.hermes/scripts/brainctl.py --json sync`
   - `python3 ~/.hermes/scripts/brainctl.py --json reindex`
   - `python3 ~/.hermes/scripts/brainctl.py --json search "Hermes" --limit 5`
   - `hermes skills list`
   - `hermes doctor`

copy 优于 symlink 的原因：

- 不同机器路径、iCloud、权限、Obsidian 行为更可控。
- 允许每台机器有本地差异。
- 通过 export/import 控制同步点，避免运行时并发写同一个 Git 工作树。

## bootstrap_machine.sh 流程

新电脑流程：

```bash
# 1. 安装 Hermes
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 2. 登录 GitHub 并 clone 私有仓库
git clone git@github.com:<your-user>/personal-hermes-brain.git ~/Code/personal-hermes-brain
cd ~/Code/personal-hermes-brain

# 3. 导入 brain/skills/scripts
bash bootstrap/bootstrap_machine.sh

# 4. 恢复 credentials（不来自 Git）
cp hermes/config/env.example ~/.hermes/.env
hermes setup model
hermes login --provider openai-codex   # 如需 Codex
hermes model                           # 设置默认 provider/model

# 5. 验证
bash bootstrap/verify.sh
```

## verify.sh 最低门禁

```bash
set -euo pipefail

hermes config path
hermes config env-path
hermes doctor
hermes skills list | head
python3 ~/.hermes/scripts/brainctl.py --json status
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "Agent" --limit 5

# repo safety
bash bootstrap/validate_safe_tree.sh

git status --short
```

## validate_safe_tree.sh 最低门禁

必须 fail-closed：

- Git staged/working tree 内不得出现 `.env`、`auth.json`、`google_oauth.json`、`witness.key`。
- 不得出现 `sessions/`、`logs/`、`cache/`、`checkpoints/`、`tick-*`、`state-snapshots/`。
- 不得出现 SQLite/DB runtime 文件。
- 对文本文件扫描常见 secret pattern：
  - `sk-...`
  - `ghp_...`
  - `xoxb-...`
  - `AIza...`
  - `ANTHROPIC_API_KEY=` with non-placeholder value
  - `OPENAI_API_KEY=` with non-placeholder value
  - `DEEPSEEK_API_KEY=` with non-placeholder value
  - `XIAOMI_API_KEY=` with non-placeholder value

建议同时接入：

- `gitleaks protect --staged`
- GitHub secret scanning / push protection
- pre-commit hook
- GitHub Actions CI secret scan

## 多机器冲突策略

推荐角色：

- Primary machine: 主要写入方，可以 export + commit + push。
- Secondary machines: 默认 consumer，可以 pull + import。若要反向写入，必须先 pull/rebase，然后 export 到分支/PR 或显式切换为 writer。

冲突规则：

1. brain Markdown 冲突：不静默覆盖，保留 `.conflict-<timestamp>.md`。
2. skills/scripts 冲突：停止导入，输出 diff，人工确认。
3. config template 冲突：本机 `.env` 永远优先，不从 Git 覆盖。
4. runtime state 冲突：不处理，因为 runtime state 不入库。

## 为什么不直接 git track ~/.hermes

因为 `~/.hermes` 混合了四类东西：

1. source-of-truth：skills、scripts、notes、部分 config。
2. secrets：`.env`、auth/OAuth token、witness.key。
3. runtime：sessions、logs、pid、lock、gateway state、cron outputs。
4. derived cache：SQLite index、semantic index、model cache、tick artifacts。

Git 同步只能同步第 1 类，不能同步第 2-4 类。

## 推进顺序

P0：只建仓库和安全门禁，不改 Hermes runtime。

1. 创建私有仓库 `personal-hermes-brain`。
2. 添加 `.gitignore`、`manifest.yaml`、`validate_safe_tree.sh`。
3. 先只导出 `~/Documents/brain`。
4. 跑 secret scan。
5. commit + push。

P1：加入 skills/scripts。

1. 导出 `~/.hermes/skills`。
2. 导出 selected `~/.hermes/scripts`。
3. 加 config templates。
4. 第二台机器 dry-run import。

P2：bootstrap 自动化。

1. 完成 `bootstrap_machine.sh`。
2. 完成 `verify.sh`。
3. 在第二台机器真实验证。
4. 记录机器角色和恢复流程。

P3：可选自动同步。

1. Primary 上设置 cron：每日 export + validate + status report。
2. 不默认自动 push。
3. Secondary 上设置 pull/import 手动命令或只读 cron。

## 最小可执行命令草案

```bash
mkdir -p ~/Code/personal-hermes-brain
cd ~/Code/personal-hermes-brain
git init
mkdir -p brain hermes/skills hermes/scripts hermes/config bootstrap docs

# 写入 .gitignore / manifest / validate script 后：
bash bootstrap/validate_safe_tree.sh
python3 ~/.hermes/scripts/brainctl.py --json status
rsync -a --delete --include='*/' --include='*.md' --exclude='*' "$HOME/Documents/brain/" brain/
bash bootstrap/validate_safe_tree.sh
git diff --check
git add README.md SECURITY.md CONFLICT_POLICY.md manifest.yaml .gitignore brain bootstrap docs hermes
git commit -m "chore: initialize personal hermes brain sync"

# 手动创建 GitHub private repo 后：
git remote add origin git@github.com:<your-user>/personal-hermes-brain.git
git push -u origin main
```

## 当前不应做的事

- 不把 `~/.hermes` 整体作为 GitHub repo。
- 不提交 `.env` / `auth.json` / OAuth token。
- 不提交 sessions / logs / cache / checkpoints / tick artifacts。
- 不提交 `~/.hermes/memory/index.sqlite` 这类 derived cache。
- 不让 bootstrap 自动覆盖新机器已有 brain/skills/scripts。
- 不让 sync 脚本默认自动 push。

## 下一步建议

如果要进入落地，我建议下一轮直接执行 P0：

1. 在 `~/Code/personal-hermes-brain` 创建本地 repo。
2. 写入 `.gitignore`、`manifest.yaml`、`bootstrap/validate_safe_tree.sh`、`README.md`、`docs/BOOTSTRAP.md`。
3. 只导出 brain Markdown。
4. 跑安全扫描和 brainctl 验证。
5. 本地 commit。
6. 等你明确同意后再创建 GitHub private repo 和 push。
