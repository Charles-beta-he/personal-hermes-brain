# UVISA Lark task interruption handoff pattern

Use when a UVISA/Lark task loop is interrupted by context compression, tool-call ceilings, or max-iteration limits before closeout.

## Required behavior

1. Do not claim the task is complete unless all closeout gates finished: deterministic verification, scoped commit, push when required, remote FE package/deploy monitor, and requested TG notification.
2. Preserve the exact current repo state in the final/handoff text:
   - branch name and upstream if known
   - modified/untracked files
   - last visible commits
   - task id/title
   - tests already run and their result
   - unfinished gates
3. If a patch is mid-refactor, call out likely compile blockers explicitly rather than hiding them behind generic wording.
4. The next session should resume with fix-first sequencing, not broader exploration:
   - repair incomplete code references
   - rerun targeted test
   - run relevant wider test/build
   - write/update evidence note
   - commit/push/remote-monitor/TG
5. Treat a RED targeted test as useful evidence, but not as delivery. Mark it as `RED evidence only` until the implementation passes.

## Example from UVISA b9d0fcf8

Task: unified transaction-record page from Home “查看全部” and Me “交易记录”.

A mid-refactor interruption should preserve facts such as:
- `src/screens/home/TxListScreen.tsx` modified
- `src/screens/home/__tests__/TxListScreen.test.tsx` added
- targeted test initially failed because `/tx` defaulted to an incoming-only tab and lacked a visible filter button
- implementation started changing `/tx` to default `filterId="all"` and always show the filter button
- likely compile blockers remained: stale `CARD_SUBTYPES`, `setCardSub`, `cardSub`, or missing `getTxLabelKey`

The next session must not report completion or send TG until those blockers are fixed and closeout gates pass.
