---
name: deprecation-and-migration
description: Use when deprecating old APIs, scripts, configs, or patterns and migrating consumers to a replacement safely.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - deprecation
    - migration
    - breaking-change
    - rollout
    related_skills:
    - documentation-and-adrs
    - source-driven-development
    - incremental-implementation
---

# deprecation-and-migration

## Overview


Don't just delete. Announce → wait → migrate → verify → remove.

## When to Use

- Deprecating old APIs, scripts, configs, or patterns and migrating consumers to a replacement safely

## The 5-Phase Process

### Phase 1: Announce
- Add @deprecated tag/comment
- Log warning on usage (not error — yet)
- Document migration path: "use X instead of Y"
- Set removal target date (minimum 30 days)

### Phase 2: Notify
- List all consumers (use code-intel.py or grep)
- If internal consumers: open issues/PRs
- If external API: add deprecation header, update docs

### Phase 3: Migrate
- One consumer at a time
- Each migration: atomic commit, verify tests pass
- Track: `consumers_migrated / consumers_total`

### Phase 4: Verify Zero Usage
- Remove or make usage fatal (throw error)
- Deploy to staging
- Monitor logs for 7 days for any remaining callers

### Phase 5: Remove
- Delete deprecated code
- Clean up tests
- Update Changelog: `Removed: X (deprecated YYYY-MM-DD)`
- Archive old config/docs

## Migration Checklist
```
[ ] All consumers identified (code-intel call-chain)
[ ] Migration path documented for each consumer
[ ] Tests updated for new API
[ ] Deprecation warning in place ≥30 days
[ ] Zero usage confirmed (7 days staging monitoring)
[ ] Changelog updated
```

## Anti-patterns
- "Just delete it, nobody uses this" → verify first
- "Add a flag to switch" → doubles maintenance burden
- "Deprecate without migration path" → leaves users stranded
- Removing without announcement → production incident

## Verification Checklist
- [ ] @deprecated tag + warning log added
- [ ] All consumers listed (code-intel blast-radius)
- [ ] Migration path documented
- [ ] Zero usage confirmed (staging logs, 7 days)
- [ ] Changelog entry for removal

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

