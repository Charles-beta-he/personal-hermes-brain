---
name: semantic-release-monorepo
description: Use when you need guidance on configure semantic-release for pnpm monorepo with GitHub Actions.
version: 1.0.0
author: Hermes Agent
license: MIT
triggers:
- semantic-release
- 自动版本
- 版本管理
- changelog
- release workflow
metadata:
  hermes:
    tags:
    - devops
    - semantic
    - release
    - monorepo
    - github
    related_skills:
    - github
---

# semantic-release + pnpm Monorepo 配置

## Overview

自动化版本管理：feat→minor, fix→patch, docs/chore→无变更。. In practice, load it when you need guidance on configure semantic-release for pnpm monorepo with GitHub Actions. It defines the expected execution lane, scope boundaries, and verification shape for this class of work.
## When to Use

- You need guidance on configure semantic-release for pnpm monorepo with GitHub Actions
- semantic-release
- 自动版本
- 版本管理
- changelog
- release workflow
- Don't use for: requests that do not need you need guidance on configure semantic-release for pnpm monorepo with GitHub Actions; choose a more specific child skill or a broader routing skill that actually matches the task.
## 关键坑点

### 1. Node.js 版本要求
semantic-release v25 需要 **Node.js ^22.14.0 || >= 24.10.0**

```yaml
# ❌ 失败
- uses: actions/setup-node@v4
  with:
    node-version: 20

# ✅ 正确
- uses: actions/setup-node@v4
  with:
    node-version: 22
```

错误信息：`node version ^22.14.0 || >= 24.10.0 is required. Found v20.x`

### 2. pnpm Workspace 安装
必须使用 `-w` 标志安装到根目录：

```bash
pnpm add -Dw semantic-release @semantic-release/changelog @semantic-release/git @semantic-release/github conventional-changelog-conventionalcommits
```

### 3. 避免 release commit 循环
在 workflow 中添加条件判断：

```yaml
jobs:
  release:
    if: "!contains(github.event.head_commit.message, 'chore(release)')"
```

## 完整配置

### .releaserc.json

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
        { "type": "revert", "release": "patch" },
        { "type": "docs", "release": false },
        { "type": "chore", "release": false },
        { "type": "ci", "release": false },
        { "type": "test", "release": false }
      ]
    }],
    ["@semantic-release/release-notes-generator", {
      "preset": "conventionalcommits",
      "presetConfig": {
        "types": [
          { "type": "feat", "section": "✨ Features" },
          { "type": "fix", "section": "🐛 Bug Fixes" },
          { "type": "perf", "section": "⚡ Performance" },
          { "type": "refactor", "section": "♻️ Refactoring" }
        ]
      }
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

### .github/workflows/release.yml

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
          node-version: 22  # 必须 22+
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

## Commit 规范 (Conventional Commits)

| 类型 | 版本变化 | 示例 |
|------|---------|------|
| `feat:` | minor (1.0.0 → 1.1.0) | `feat: 添加落子动画` |
| `fix:` | patch (1.0.0 → 1.0.1) | `fix: 修复动画冲突` |
| `perf:` | patch | `perf: 优化渲染性能` |
| `docs:` | 不变 | `docs: 更新 README` |
| `chore:` | 不变 | `chore: 更新依赖` |
| `ci:` | 不变 | `ci: 添加 workflow` |

## 首次发布

首次运行会将所有历史 commit 生成 v1.0.0 release。后续按 commit 类型自动递增。

## Cloudflare Pages 部署

### ⚠️ pnpm Workspace + wrangler-action 坑

使用 `cloudflare/wrangler-action@v3` 时，它会尝试 `pnpm add wrangler` 但缺少 `-w` 标志导致失败。

**错误信息**：
```
ERR_PNPM_ADDING_TO_ROOT  Running this command will add the dependency to the workspace root
```

**解决方案**：直接用 `npx wrangler pages deploy`

```yaml
- name: Deploy to Cloudflare Pages
  env:
    CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
  run: npx wrangler pages deploy apps/web/dist --project-name=YOUR_PROJECT --branch=${{ github.ref_name }}
```

需要将 `wrangler` 添加到 devDependencies：
```bash
pnpm add -Dw wrangler@3.90.0
```

## Verification Checklist

```bash
# 本地测试（dry-run）
npx semantic-release --dry-run

# 查看 GitHub Actions
gh run list --workflow=release.yml --limit 3

# 查看 Release
gh release view v1.0.0
```
- [ ] Preconditions, scope, and tool availability were checked before following this workflow.
- [ ] The key output artifacts, commands, or side-effects were verified by read-back or direct inspection.
- [ ] The final result still matches the trigger and acceptance shape of this skill.
## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

