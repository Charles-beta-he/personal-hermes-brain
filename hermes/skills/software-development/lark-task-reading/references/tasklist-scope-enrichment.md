# Lark Tasklist Scope Enrichment

Session lesson: Lark `/task/v2/tasks?completed=false` may return `tasklists` entries with only `tasklist_guid` and `section_guid`, not the human-readable tasklist name. In that shape, `LARK_TASK_SCOPE_MODE=only` for a list such as `UVISA-2.0新版开发` can return zero even though the target tasks are present.

## Correct pattern

1. Fetch incomplete tasks:
   - `GET /task/v2/tasks?page_size=100&completed=false`
   - paginate with `page_token` until `has_more=false`.
2. Fetch visible tasklists:
   - `GET /task/v2/tasklists?page_size=100`
   - paginate if needed.
3. Build `tasklist_guid -> tasklist metadata`.
4. Enrich each task's `tasklists[]` with `name`, `url`, and canonical `guid` from the tasklist map.
5. Run scope matching after enrichment, not before.
6. For hard filters (`scope_mode=only`), require the enriched `tasklist_names` / `tasklists[].name` to include the desired scope; do not rely on title text.

## Evidence-first validation

A correct UVISA hard-scope read should prove:

```text
count > 0
all task.lark_task_scope == "UVISA-2.0新版开发"
all "UVISA-2.0新版开发" in task.tasklist_names
```

This distinguishes true tasklist membership from weak title/description keyword matching.

## Implementation notes

- Preserve raw `tasklists` and derived `tasklist_names` in the payload.
- Preserve fallback semantics: `prefer` may fall back to all incomplete tasks when no scoped tasks are visible; `only` should remain a true hard filter after tasklist enrichment.
- If `/task/v2/tasklists` is unavailable, fail visibly or annotate warnings for scope certification; do not claim hard-scope correctness from titles alone.
- Task descriptions may be empty while comments contain the actionable details. `issue_body` should merge description + comments + linked docs, while still preserving `description`, `comments`, and `docs_content` separately.
