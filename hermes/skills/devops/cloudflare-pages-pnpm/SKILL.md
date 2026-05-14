---
name: cloudflare-pages-pnpm
description: Use when you need to deploy pnpm monorepo to Cloudflare Pages via GitHub Actions.
version: 1.0.0
author: Hermes Agent
license: MIT
triggers:
- cloudflare pages
- wrangler deploy
- pages deploy
- pnpm deploy
metadata:
  hermes:
    tags:
    - devops
    - cloudflare
    - pages
    - pnpm
    - github
    related_skills:
    - github
---

# Cloudflare Pages + pnpm Monorepo 部署

## Overview

Deploy pnpm monorepo to Cloudflare Pages via GitHub Actions. In practice, load it when you need to deploy pnpm monorepo to Cloudflare Pages via GitHub Actions. It defines the expected execution lane, scope boundaries, and verification shape for this class of work.
## When to Use

- You need to deploy pnpm monorepo to Cloudflare Pages via GitHub Actions
- cloudflare pages
- wrangler deploy
- pages deploy
- pnpm deploy
- Don't use for: requests that do not need you need to deploy pnpm monorepo to Cloudflare Pages via GitHub Actions; choose a more specific child skill or a broader routing skill that actually matches the task.
## 常见坑：wrangler-action + pnpm workspace

`cloudflare/wrangler-action@v3` 在 pnpm workspace 中会失败：

```
ERR_PNPM_ADDING_TO_ROOT: Running this command will add the dependency to workspace root
ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL: Command "wrangler" not found
```

### 解决方案：直接用 npx wrangler

不要使用 wrangler-action，直接在 devDependencies 中添加 wrangler，用 npx 执行：

#### 1. 安装 wrangler 到根目录

```bash
pnpm add -Dw wrangler@3.90.0
```

#### 2. 修改 deploy.yml

```yaml
name: Deploy to Cloudflare Pages

on:
  push:
    branches:
      - main
      - master

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      deployments: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 9

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build
        run: pnpm -F @tg/web build

      - name: Deploy to Cloudflare Pages
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
        run: |
          # Cloudflare Pages API rejects non-ASCII commit messages (e.g. Chinese chars).
          # Override with a safe ASCII message to prevent UTF-8 errors.
          COMMIT_MSG=$(git log -1 --pretty=format:'%s' | LC_ALL=C tr -cd '[:print:]' | sed 's/  */ /g' | head -c 200)
          npx wrangler pages deploy apps/web/dist \
            --project-name=trusted-games-platform \
            --branch=${{ github.ref_name }} \
            --commit-message="${COMMIT_MSG:-chore: deploy}"
```

## 常见坑：中文 commit message 导致部署失败

**症状**：
```
Invalid commit message, it must be a valid UTF-8 string. [code: 8000111]
```

**原因**：wrangler 默认读取 git commit message 传给 Cloudflare Pages API，API 不接受非 ASCII 字符。中文 commit message（如 `fix: 修复五子棋`）直接导致部署失败。

**修复**：用 `--commit-message` 参数传入 ASCII 过滤后的消息：
- `LC_ALL=C tr -cd '[:print:]'` — 剥离所有非 ASCII 字符
- `sed 's/  */ /g'` — 压缩多个连续空格为一个
- `head -c 200` — 截断超长消息
- `${COMMIT_MSG:-chore: deploy}` — 兜底默认消息

**验证**：`--commit-message` 是 wrangler pages deploy 的原生参数，非 hack。

## 需要的 GitHub Secrets

- `CLOUDFLARE_API_TOKEN` - Cloudflare API Token (需要 Pages:Edit 权限)
- `CLOUDFLARE_ACCOUNT_ID` - Cloudflare Account ID

## 部署地址格式

- 生产: `https://{project-name}.pages.dev`
- 预览: `https://{hash}.{project-name}.pages.dev`

## semantic-release 集成

### 常见坑：Node.js 版本

`semantic-release@25` 需要 Node.js `^22.14.0 || >= 24.10.0`，不能用 Node 20。

### 1. 安装依赖

```bash
pnpm add -Dw semantic-release @semantic-release/changelog @semantic-release/git @semantic-release/github conventional-changelog-conventionalcommits
```

### 2. .releaserc.json

```json
{
  "branches": ["main"],
  "plugins": [
    ["@semantic-release/commit-analyzer", {
      "preset": "conventionalcommits",
      "releaseRules": [
        { "type": "feat", "release": "minor" },
        { "type": "fix", "release": "patch" },
        { "type": "perf", "release": "patch" },
        { "type": "docs", "release": false },
        { "type": "chore", "release": false }
      ]
    }],
    ["@semantic-release/release-notes-generator", {
      "preset": "conventionalcommits"
    }],
    ["@semantic-release/changelog", {
      "changelogFile": "CHANGELOG.md"
    }],
    ["@semantic-release/npm", {
      "npmPublish": false
    }],
    ["@semantic-release/git", {
      "assets": ["CHANGELOG.md", "package.json"],
      "message": "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}"
    }],
    ["@semantic-release/github"]
  ]
}
```

### 3. release.yml workflow

```yaml
name: Release

on:
  push:
    branches:
      - main

permissions:
  contents: write
  issues: write
  pull-requests: write

jobs:
  release:
    runs-on: ubuntu-latest
    if: "!contains(github.event.head_commit.message, 'chore(release)')"

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Setup pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 9

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 22  # 必须 22+，semantic-release v25 要求
          cache: pnpm

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Run tests
        run: pnpm test

      - name: Build
        run: pnpm -F @tg/web build

      - name: Release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: npx semantic-release
```

### Commit 规范

| 类型 | 版本变化 | 示例 |
|------|---------|------|
| `feat:` | minor | `feat: 添加新功能` |
| `fix:` | patch | `fix: 修复 bug` |
| `perf:` | patch | `perf: 优化性能` |
| `docs:` | 不变 | `docs: 更新文档` |
| `chore:` | 不变 | `chore: 更新依赖` |

### 避免循环触发

semantic-release 会创建 `chore(release): x.y.z [skip ci]` commit，用 `if: "!contains(...)"` 跳过。

## Verification Checklist

```bash
# 查看部署状态
gh run list --workflow=deploy.yml --limit 3

# 查看部署日志
gh run view <run-id> --log | grep "pages.dev"

# 查看 release 状态
gh run list --workflow=release.yml --limit 3

# 查看发布版本
gh release list
```
- [ ] Preconditions, scope, and tool availability were checked before following this workflow.
- [ ] The key output artifacts, commands, or side-effects were verified by read-back or direct inspection.
- [ ] The final result still matches the trigger and acceptance shape of this skill.
## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

