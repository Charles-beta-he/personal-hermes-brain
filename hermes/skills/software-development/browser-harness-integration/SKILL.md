---
name: browser-harness-integration
description: Integrate comprehensive browser-based verification into automated task pipelines - combines dogfood testing, visual regression, and UIMax audit with project-type detection and viewport-specific testing
version: 1.0.0
metadata:
  hermes:
    tags: [qa, browser, testing, automation, verification, pipeline]
    related_skills: [dogfood, visual-regression, uimax-audit]
---

# Browser Harness Integration

> Integrate comprehensive browser-based verification into automated task pipelines. Combines dogfood testing, visual regression, and UIMax audit with intelligent project detection.

## When to Use

- Adding automated QA verification to task execution pipelines
- Need to verify frontend projects after code changes
- Want comprehensive testing (functional, visual, quality scoring)
- Need project-type detection for Vue, React, mobile vs desktop
- Integrating browser verification into existing automation workflows

## Core Workflow

```
Task Execution Complete
    ↓
Build Verification Passes
    ↓
Start Dev Server
    ↓
┌─────────────────────────────────────┐
│ 0. Test Ledger Walkthrough          │
│    - Read project UI test cases     │
│    - Open real browser/harness      │
│    - Actually click/type/navigate   │
│    - Inspect console/network/storage│
├─────────────────────────────────────┤
│ 1. Dogfood Testing (per page)       │
│    - Page screenshot                │
│    - Console error check            │
│    - Interactive element testing    │
│    - Issue collection               │
├─────────────────────────────────────┤
│ 2. Visual Regression Check          │
│    - Current vs baseline screenshot │
│    - AI difference analysis         │
│    - Regression detection           │
├─────────────────────────────────────┤
│ 3. UIMax / UI Skill Audit           │
│    - 6-dimension scoring (A-F)      │
│    - ui-ux-pro-max constraints      │
│    - baseline/a11y/motion checks    │
│    - Optimization suggestions       │
└─────────────────────────────────────┘
    ↓
Generate Verification Report
    ↓
Stop Dev Server
```

### User/Project Preference: Real Browser Walkthrough First

For projects with an existing UI test ledger (for example `docs/UI_TEST_CASES.md`), treat browser-harness / real-browser walkthrough as the primary UI acceptance evidence. Automated screenshot scripts such as `npm run ui:regression` are guardrails, not substitutes for opening the app and truly walking the flow.

Required sequence for UI work:
1. Read the project Workpad and UI test-case ledger before testing.
2. Start the dev/mock environment and verify health.
3. Open the page in browser-harness/real browser at the target viewport (mobile 375/390 for H5 apps unless specified).
4. Follow the documented test case step-by-step: click, type, submit, go back, interrupt flows, switch theme/language, and verify completion state.
5. Capture screenshots plus console, network, and storage observations; redact tokens/passwords/private data.
6. Apply UI quality constraints from `ui-ux-pro-max`, `uimax-audit`, `baseline-ui`, accessibility, and motion/performance skills: touch targets, safe-area/bottom-nav avoidance, no horizontal overflow, dark/i18n contrast, feedback/loading/error states, animation timing, focus/ARIA, and recovery paths.
7. For auth-gated frontend-only UI validation, if the task does not require real account/backend semantics and unit/build gates already prove the logic, it is acceptable to inject a clearly labeled test auth state into localStorage/sessionStorage to reach protected routes. Record this as `browser UI with mocked auth state`, not as full product/business acceptance. Still inspect console errors and verify rendered user-facing text/DOM state.
8. Run automated guards (`ui:regression`, Playwright, unit/build) after the real walkthrough to catch deterministic regressions.
8. Deposit evidence paths and verdicts back into the UI ledger / Workpad.

Pitfall: Do not declare UI acceptance from script screenshots alone. A script can prove selected pages render, but it may miss wrong flow semantics, broken back behavior, missing feedback, stale storage, or a visually acceptable screen reached through an invalid path.

### UI Evidence Closeout Rule

When closing a frontend/UI-affecting task, distinguish these evidence levels explicitly:

- Unit/store/service tests prove mapping/logic only.
- Multi-model review can suggest missing cases, but model agreement is not UI evidence.
- Playwright/browser-harness evidence is required before saying “UI 回测已通过” or “browser verified”.

