# Lark Task API v2 — Task Update and Batch Closeout

## Updating task description (PATCH)

The Lark Task API v2 uses `PATCH /task/v2/tasks/{guid}` with a **wrapped** `task` object:

```python
body = json.dumps({
    "task": {"description": "evidence text here"},
    "update_fields": ["description"]
}).encode("utf-8")

url = f"https://open.larksuite.com/open-apis/task/v2/tasks/{guid}"
req = urllib.request.Request(url, data=body, method="PATCH")
req.add_header("Authorization", f"Bearer {token}")
req.add_header("Content-Type", "application/json")
```

**Critical**: the `task` wrapper is required. Sending `{"description": "...", "update_fields": [...]}` without the wrapper returns `400: Invalid Param 'task', must not be empty`.

## Comments API — NOT AVAILABLE via v2

The comments endpoint `POST /task/v2/tasks/{task_id}/comments` returns **404 Not Found** on Larksuite (international). The endpoint may work on feishu.cn tenants but is unreliable for international apps.

**Workaround**: Use the `description` field for evidence. This is visible in the task detail page and persists across sessions.

## Batch closeout pattern

```python
#!/usr/bin/env python3
"""Batch update Lark task descriptions with evidence."""
import sys, json, urllib.request
sys.path.insert(0, "/Users/charles/.hermes/scripts")
from lark_task_reader import get_token, LarkClient

token = get_token()
client = LarkClient()

CLOSED_TASKS = {
    "guid-prefix-8": "✅ 已完成 | evidence summary | commit hash | test results",
    # ... more tasks
}

data = client.get("/task/v2/tasks", token, {"page_size": "50"})
items = data.get("data", {}).get("items", [])

for item in items:
    guid = item.get("guid", "")
    for guid_prefix, evidence in CLOSED_TASKS.items():
        if guid_prefix in guid:
            body = json.dumps({
                "task": {"description": evidence},
                "update_fields": ["description"]
            }).encode("utf-8")
            url = f"https://open.larksuite.com/open-apis/task/v2/tasks/{guid}"
            req = urllib.request.Request(url, data=body, method="PATCH")
            req.add_header("Authorization", f"Bearer {token}")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read())
                print(f"{'✅' if result.get('code')==0 else '❌'} {guid_prefix}")
            break
```

## Task fields available

Each task from `/task/v2/tasks` contains:
- `guid`: UUID — used for PATCH URL
- `task_id`: e.g. `t103374` — internal ID
- `summary`: task title
- `description`: task body (updatable via PATCH)
- `status`: `todo` | `done` etc.
- `completed_at`: timestamp or `"0"` if not completed
- `tasklists[]`: `{tasklist_guid, section_guid}`
- `members[]`: `{id, role, type}`
- `url`: deep link to task in Lark app

## Skipping already-updated tasks

Before batch-updating, check if `description` already contains evidence markers (`✅` or `🔶`). Skip those to avoid overwriting previous closeout evidence.
