# Mobile H5 Browser-Harness Loop Gates

Use this reference when a mobile web app has credential, payment, wallet, or security flows and the user expects real browser/browser-harness verification before declaring UI acceptance.

## Trigger

Apply these gates when testing flows such as:
- login / OTP / captcha / verification code
- PIN setup / payment password / keypad flows
- email/phone/password/security changes
- wallet/home/funds entry points
- bottom navigation or fixed CTA screens

## Required Device Classes and Viewports

For product acceptance, target mainstream mobile classes instead of chasing arbitrary rare viewport sizes:
- Apple/iOS Safari/WebKit: normal modern iPhone class plus short/SE or browser-chrome-reduced height
- Android Chrome/OEM WebView: normal Android class plus short in-app/browser-chrome-reduced height
- HarmonyOS/WebView: normal HarmonyOS class plus short WebView/browser-chrome-reduced height

Always include at least two mobile heights for each relevant class or a representative equivalent when device emulation is limited:
- Normal mobile: `390x844` / project standard modern phone height
- Short browser/mobile-H5: `390x577` / SE-class or browser-chrome-reduced height

Recommended frozen mainstream matrix for credential/payment/security loops:
- `ios-modern-390x844`
- `ios-short-390x667`
- `android-modern-412x915`
- `android-short-393x600`
- `harmony-modern-393x852`
- `harmony-short-393x580`

Use the template `templates/mobile-h5-issue-ledger.json` when promoting this from an ad-hoc run into a repeatable project gate.

Why: a flow can complete at 390x844 while the CTA, random keypad, delete key, or safe-area bottom is clipped at short H5 heights. This is common in H5, in-app browsers, iOS Safari chrome changes, split-screen, small Android devices, and HarmonyOS WebViews.

## Evidence to Capture

For every major step, capture:
- screenshot path
- current URL and visible body text prefix
- page errors and console warnings/errors
- relevant `/api/` response status and success flag, with tokens/passwords redacted
- `horizontalOverflow`
- `offscreenInteractive` count and examples
- `smallTouchTarget` count and examples

Console policy for committed gates:
- Browser `console.error` must become a HIGH/runtime finding and block acceptance.
- Browser `console.warning` should enter the issue ledger as INFO by default so it is visible but does not block unless it correlates with a failed assertion, pageerror, API failure, or user-visible defect.
- Summary/report output should include `consoleErrors` and `consoleWarnings`; raw console message count alone is not enough because benign browser noise can hide real runtime errors.

For OTP/PIN/keypad pages, explicitly verify:
- all digits are fully visible
- delete/backspace is fully visible
- primary CTA is fully visible after input and before input
- bottom safe-area padding exists
- user can recover from a wrong digit/code
- paste/autofill behavior is not blocked unless there is a documented security reason

## Scroll-Proof Classification Protocol

Before treating raw `offscreenInteractive` counts as blockers, classify each finding:

1. Capture initial screenshot and element bounding box.
2. If the element is not a fixed keypad/CTA, run `element.scrollIntoView({ block: 'center' })` or scroll the page/container to bottom.
3. Re-capture screenshot and bounding box.
4. Check whether fixed bottom navigation or safe-area overlays cover the element.
5. Assign exactly one classification:
   - `true_clip`: required control remains unavailable/obscured after scroll, or fixed keypad/CTA is clipped.
   - `bottom_nav_overlap`: element can be scrolled near view but is covered by fixed nav/safe-area.
   - `scrollable_below_fold`: element is reachable by normal scroll and not covered.
   - `safe_area_risk`: control is mostly visible but has insufficient bottom inset/gesture-area padding.
   - `harness_false_positive`: deterministic screenshot + layout evidence proves the raw detector is wrong.
   - `needs_scroll_proof`: cannot decide yet; this cannot pass final UI acceptance.

Home/wallet lists often start as `needs_scroll_proof`; PIN keypads/delete keys clipped at short heights are usually immediate `true_clip` because scrolling the page cannot expose fixed keypad rows safely.

## Severity Mapping