### Prototype URL Comparison / Project Memory Capture

When the user provides a frontend prototype URL (for example a design demo or clickable product prototype) and asks whether implementation matches it:

1. Treat the URL as a durable project fact if it is project-specific: add it to the project Workpad/project memory, not global memory, and label it as `prototype/design reference` rather than a real backend/test environment unless proven otherwise.
2. Open the prototype route in browser-harness and walk the target flow, recording exact visible step labels, CTA labels, warning copy, default factor/channel, demo codes/password hints, and final state.
3. Compare against the current implementation at the same route/flow using real browser evidence plus code/test evidence when available.
4. Classify differences by source-of-truth:
   - `matches prototype`: visual/interaction semantics align.
   - `intentional task-driven divergence`: current task/PRD/security requirement supersedes prototype (e.g. replacing old-phone OTP with current-account email/SMS step-up). Do not call this a bug; explain why it is safer/better and task-compliant.
   - `prototype drift / implementation gap`: no task/PRD reason supports the mismatch; record follow-up.
5. Do not let a prototype demo path certify backend semantics. A prototype can validate UI copy/flow shape only; auth/OTP/PIN/security contracts still require real backend or inspected controller/service evidence.

For i18n/toast/error-state fixes, add at least one browser-level assertion that drives the user flow and checks the rendered user-facing text in the active language, including a negative assertion that the raw backend message in the wrong language is not visible. Prefer running both desktop Chromium and mobile viewport projects when the app is H5/mobile-first.

Evidence path durability: Playwright may clean or overwrite `test-results/` during later runs. For evidence that will be referenced in docs/Workpad/TG closeout, write reports/screenshots to a stable temp path such as `/tmp/<project>-<scope>-<date>/...` or copy them there before running additional Playwright commands.

## Implementation Pattern

### 1. Project Type Detection

```python
def _get_project_pages(project_path: str) -> List[Dict[str, str]]:
    """
    Determine which pages to test based on project type.
    
    Returns:
        List of page configs: [{"path": "/", "name": "home", "viewport": "desktop"}, ...]
    """
    pkg_json = Path(project_path) / "package.json"
    if pkg_json.is_file():
        pkg = json.loads(pkg_json.read_text())
        deps = pkg.get("dependencies", {})
        dev_deps = pkg.get("devDependencies", {})
        all_deps = {**deps, **dev_deps}
        
        # Vue 2 + Element UI (desktop)
        if "vue" in all_deps and "element-ui" in all_deps:
            return [
                {"path": "/", "name": "home", "viewport": "desktop"},
                {"path": "/login", "name": "login", "viewport": "desktop"},
                {"path": "/dashboard", "name": "dashboard", "viewport": "desktop"},
            ]
        
        # Vue 2 + Vant (mobile)
        if "vue" in all_deps and "vant" in all_deps:
            return [
                {"path": "/", "name": "home", "viewport": "mobile"},
                {"path": "/login", "name": "login", "viewport": "mobile"},
                {"path": "/market", "name": "market", "viewport": "mobile"},
            ]
        
        # React + Ant Design
        if "react" in all_deps and "antd" in all_deps:
            return [
                {"path": "/", "name": "home", "viewport": "desktop"},
                {"path": "/login", "name": "login", "viewport": "desktop"},
                {"path": "/dashboard", "name": "dashboard", "viewport": "desktop"},
            ]
    
    # Default
    return [{"path": "/", "name": "home", "viewport": "desktop"}]
```

### 2. Viewport-Specific Testing

