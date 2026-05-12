# UVISA frontend i18n/copy-only Lark task closeout

Use this reference for small UVISA frontend copy or i18n tasks such as fiat currency labels, button text, or prototype wording when the change is low code-risk but still needs Lark loop closeout discipline.

## Pattern

1. Classify first:
   - Usually `point fix` when a single i18n key or one component label is wrong.
   - Still scan nearby paired concepts before editing (for example CNY vs CNH) so a copy fix does not collapse a required distinction.
2. Write a focused RED guard before changing the value:
   - Prefer a small Vitest assertion against the i18n JSON/module for pure copy changes.
   - The RED failure should prove the current string is the offending old value.
3. Apply the smallest i18n/component patch.
4. Run deterministic gates:
   - targeted Vitest for the new guard and any nearby existing guard,
   - full `pnpm test`,
   - `pnpm build`,
   - `git diff --check` before commit.
5. Build multi-model certification from explicit claim/evidence pairs, not a vague task prompt:
   - C-001: exact user-facing label/copy changed as required.
   - C-002: adjacent distinction/route/flow preserved.
   - C-003: targeted guard passed.
   - C-004: full test/build passed.
   - Evidence should include file paths, command outputs, and support links to the exact claim IDs.
6. Commit scoped files only, push the shared Lark task-loop branch, then monitor the frontend Railway service/package status.
7. TG closeout must include task id, commit hash, local gates, multi-model status, and remote frontend status.

## Railway wording caveat

If the Railway frontend service is healthy but tracks a deployment branch different from the pushed task-loop branch, phrase the evidence precisely:

- Correct: `task-loop branch pushed; current frontend service/package status is SUCCESS/healthy`.
- Incorrect: `this task-loop commit is deployed` unless the deployment metadata actually points to that commit/branch.

## Example: CNY fiat-wallet label

A small copy task changed `ccy.cny.name` from `人民币` to `CNY` while preserving `ccy.cnh.name = 离岸人民币`.

Useful guard shape:

```ts
import { describe, expect, it } from 'vitest';
import zh from '../zh.json';

describe('Chinese wallet currency labels', () => {
  it('uses CNY as the onshore RMB fiat-wallet account label while preserving CNH distinction', () => {
    expect(zh['ccy.cny.name']).toBe('CNY');
    expect(zh['ccy.cnh.name']).toBe('离岸人民币');
  });
});
```

Closeout evidence should state whether the remote frontend status is for the exact commit or only the currently configured deployment branch.
