# Memory-cap selfcheck and compaction

Use when Hermes memory/user profile is near the storage cap and a new durable fact fails to save.

## Trigger
- memory tool refuses an add because the store would exceed its size limit
- user explicitly asks to "开启自检" / run selfcheck on memory pressure
- current session produced several new durable facts but memory is close to full

## Goal
Free space without losing the highest-value durable facts.

## Procedure
1. Read both stores:
   - `~/.hermes/memories/MEMORY.md`
   - `~/.hermes/memories/USER.md`
2. Prefer `replace` over `add` for long entries that can be compressed into shorter declarative facts.
3. Compress environment/process notes to the minimum durable payload:
   - keep stable identifiers, key scripts, and core outcomes
   - drop long enumerations, one-off transcripts, temporary state, and session narratives
4. Preserve user-preference entries unless they are redundant; compress wording instead of deleting preference signal.
5. Retry the intended memory save only after verifying enough headroom exists.
6. If the session introduced a workflow correction (not just a user fact), patch the governing class-level skill as part of the selfcheck pass so the lesson lives in procedure, not only in memory.

## Good compression targets seen in session
- long implementation-history notes → one-line durable fact with key modules only
- verbose tool-fix notes → one-line durable governance fact
- project-specific browser-harness detail → short preference plus core viewport facts

## Pitfall
Do not save the failed attempted note itself verbatim as a long summary; the fix is usually to shorten old entries first, not to force one more long entry into an already full store.