```python
def run_dogfood_test(url: str, page_name: str, output_dir: str, viewport: str = "desktop") -> Dict[str, Any]:
    """
    Run dogfood-style exploratory testing with viewport-specific instructions.
    """
    if viewport == "mobile":
        viewport_instruction = """
### Mobile Viewport Testing (375px width):
1. Test touch interactions (tap, swipe)
2. Check mobile navigation (hamburger menu, bottom nav)
3. Verify responsive layout at 375px width
4. Test mobile-specific features (pull-to-refresh, etc.)
5. Check for horizontal scrolling issues
6. Verify touch targets are large enough (44px minimum)
"""
    else:
        viewport_instruction = """
### Desktop Viewport Testing (1280px width):
1. Test mouse interactions (hover, click)
2. Check desktop navigation (sidebar, header)
3. Verify responsive layout at 1280px width
4. Test keyboard navigation
5. Check for proper spacing and alignment
6. Verify all interactive elements are accessible
"""
    
    # Build prompt with viewport-specific instructions
    prompt = f"""## Browser QA Testing Task

Test the web page at: {url}
Viewport: {viewport} ({'375px' if viewport == 'mobile' else '1280px'} width)

### Instructions:
1. Navigate to the URL
2. Take a screenshot for visual assessment
3. Check console for JavaScript errors
4. Test all interactive elements (buttons, forms, links)
5. Check for visual issues (layout, spacing, colors)
6. Test responsive behavior (scroll, zoom)
7. Report any issues found
{viewport_instruction}
"""
```

### 3. Integration with Existing Pipeline

```python
# In executor.py - after build verification
harness_result = browser_harness.verify_with_browser_harness(envelope, dry_run=False)
if harness_result.get("success"):
    print(f"  [HARNESS OK] Grade: {harness_result.get('overall_grade')}")
    db.append_trace(eid, {
        "event": "browser_harness_passed",
        "grade": harness_result.get("overall_grade"),
        "report_path": harness_result.get("report_path"),
        "issues": harness_result.get("total_issues", 0)
    })
else:
    print(f"  [HARNESS FAIL] Grade: {harness_result.get('overall_grade')}")
    db.append_trace(eid, {
        "event": "browser_harness_failed",
        "grade": harness_result.get("overall_grade"),
        "report_path": harness_result.get("report_path"),
        "issues": harness_result.get("total_issues", 0),
        "critical": harness_result.get("critical_issues", 0),
        "high": harness_result.get("high_issues", 0)
    })
    
    # Handle issues based on severity
    critical_issues = harness_result.get("critical_issues", 0)
    high_issues = harness_result.get("high_issues", 0)
    
    if critical_issues > 0:
        notify.notify_task_failed(
            summary, 
            project_id, 
            f"Browser harness found {critical_issues} critical issues"
        )
    elif high_issues > 0:
        # High severity issues notify but don't fail the task
        notify.notify_task_completed(summary, project_id, files_changed)
        print(f"  [HARNESS WARNING] {high_issues} high issues found")
```

## Configuration

### Environment Variables

```bash
# Browser harness timeout (default: 300 seconds)
export ARC_BROWSER_HARNESS_TIMEOUT=300

# Hermes command path (default: "hermes")
export ARC_HERMES_CMD=hermes

# Screenshots directory (default: ~/.arc-dispatch/screenshots)
export ARC_SCREENSHOT_DIR=~/.arc-dispatch/screenshots

# Reports directory (default: ~/.arc-dispatch/reports)
export ARC_REPORT_DIR=~/.arc-dispatch/reports
```

### Manual Testing

```bash
# Test a single project
python3 browser_harness.py --project-path /path/to/project --project-id web_ui

# Dry run
python3 browser_harness.py --project-path /path/to/project --dry-run

# Test with specific viewport
python3 browser_harness.py --project-path /path/to/project --viewport mobile
```

## Report Structure

Reports are generated in `~/.arc-dispatch/reports/{project-id}-{timestamp}/verification-report.md`:

```markdown
# Browser Harness Verification Report

## Executive Summary
- **Project**: web_ui
- **Task**: Fix login page styling
- **Overall Grade**: B
- **Total Issues**: 3
  - Critical: 0
  - High: 1
  - Medium: 2
  - Low: 0

## Test Results

### Dogfood Testing (Exploratory QA)
| Page | Success | Issues | Console Errors | Screenshot |
|------|---------|--------|----------------|------------|
| home | ✅ | 1 | 0 | [View](screenshots/home-desktop-screenshot.png) |
| login | ✅ | 2 | 1 | [View](screenshots/login-desktop-screenshot.png) |

### Visual Regression
| Page | Regression | Severity | Differences |
|------|------------|----------|-------------|
| home | ✅ | none | 0 |
| login | ⚠️ | low | 1 |

### UIMax Audit
| Page | Visual | Responsive | A11y | Code | Interaction | Console |
|------|--------|------------|------|------|-------------|---------|
| home | A | B | C | A | B | A |
| login | B | B | B | A | B | B |
```

