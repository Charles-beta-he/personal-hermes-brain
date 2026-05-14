---
name: gifs
description: Use when the user asks for GIFs, reaction GIFs, Tenor/Giphy-style search, short animated media, or GIF file handling.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - gifs
    - media
    - reaction-gifs
    - search
    - download
    related_skills:
    - gif-search
    - media
---

# Gifs

## Overview


GIF 工作流总入口：当用户要“找一个 GIF / 下载 GIF / 发 GIF / 做短动图 / 处理 GIF 文件”时，先用本 skill 判定路线，再按需加载更具体的 `gif-search` 或媒体处理 skill。

## When to Use

- The user asks for GIFs, reaction GIFs, Tenor/Giphy-style search, short animated media, or GIF file handling

## Input / 输入

- 用户意图：搜索、下载、推荐、发送、转换、压缩、裁剪或分析 GIF。
- 查询词或语义：例如 “celebration”, “cat typing”, “震惊表情包”。
- 交付目标：直接给 URL、下载本地文件、发送到聊天平台，或嵌入 Markdown。
- 可选约束：风格、语言/地区、安全等级、文件大小、透明背景、尺寸、时长、目标平台。

## Output / 输出

- GIF URL、Markdown 图片语法、或本地文件路径（必要时用 `MEDIA:<path>` 交付）。
- 简短说明：为什么选这个 GIF、来源/格式、尺寸或体积注意事项。
- 如果无法获取 GIF：说明失败原因，并给出替代查询或手动下载方案。

## Workflow / 工作流

1. **判定任务类型**
   - 搜索/下载现成 GIF → 使用 `gif-search`（Tenor API，需 `TENOR_API_KEY`）。
   - 从网页找 GIF → 使用浏览器或网络抓取，优先返回原始媒体 URL。
   - 转换/压缩/裁剪本地媒体 → 使用终端工具（如 `ffmpeg`/ImageMagick，先检查是否安装）。
   - 发送到聊天平台 → 产出本地文件路径或可访问 URL，不要只给不可下载的页面链接。

2. **选择格式**
   - 聊天/移动端优先 `tinygif` 或 MP4/WebM 变体，体积更小。
   - 文档/Markdown 可用标准 GIF URL：`![alt](url)`。
   - 如果平台不支持 GIF 预览，改用 MP4/WebM 并说明。

3. **执行与验证**
   - 搜索时给出 3–5 个候选，除非用户明确要“第一个”。
   - 下载后验证文件存在且非空；必要时检查 MIME/扩展名。
   - 发送前确认路径是本地可读文件或 URL 可访问。

4. **交付**
   - 用户要“发出去”时，输出可发送的 `MEDIA:<local_path>` 或调用相应消息工具（仅在用户明确要求发送时）。
   - 用户只要素材时，直接给 URL/文件路径和一句使用建议。

## Constraints / 边界条件与约束

- 不要伪造 GIF URL；必须来自工具结果、可访问网页或本地生成文件。
- 不要暴露 API key；命令示例用 `$TENOR_API_KEY` 或 `***`。
- NSFW、暴力或版权敏感内容要降低风险：使用安全过滤、给出中性替代词，或拒绝明显违规请求。
- 大文件优先压缩或改用 MP4/WebM；避免把超大 GIF 直接发到聊天平台。
- 如果缺少 `TENOR_API_KEY`，不要卡住：可改用公开网页搜索、请求用户提供 key，或说明无法调用 Tenor API。

## Checkpoints / 检查点

- [ ] 是否明确了用途：搜索、下载、转换、发送或嵌入？
- [ ] 是否选择了适合目标平台的格式与大小？
- [ ] URL 或本地文件是否真实可访问？
- [ ] 是否避免泄露 API key 和不必要的敏感内容？

## Examples / 示例

### 示例 1：搜索并返回候选

```text
User: 找几个 “nice work” 的鼓励 GIF
Agent: 使用 gif-search 查询 nice work，返回 3 个 tinygif 候选 URL，并推荐最适合聊天发送的一个。
```

### 示例 2：下载后发送

```text
User: 下载一个 celebration GIF 并发给 Telegram
Agent: 搜索 celebration → 下载 top result 到 /tmp/.../celebration.gif → 验证文件非空 → 用 MEDIA:/tmp/.../celebration.gif 交付/发送。
```

### 示例 3：处理本地 GIF

```text
User: 把 ./demo.gif 压到 5MB 以下
Agent: 检查文件大小与 ffmpeg/ImageMagick 可用性 → 通过缩放/降帧压缩 → 输出压缩后的本地路径与新大小。
```

## Related Skills / 关联 Skill

- `gif-search` — Tenor API 搜索与下载 GIF 的具体命令。
- `media` — 更通用的媒体处理、转码、YouTube/音频/视频工作流。
- `gifs` 只负责路由与通用边界；具体 API 命令以 `gif-search` 为准。

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

