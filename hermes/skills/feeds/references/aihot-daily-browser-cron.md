# AIHOT daily browser+cron pattern

Use when the user wants a recurring Chinese AI daily brief from https://aihot.virxact.com/.

Observed pattern
- Site root may return 403 to raw curl, so do not treat plain HTTP fetch failure as source failure.
- Browser navigation to `https://aihot.virxact.com/daily` works and exposes the latest issue in page text.
- The page contains a `最新一期` section with the current daily date.

Recommended workflow
1. Load the `feeds` skill.
2. Use browser tools, not curl, to read `https://aihot.virxact.com/daily`.
3. Extract the latest issue date and the top items from `document.body.innerText` or DOM queries.
4. If the latest issue has not changed for today, report `今日 AIHOT 日报未更新` and summarize the most recent issue instead.
5. For automation, create a cronjob with `enabled_toolsets:["browser"]` and `deliver:"origin"` so the report is posted back to the current chat.

Suggested report shape
- 日期
- 今日重点（3-6 条）
- 值得关注的模型/产品/公司
- 对 Hermes 自身可迁移的启发
- 一句总评

Pitfalls
- Do not hit only the site root and assume the source is down because curl got 403.
- Do not summarize the homepage mixed feed when the user asked for a daily brief; prefer `/daily` latest issue.