## Product Logic / PRD-derived Guards

When a project has product/business semantics beyond page function (funds, KYC, registration boundaries, card lifecycle, allowed rails/networks, investment scope), use `references/prd-product-logic-guards.md`. Add deterministic Playwright tests that assert PRD invariants directly, run the configured browser matrix, and update the product ledger + UI ledger + Workpad. Treat single-surface coverage as PARTIAL, not PASS.

For frontend work that depends on a writable/runnable real backend, use `references/fullstack-real-backend-verification.md`: boot both repos, start real backend dependencies, curl exact service paths, run UI guards against the live stack, classify pre-existing backend-suite failures honestly, and commit frontend/backend scopes separately.

If a task changes both frontend and backend code, local full-stack browser evidence is mandatory for UI acceptance: start the local backend, point the local frontend at it, operate the browser walkthrough/regression yourself, score UI quality, and record console/network/storage/screenshots plus backend health/exact-service-path curl evidence. Mock-server and staging/Railway can be comparison or regression surfaces, but they do not substitute for local frontend → local backend acceptance of the changed contract.

For PRD/product-flow walkthroughs against a deployed/test backend, use `references/live-backend-product-flow-triage.md`: run the local frontend through the live backend, separate route reachability from true business closure, compare legacy vs canonical APIs, attribute abnormalities to frontend/backend/config/test-seed owners, and mark safe-but-unexecuted writes explicitly.

Regression coverage must be labeled by evidence level. Frontend unit/build and mock-server fixtures prove only frontend behavior and expected contract shape; they do not certify that the real backend endpoint is filled, safe, or semantically correct. For backend-owned semantics (auth/OTP/PIN/2FA/device/session/KYC/card/wallet/topup/exchange/remittance/notification/account/profile/money/status/time/order), inspect backend controller/service/entity/repository and, when the contract changes, collect local/live backend curl or Playwright evidence plus backend targeted test/compile evidence.

## Mobile H5 Loop Gates

For mobile web / H5 apps, especially login, OTP, PIN, payment-password, email/phone security, wallet, or bottom-nav flows, apply the additional gate in `references/mobile-h5-loop-gates.md`.

For auth/payment security state machines, also apply `references/auth-pin-security-gates.md`: verify login/logout/relogin final routes, first-login PIN setup gating, unauthenticated deep-link protection, payment/card PIN reset old-PIN verification, and backend contract/follow-up evidence. Do not accept a happy-path page PASS as proof that the security state machine is correct.

For deployed email-OTP flows where the mailbox is in desktop Lark/Feishu, use `references/email-otp-lark-verification.md`: trigger OTP only when ready, foreground Lark Mail, screenshot/OCR the newest timestamped verification email, account for stale visible codes and single-use OTP consumption, and redact tokens/codes from durable docs.

Key rule: always test both a normal mobile viewport and a short mobile browser viewport. A flow can reach its final state at `390x844` while the real CTA, random keypad bottom row, or delete key is clipped at short H5 heights. Treat HIGH offscreen interactive controls on credential/payment/security paths as a loop-blocking P0/P1 issue, even if scripts can still click through.

Committed mobile-H5 gates should promote browser console errors into blocking issue-ledger findings, keep warnings visible as INFO unless tied to a user-visible failure, write evidence back to the UI ledger/Workpad, and clean up dev/mock ports before stopping.

For repeatable project gates, start from `templates/mobile-h5-issue-ledger.json`: it freezes the mainstream iOS/Android/HarmonyOS matrix, records stable issue IDs, and encodes ratchet/no-regression rules so loops cannot preserve pass rate by changing coverage, thresholds, or harness behavior.

## Pitfalls

