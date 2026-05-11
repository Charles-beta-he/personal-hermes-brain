---
name: deprecation-and-migration
description: Standardized process for deprecating old APIs, scripts, configs, or patterns and migrating consumers to the replacement.
triggers:
  - "deprecate X", "remove old Y", "migrate from A to B"
  - when old code exists alongside new equivalent
  - when a feature flag has been on 100% for >30 days
model: default for migration execution, strong for breaking-change impact analysis
---

# deprecation-and-migration

Don't just delete. Announce → wait → migrate → verify → remove.

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

## Verification
- [ ] @deprecated tag + warning log added
- [ ] All consumers listed (code-intel blast-radius)
- [ ] Migration path documented
- [ ] Zero usage confirmed (staging logs, 7 days)
- [ ] Changelog entry for removal
