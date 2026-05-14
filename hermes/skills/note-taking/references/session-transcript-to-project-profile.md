When updating a durable project profile from a Claude resume/session transcript, treat the transcript as evidence, not as truth by default.

Use this workflow:
1. Locate the session transcript file first (for Claude resume sessions this is often under ~/.claude/projects/.../<session-id>.jsonl).
2. Read the current canonical profile before extracting anything so you know the target schema and avoid duplicating old facts.
3. Extract only durable facts:
   - stable repo paths / canonical files
   - enduring architecture decisions
   - durable UX or workflow conventions repeated across files/tasks
   - verified integration boundaries and source-of-truth rules
4. Reject transient content:
   - one-off task narratives
   - temporary blockers
   - credentials / OTP / secrets
   - unresolved claims not cross-checked in code or docs
5. Cross-check transcript claims against code/config when possible before proposing profile edits.
6. Record the evidence path in profile_update_history or the equivalent audit field.

Useful extraction signals from transcripts:
- repeated edits across a cluster of related files -> durable subsystem/workflow pattern
- schema/migration + domain + controller + test changes together -> architecture-level fact worth profiling
- user restatements of acceptance criteria -> candidate convention, but phrase it as a reusable rule rather than a one-off task note

Good profile updates from this pattern:
- 'auth/otp/password screens preserve user-entered values during submit/loading; bind loading to the triggering button instead of clearing fields'
- 'frontend version display is sourced from package.json.version plus build metadata injected at build time'
- 'FX domain uses multi-source quote clients plus pair/source mapping and aggregation, with admin-side management and snapshot retention'

Bad profile updates from this pattern:
- 'Session X fixed page Y'
- 'Tool Z failed on line N'
- raw task descriptions copied from chat