0. **Real-backend evidence before mock alignment**: For backend-contract or security-state-machine issues, do not prove the claim with `mock-server` first and then treat it as acceptance. First run the deployed/test-env UI or local frontend connected to the real test backend, capture console/network/storage evidence, and classify whether the fix belongs to frontend or backend. Only after the real backend behavior is known should mock-server be updated to mirror the confirmed or recommended contract. If the best fix is backend-owned, record it in a frontend-repo backend-followup document (issue, evidence, recommended API shape) rather than hiding the drift with a frontend/mock shim.
1. **Dev server startup**: Always verify server is ready before testing. Use health checks.
1a. **Route reachable is not PRD PASS**: In live-backend product-flow work, a page rendering and a 200 list/detail API only proves PARTIAL. Money/card/security flows require the actual business outcome (write action, state transition, balances/notifications/ledger consistency, or documented safe non-execution). If the live account has no card/holding/payee seed, classify as FAIL/BLOCKED/PARTIAL by evidence instead of letting legacy placeholders or mock-era IDs manufacture a pass.
2. **Timeout handling**: Browser tests can be slow. Set appropriate timeouts.
3. **False positives**: Dynamic content (timestamps, random IDs) can cause visual regression false positives.
4. **Mobile viewport**: Browser tools may not always expose direct viewport controls; when available, test both normal and short mobile heights. When not available, add deterministic CSS/layout probes and screenshots for short-height states.
5. **Nested scroll containers**: Mobile H5 apps often keep `body/documentElement` fixed while the real content scrolls inside `main` or another `overflow-y:auto` container under a fixed header/bottom nav. If `browser_scroll` appears ineffective or bottom nav seems to cover below-fold content, run a DOM probe such as `Array.from(document.querySelectorAll('*')).filter(el => el.scrollHeight > el.clientHeight + 5)` to identify the scrollable container, then set `container.scrollTop` and re-screenshot before classifying the issue. Treat "fixed bottom nav overlaps first viewport but content can scroll above it" as INFO; only escalate to HIGH/P0 when critical controls or final content remain inaccessible after scrolling the actual container.
6. **Project detection**: Some projects may have unusual dependency structures. Provide fallbacks.
7. **Auth-gated route testing**: When a local frontend route is blocked by `RequireAuth` but the task is a frontend validation/layout change, create an explicit test-only authenticated browser state rather than burning the closeout budget on OTP/login. For Zustand/sessionStorage-style apps, inspect the store shape first, then set only the minimal token/user/isAuthenticated fields in `localStorage`/`sessionStorage` and reload the protected route. Label evidence as mocked-auth browser UI verification and do not use it to certify backend contracts, OTP, permission, or business-write flows.

## Key Learnings

1. **Project-specific detection**: Vue+Element UI (desktop), Vue+Vant (mobile), React+Ant Design (desktop) each need different test approaches.
2. **Viewport-specific instructions**: Mobile and desktop have different interaction patterns and accessibility requirements.
3. **Severity-based notifications**: Critical issues should fail tasks, high issues should warn but not fail.
4. **Fallback mechanisms**: Always have a fallback (e.g., simple screenshot) if browser_harness is unavailable.
5. Integration points: Browser verification should run after build verification but before task completion.
6. When a flow depends on a provided test account, verify the live deployed login contract before assuming the credential identifier type. If the user provides a phone account but the deployed UI only accepts email (or vice versa), record this as a product/backend/frontend contract mismatch and stop the deployed walkthrough at that evidence point; do not switch to mock-server or force the old identifier shape to manufacture a pass.
6a. For local-frontend-to-live-backend walkthroughs, always inspect both the frontend service/store path and backend controller/config source for abnormal states. Common high-value checks: legacy compatibility endpoints versus canonical endpoints; public config rows overriding safe fallbacks; canonical list endpoints returning empty while legacy single-object endpoints return placeholders; PRD/test ledgers containing mock-era IDs not present in live products/holdings.
7. For repeatable project gates, start from `templates/mobile-h5-issue-ledger.json`: it freezes the mainstream iOS/Android/HarmonyOS matrix, records stable issue IDs, and encodes ratchet/no-regression rules so loops cannot preserve pass rate by changing coverage, thresholds, or harness behavior.

## Integration with Other Skills

- **dogfood**: Core testing methodology for exploratory QA
- **visual-regression**: Screenshot comparison for detecting UI changes
- **uimax-audit**: Quality scoring across 6 dimensions
- **systematic-debugging**: When browser tests fail unexpectedly
- **requesting-code-review**: Can trigger browser verification as part of code review