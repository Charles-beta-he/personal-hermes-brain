---
name: chinese-platforms
description: "中文互联网平台路由 — B站/小红书/抖音/微博/V2EX/微信公众号/雪球/小宇宙/Reddit/LinkedIn。路由知识来自 Agent-Reach 选择性借鉴, 全部映射为 Hermes 原生工具。触发词: 小红书, xhs, 抖音, douyin, B站, bilibili, b站, 微博, weibo, V2EX, v2ex, 公众号, 微信文章, 雪球, 股票, xueqiu, 小宇宙, 播客, reddit, linkedin, 领英, 职场"
license: MIT
attribution: "路由知识借鉴自 Agent-Reach (https://github.com/Panniantong/Agent-Reach), MIT License"
---

# 中文互联网平台路由

> 路由知识选择性借鉴自 Agent-Reach。全部映射为 Hermes 原生工具，零新增依赖。

## 路由表

| 用户意图 | 平台 | Hermes 工具 | 认证 |
|---------|------|------------|------|
| 搜索/阅读笔记 | 小红书 | `terminal(xhs search/read ...)` | Cookie |
| 视频解析 | 抖音 | `mcporter call douyin.*` | 无需 |
| 视频/字幕/搜索 | B站 | `terminal(yt-dlp + bili)` | 海外Cookie |
| 热搜/阅读 | 微博 | `web_extract` / `curl r.jina.ai` | 无需 |
| 热门/节点 | V2EX | `curl v2ex.com/api/...` | 无需 |
| 公众号文章 | 微信 | `mcporter call exa.*` domain限定 | 无需 |
| 股票行情/社区 | 雪球 | `web_extract` / `browser_navigate`；完整社区能力需浏览器 Cookie | Cookie/浏览器 |
| 搜索/阅读 | Reddit | `terminal(rdt search/read ...)` | 搜索无需 |
| 搜索/职位 | LinkedIn | `curl r.jina.ai` fallback | 无需 |
| 播客转录 | 小宇宙 | ffmpeg + Groq Whisper | API key |

---

## 小红书

```bash
xhs search "query"          # 搜索
xhs read NOTE_ID_OR_URL    # 阅读 (必须先搜再读!)
xhs hot                     # 热门
```
> 需: `pipx install xiaohongshu-cli` + `xhs login`

## 抖音

```bash
mcporter call 'douyin.parse_douyin_video_info(share_link: "URL")'
```
> 需: `pipx install douyin-mcp-server`

## B站

```bash
yt-dlp --dump-json "BVxxx"           # 元数据
yt-dlp --write-sub --skip-download   # 字幕
bili search "query" -n 5             # 搜索
```
> 海外IP需Cookie。需: `pipx install bilibili-cli`

## 微博 / V2EX

```bash
curl -s "https://r.jina.ai/https://weibo.com/..."  # 微博
curl -s "https://www.v2ex.com/api/topics/hot.json"  # V2EX公开API
```

## 微信公众号 / Reddit / LinkedIn

```bash
# 微信 — Exa (Jina被CAPTCHA拦截)
mcporter call 'exa.web_search_exa(includeDomains: ["mp.weixin.qq.com"], ...)'

# Reddit — rdt-cli
rdt search "query" --limit 10
rdt read POST_ID

# LinkedIn — Jina fallback
curl -s "https://r.jina.ai/https://linkedin.com/in/username"
```

## Agent-Reach 借鉴边界（Hermes-native）

- 不整体安装或 vendor Agent-Reach；优先复用 Hermes 已有 `web` / `browser` / `terminal` / `mcporter` / platform skills。
- 借鉴其能力分层：零配置公开读取、可选 Cookie/API key 解锁、复杂平台手动配置。
- 借鉴其 doctor UX：先检查命令是否存在、凭据是否配置、渠道是否可用，再决定工具路线。
- 涉及 Cookie / token / proxy 时只报告是否存在与权限状态；输出中必须掩码，避免泄露原值。
- 不把原始 Cookie/API key/token 粘贴进 prompt、日志、shell history 或任务正文；优先放入权限受限配置文件并只引用“已配置/未配置”。
- 对高风控平台优先 dry-run/safe-mode 说明，不在无确认时自动安装或登录。

## 验证

```bash
which xhs yt-dlp bili rdt 2>/dev/null
python3 ~/.hermes/scripts/skill-steward.py --graph-check --json
```
