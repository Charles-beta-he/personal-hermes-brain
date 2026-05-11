---
name: feeds
description: Monitor, validate, and summarize RSS/Atom/JSON feeds and blog update sources.
license: MIT
metadata:
  hermes:
    tags: [feeds, rss, atom, monitoring, blogwatcher]
    related_skills: [research, blogwatcher, cronjob]
---

# Feeds

Use this skill when the task involves RSS, Atom, JSON feeds, blog monitoring, newsletter-like web sources, update detection, feed validation, or scheduled feed summaries.

## Inputs / 输入

Collect the minimum feed task contract before acting:

- Feed source: URL, OPML file, blog homepage, existing feed list, or a named source already configured locally.
- Desired action: discover feed, validate feed, fetch latest items, summarize changes, create/update monitor, or debug a failing monitor.
- Time window: latest N items, since last run, last 24h/7d, or full backfill.
- Output target: direct reply, markdown report, local file, cron delivery, or downstream notes.
- Filters: keywords, authors, categories, language, domain allow/deny list, duplicate policy.
- Freshness requirements: one-shot check vs recurring watch cadence.

If a homepage is supplied instead of a feed URL, first discover feed links from `<link rel="alternate" type="application/rss+xml|application/atom+xml">`, common paths (`/feed`, `/rss`, `/atom.xml`, `/feed.xml`), and site metadata before declaring no feed exists.

## Outputs / 输出

Return a compact, auditable result:

- Feed identity: title, canonical URL, detected format, final resolved URL.
- Fetch status: HTTP status, redirect target, content type, item count, newest item timestamp.
- Change summary: new/changed items, duplicates skipped, filters applied.
- Health verdict: `ok`, `degraded`, `invalid_feed`, `unreachable`, `empty`, or `needs_auth`.
- Next action: no action, repair URL, reduce cadence, add parser exception, or create/update cron job.
- For monitoring jobs: state file path and schedule, plus a note that cron prompt must be script-first and bounded.

## Workflow

1. **Discover**
   - If given a page URL, discover candidate feed URLs.
   - Prefer explicit feed links over guessed paths.
   - Preserve redirects and canonicalize final URLs.

2. **Fetch safely**
   - Use bounded timeouts and a clear user agent.
   - Avoid retry storms; retry only transient network errors.
   - Record HTTP status, content type, and final URL.

3. **Parse and normalize**
   - Normalize RSS/Atom/JSON Feed into a common item schema: `id`, `title`, `url`, `published`, `updated`, `author`, `summary`, `content_hash`.
   - Deduplicate by stable GUID/id first, then canonical URL, then `(title, published)`.

4. **Compare state**
   - For monitors, compare against a local state file under `~/.hermes/state/feeds/` or the existing watcher state.
   - Do not overwrite state until the fetch and parse phase succeeds.
   - If state is missing, treat the run as bootstrap and avoid sending a noisy “all items are new” alert unless the user requested backfill.

5. **Summarize**
   - Summaries should separate facts from interpretation.
   - Include source links and timestamps.
   - For multi-source reports, group by source, then sort by time descending.

6. **Persist / schedule when requested**
   - Prefer deterministic scripts for recurring feed checks.
   - Cron prompts should only summarize injected JSON/text output in 2–3 lines.
   - Do not create recursive cron jobs from a cron run.

## Boundary Conditions / 边界条件

- **Invalid XML/HTML returned:** report `invalid_feed`, include content type and first parse error; try homepage discovery once if safe.
- **HTTP 403/401/auth wall:** report `needs_auth`; do not scrape private/authenticated feeds without credentials.
- **HTTP 429/rate limit:** report `degraded`; reduce cadence or back off, never increase retry pressure.
- **No timestamps:** use fetch time for ordering only as a fallback and label it as inferred.
- **Duplicate GUIDs with changed content:** compare content hash; report as `changed` rather than `new`.
- **Timezone ambiguity:** keep original timestamp and normalized UTC where possible.
- **Large feeds:** cap parsed items by requested window; do not dump full feed content into context.
- **Binary/non-text response:** stop and report content type; do not attempt to parse as feed.
- **Redirect loops:** stop after a small fixed limit and report `unreachable`.
- **Cron monitoring:** never put arguments in Hermes cron `script`; create a no-argument wrapper if arguments are needed.

## Checkpoints / 检查点

- [ ] Source URL or feed list is explicit and normalized.
- [ ] Fetch used bounded timeout and captured final URL/status/content type.
- [ ] Feed format and item count are reported.
- [ ] Dedupe key is documented.
- [ ] State update is atomic and only after successful parse.
- [ ] Output includes source links and timestamps.
- [ ] Recurring monitor is script-first, bounded, and emits non-empty JSON/text.
- [ ] Failures are classified (`invalid_feed`, `unreachable`, `needs_auth`, `degraded`) instead of silently ignored.

## Examples / 示例

### Example 1: Validate a feed URL

User: “检查 https://example.com/feed.xml 是否可用”

Expected behavior:

```text
Fetch with timeout → parse RSS/Atom/JSON → report status, final URL, item count, newest timestamp, and health verdict.
```

### Example 2: Discover a blog feed

User: “帮我监控这个博客的新文章：https://example.com/blog”

Expected behavior:

```text
Discover alternate feed links → validate the best candidate → propose or create a bounded script-first monitor if the user requested scheduling.
```

### Example 3: Summarize latest feed changes

User: “总结这 5 个 RSS 最近 24 小时的新内容”

Expected behavior:

```text
Fetch each source with bounded timeout → normalize items → filter by 24h → dedupe → grouped markdown summary with links and timestamps.
```

### Example 4: Debug a noisy feed monitor

User: “这个 feed 每次都把旧文章当新文章”

Expected behavior:

```text
Inspect state and item identifiers → compare GUID/URL/title+published/content hash → identify unstable ids or missing state update → recommend a stable dedupe key.
```

## Minimal Python Pattern

```python
from urllib.request import Request, urlopen

req = Request(url, headers={"User-Agent": "HermesFeedMonitor/1.0"})
with urlopen(req, timeout=20) as resp:
    status = resp.status
    content_type = resp.headers.get("content-type", "")
    body = resp.read(2_000_000)
```

Keep network and parsing code bounded. For recurring jobs, write JSON with `status`, `source`, `items_seen`, `new_items`, `error`, and `state_path` so the cron agent only summarizes deterministic output.

## Related Skills

- `research`: turn feed items into research digests.
- `blogwatcher`: monitor blogs/RSS sources over time.
- `cronjob`: schedule bounded recurring feed checks.