P0 / Blocker:
- HIGH `offscreenInteractive` on auth, OTP, PIN/payment credential, email/phone/security, or funds critical path
- CTA clipped below viewport on a required step
- random keypad bottom row, delete key, or any digit clipped/unreachable
- horizontal overflow that hides core controls

P1 / Major:
- funds/home wallet cards or security entry points not reachable in short viewport, unless proven scrollable and not obscured by bottom navigation
- credential/security screens have repeat touch-target issues below 44px
- flow reaches final state only via script shortcuts while real clickable controls are visually clipped

P2 / Quality:
- no HIGH issues, but medium a11y/touch-target/contrast/motion issues remain
- demo-code text visible in mock/test mode; production must hide it
- minor text contrast issues or non-critical icon hit areas

## Loop Decision Rules

CONTINUE loop when:
- any P0/P1 issue remains and local code can plausibly fix it
- browser-harness flow completes but UI evidence has HIGH offscreen issues on critical paths
- deterministic gates pass except UI layout/a11y gates

PAUSE loop only when:
- dev/mock cannot start due to missing local config
- browser-harness cannot run or evidence cannot be produced
- external account/production-only verification is required

ABORT loop only when:
- requirements conflict or the task is impossible without unavailable production access

STOP loop only when all are true:
- real browser walk reaches the expected end state on normal and short mobile viewports
- `pageerrors=0`
- `consoleErrors=0` (warnings may remain only as classified INFO or accepted lower-severity debt)
- relevant mock/backend APIs return expected success
- no HIGH offscreen interactive elements on auth/PIN/payment/email/funds critical paths
- no horizontal overflow
- core touch targets are >=44px or have >=44px invisible hit areas
- automated guard (`ui:regression`/Playwright) passes
- unit tests and build pass
- evidence is written back to the project UI ledger/Workpad
- dev/mock/background processes are stopped and ports are verified closed; if shell/lsof commands are misclassified as long-lived by the terminal wrapper, use a small Python/socket process check instead of skipping cleanup

## Anti-Ping-Pong / Anti-Coverage-Gaming Rules

To keep autonomous loops from repeatedly changing harness code, viewport choices, or thresholds just to preserve pass rate:
- Freeze a device-matrix contract for the loop before fixing UI; any matrix change requires a new ledger entry explaining why.
- Record every HIGH/P0/P1 finding in a stable issue ledger: `issue_id`, viewport/class, selector or element text, symptom hash, classification, owner, status, evidence path.
- Classify each offscreen finding before fixing: `true_clip` (control unavailable/obscured), `scrollable_below_fold` (acceptable if proven scrollable and not hidden by fixed nav), or `harness_false_positive` (requires evidence and reviewer sign-off).
- Ratchet rule: once a viewport bucket passes, do not relax thresholds or remove that bucket in later rounds; a new failure means fix UI or file accepted risk, not shrink coverage.
- Single-responsibility rule per loop round: change one of UI code, harness code, or test ledger — not all three — unless the reason is documented and separately verified.
- Temporary `/tmp` harness workarounds may use project-root module resolution; repo-committed harness scripts must stay portable and must not hardcode personal absolute paths.
- Multi-model output can propose priorities and challenge classifications, but cannot certify a threshold or coverage reduction without deterministic evidence.

## Common Fix Directions

Do not delete controls, hide entry points, or reduce business content to pass the gate. Prefer:
- `min-height: 100dvh` / `h-dvh` over brittle `100vh`
- `padding-bottom: calc(16px + env(safe-area-inset-bottom))`
- flex layouts with a scrollable middle region and fixed/sticky safe-area-aware footer
- short-height media queries to reduce vertical spacing, icon size, and nonessential decoration before clipping controls
- keypad containers that keep all digits + delete key visible
- 44x44 hit-area wrappers around visually smaller icons

## Multi-Model State Packaging

When asking multiple models to analyze the loop scenario, create claim-linked evidence:
- C: flow reached final state
- C: runtime errors/API status
- C: short viewport has clipped CTA/keypad/delete
- C: touch targets/a11y debt blocks A+ acceptance
- C: next loop priority is safe-area/keypad/CTA before cosmetics

Each evidence object must support exact claim IDs; otherwise truth gates may report no coverage even if screenshots exist.
