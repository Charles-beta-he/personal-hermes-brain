---
name: uimax-audit
description: Use when you need guidance on uIMax — Systematic UI quality audit with A-F grading.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - qa
    - ui
    - audit
    - grading
    - browser
    - accessibility
    related_skills:
    - color-contrast-checker
    - design
    - dogfood
    - loop
    - p10
    - plan
    - popular-web-designs
    - router
---

# UIMax — UI Quality Audit with A-F Grading

## Overview


> Comprehensive UI quality scoring across 6 dimensions. Goes beyond bug-finding (dogfood) into quality measurement and optimization planning.

## When to Use

- User says "UIMax", "UI审计", "UI评分", "UI检查", "UI走查"
- Before/after optimization loops to measure improvement
- Pre-release quality gates
- Don't use for: requests that do not need you need guidance on uIMax — Systematic UI quality audit with A-F grading; choose a more specific child skill or a broader routing skill that actually matches the task.
## Scoring Dimensions

| Dimension | What to Check | A Criteria |
|-----------|--------------|------------|
| Visual Design | Layout, spacing, typography, color, hierarchy | Consistent, polished, clear hierarchy |
| Responsiveness | Mobile/desktop, breakpoints, overflow | Works well at 375px and 1280px+ |
| Accessibility | ARIA, tabIndex, :focus, contrast, keyboard nav | Full keyboard operability, screen reader support |
| Code Quality | Inline styles, CSS vars, hardcoded colors, keyframes | Minimal static inline styles, CSS vars for all colors |
| Interaction | Animations, transitions, feedback, loading states | Smooth, non-blocking, respects prefers-reduced-motion |
| Console Health | JS errors, failed API calls, warnings | Zero JS errors |

**Grades**: A (excellent) → B (good) → C (passable) → D (poor) → F (fail)

## Workflow

### Phase 1: Visual Audit (browser tools)

For each page/component:

1. **Read the UI test ledger first** (`docs/UI_TEST_CASES.md`, project Workpad, or equivalent) and choose the exact flow/status to verify.
2. **Navigate** to the page in browser-harness / a real browser at the target viewport.
3. **Actually perform the documented flow**: click, type, submit, back/interrupt, switch theme/language, and confirm finish/error states. Do not score from screenshots alone.
4. **Check console** for JS errors: `browser_console(clear=true)`
5. **Inspect network/storage where relevant**; redact tokens/passwords/private values in reports.
6. **Screenshot + analyze**: `browser_vision(question="Analyze UI quality...", annotate=true)`
7. **Test interactions**: touch target size, press feedback, loading/error states, fixed header/bottom-nav safe-area, keyboard/focus/ARIA, reduced-motion, dark/i18n contrast.
8. **Note issues** with severity and category, and link each issue to the test case ID and evidence path.

**Important**: React CSR apps may show "Empty page" in browser_snapshot. Use browser_vision screenshots instead.

**Acceptance rule**: UIMax scoring is secondary to flow truth. A visually polished screenshot is not a pass if the documented business flow was not actually completed through the browser.

### Phase 2: Code Audit (terminal/file tools)

Scan source code for quality metrics:

```
# Inline styles count per file
search_files(r'style=\{', target='content', path='src/', file_glob='*.jsx')

# ARIA attributes
search_files(r'aria-', target='content', path='src/', file_glob='*.jsx')

# tabIndex usage
search_files(r'tabIndex', target='content', path='src/', file_glob='*.jsx')

# Focus styles in CSS
search_files(r':focus', target='content', path='src/', file_glob='*.css')

# Hardcoded colors (not CSS vars)
search_files(r"(?:color|background|border).*#[0-9a-fA-F]{3,8}", target='content', path='src/')

# prefers-reduced-motion
search_files(r'prefers-reduced-motion', target='content', path='src/')

# CSS variable coverage
# Count defined vs used in CSS files
```

### Phase 3: Generate Report

Write `UIMAX_REPORT.md` with:
1. Overall scores per dimension (table)
2. Per-page/component grades
3. Code quality statistics
4. Prioritized issue list (P0/P1/P2)
5. Optimization roadmap for next loop iteration

### Phase 4: Optimization (P10 strategy)

Based on scores, prioritize:
1. **P0 (blocking)**: Accessibility gaps — tabIndex, :focus, ARIA
2. **P1 (important)**: Static inline style migration, hardcoded colors
3. **P2 (nice-to-have)**: CSS variable coverage, responsive polish

After fixes: `pnpm test && pnpm build` → re-run Phase 1-3 to verify improvement.

## Key Findings from Experience

### Accessibility Patterns (proven effective, ARIA +350%)

**1. Global focus-visible** — Add to index.css:
```css
*:focus-visible {
  outline: 2px solid var(--accent-primary, #00d4ff);
  outline-offset: 2px;
}
button:focus-visible, a:focus-visible, [role="button"]:focus-visible,
input:focus-visible, select:focus-visible, textarea:focus-visible {
  outline: 2px solid var(--accent-primary, #00d4ff);
  outline-offset: 2px;
  box-shadow: 0 0 0 4px rgba(0, 212, 255, 0.15);
}
*:focus:not(:focus-visible) { outline: none; box-shadow: none; }
```

**2. Clickable divs → accessible buttons** — Game cards, interactive divs:
```jsx
<div role="button" tabIndex={0} aria-label="Game Name - Description"
     aria-disabled={!isInstalled}
     onClick={() => isInstalled && handleSelect()}
     onKeyDown={e => { if (isInstalled && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); handleSelect() }}}>
```

**3. `<span onClick>` → `<button>`** — Theme arrows, any clickable span:
```jsx
// Before: <span onClick={prev} className="cursor-pointer">‹</span>
// After:
<button onClick={prev} aria-label="Previous theme"
        className="cursor-pointer bg-transparent border-none">‹</button>
```

**4. Toggle buttons** — Difficulty/style selectors:
```jsx
<button aria-pressed={active} aria-label="Label - Description"
        className={active ? 'selected-styles' : 'default-styles'}>
```

**5. Tab navigation** — Desktop + mobile tab bars:
```jsx
<div role="tablist" aria-label="Section name">
  <button role="tab" aria-selected={activeTab === id} aria-controls={`panel-${id}`}>
</div>
```

**6. Skip-to-content links** — First element in component:
```jsx
<a href="#main-content"
   className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[999] ...">
  Skip to content
</a>
// ... later ...
<main id="main-content">
```

**7. Live regions** — Dynamic status indicators:
```jsx
<div role="status" aria-live="polite">
  {isOnline ? 'Connected' : 'Offline'}
</div>
```

**9. Form label associations** — Convert visual labels to `<label htmlFor>`:
```jsx
// Pattern A: wrap existing visual label text
<label htmlFor="quick-join-input" className="text-[11px] text-theme-muted block">
  QUICK JOIN — 已有邀请码？
</label>
<input id="quick-join-input" type="text" aria-label="输入邀请链接或房间码" />

// Pattern B: sr-only label when visual label is separate
<label htmlFor="room-code-input" className="sr-only">输入 6 位房间码</label>
<input id="room-code-input" aria-label="输入 6 位房间码" />

// Pattern C: convert adjacent <span> to <label>
// Before: <span className="text-[10px]">规则</span><select ...>
// After:  <label htmlFor="rule-select" className="text-[10px]">规则</label>
//         <select id="rule-select" ...>
```

**8. Semantic landmarks** — header/footer/nav with roles:

**10. aria-pressed filter buttons** — Game type filter tabs:
```jsx
const filterLabels = { all: '全部', gomoku: '五子棋', go: '围棋' }
{Object.entries(filterLabels).map(([key, label]) => (
  <button
    key={key}
    onClick={() => setFilter(key)}
    aria-pressed={filter === key}
    aria-label={`筛选: ${label}`}
    className={filter === key ? 'active-styles' : 'inactive-styles'}
  >{label}</button>
))}
```

**11. Card view ↔ List view toggle** — "查看全部" pattern:
```jsx
const [showAll, setShowAll] = useState(false)
<button onClick={() => setShowAll(v => !v)} aria-label={showAll ? '返回卡片视图' : '查看全部'}>
  {showAll ? '‹ 返回' : '查看全部 >'}
</button>
{showAll && <ListView items={items} />}  {/* full list with per-item actions */}
{!showAll && <CardView item={items[currentIndex]} />}  {/* single card + floating actions */}
```

### New Page from Screenshot Workflow

When implementing a new page from a mobile screenshot reference:

### Step 1: Analyze Screenshot
Use `vision_analyze` to extract: element hierarchy, colors, spacing, component types.

### Step 2: Create Page Component
Standard structure for a mobile-first page:
```jsx
import { useState, useCallback, useEffect } from 'react'
import BottomNav from '../components/BottomNav.jsx'

export default function NewPage() {
  // State machine: idle → loading → loaded | empty | error
  const [status, setStatus] = useState('loading')
  
  return (
    <div className="min-h-[100svh] bg-theme-primary text-theme-primary font-theme flex flex-col">
      <a href="#page-content" className="sr-only focus:not-sr-only ...">Skip to content</a>
      <header role="banner">...</header>
      <main id="page-content" role="main" className="flex-1 px-4 sm:px-5 pb-28 overflow-y-auto">
        {/* content */}
      </main>
      <BottomNav active="page-id" />
    </div>
  )
}
```

### Step 3: Add Route
In `router/index.jsx`:
```jsx
const NewPage = lazy(() => import('../pages/NewPage.jsx'))
// Add to ROUTES array
{ path: '/new-page', label: 'NewPage', element: <NewPage /> }
```

### Step 4: Verify
`pnpm test && pnpm build` → browser_navigate → browser_vision → browser_console

### BottomNav Pattern
Fixed bottom nav with 4 items, aria-current highlighting:
```jsx
<nav role="navigation" aria-label="主导航"
  className="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around bg-theme-surface border-t border-theme"
  style={{ height: 56, paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
  {items.map(item => (
    <button key={item.id} onClick={() => navigate(item.path)}
      aria-label={item.label} aria-current={activeId === item.id ? 'page' : undefined}
      style={{ color: isActive ? 'var(--accent-primary)' : 'var(--text-muted)' }}>
      {item.icon}
      <span className="text-[10px]">{item.label}</span>
    </button>
  ))}
</nav>
```

## Code Audit Quick Wins

```bash
# Count ARIA improvement (before vs after)
search_files(r'aria-', target='content', path='src/', file_glob='*.jsx')

# Count focus-visible rules
search_files(r':focus-visible', target='content', path='src/', file_glob='*.css')

# Count semantic landmarks
search_files(r'<(main|nav|header|footer)\\b', target='content', path='src/', file_glob='*.jsx')

# Find remaining <span onClick> (should be zero)
search_files(r'<span[^>]*onClick', target='content', path='src/', file_glob='*.jsx')

# Count aria-pressed usage
search_files(r'aria-pressed', target='content', path='src/', file_glob='*.jsx')
```

### Practical Tips

- **CSR snapshot issue**: browser_snapshot returns "Empty page" for React CSR — always use browser_vision for visual assessment
- **Buttons missing ref IDs in snapshot**: Some dynamically rendered buttons (e.g., inside conditional `{!selectedMode && ...}` blocks) appear in the accessibility tree but don't get assigned clickable ref IDs. Workaround: `browser_console(expression="document.querySelector('button[aria-label*=\"keyword\"]').click()")`
- **browser_click 30s timeout**: Can time out on slow pages. Fallback to browser_console JS click.
- **Inline styles with CSS vars**: Not all inline styles need migration — those using `var(--accent-primary)` are theme-aware and acceptable
- **Diminishing returns**: After ARIA fixes, inline style migration has low impact — prioritize accessibility first
- **Audit before fixing**: Always verify current state before assuming gaps. ModeSelect cards appeared to lack keyboard support in browser_snapshot (no ref IDs), but code inspection showed they were already proper `<button>` elements. The real gap was label/htmlFor (1→4). Cross-reference snapshot with source code.
- **Build verification**: Always run `pnpm test && pnpm build` after changes — tests don't cover all web components

## New Page from Screenshot Workflow

### Responsive Breakpoint Audit

Count breakpoint usage to identify mobile-first gaps:
```bash
search_files(r'sm:', target='count', path='src/', file_glob='*.jsx')
search_files(r'md:', target='count', path='src/', file_glob='*.jsx')
search_files(r'lg:', target='count', path='src/', file_glob='*.jsx')
```

**Key pattern**: `px-8` (32px each side = 311px content on 375px screen). Fix:
```jsx
// Before (desktop-only):
className="px-8 py-12"
// After (mobile-first):
className="px-4 sm:px-8 py-6 sm:py-12"
```

Apply to: header, main content, footer, nav bars. Goal: sm: count 2-3x md: count.

### P10 Code Quality Triage

Before mass-migrating inline styles, audit whether they're actually low quality:
```bash
search_files(r"style=\{\{(?!.*var)", target='content', path='src/', file_glob='*.jsx')
```

**Decision rule**: If 90%+ inline styles use `var(--*)`, they're theme-aware and B is a fair score. Further migration has diminishing returns. Focus on responsive/a11y instead.

### Grid Background Subtlety

Lobby/hero grid backgrounds can overwhelm content. Fix:
```jsx
<div aria-hidden style={{
  backgroundImage: `linear-gradient(var(--board-line-glow) 1px, transparent 1px)...`,
  backgroundSize: '60px 60px',  // larger = less dense
  opacity: 0.5,                  // reduce prominence
  pointerEvents: 'none',
  zIndex: 0,
}} />
```

## CSS Utility Class Migration (code quality B→A)

When inline styles use `var(--accent-danger)` or `var(--accent-success)` repeatedly, create CSS utility classes:

**Step 1**: Add to `index.css` @layer utilities:
```css
.text-danger     { color: var(--accent-danger); }
.text-warning    { color: var(--accent-warning, #ff9f43); }
.text-success    { color: var(--accent-success); }
.bg-danger-subtle { background: color-mix(in srgb, var(--accent-danger) 8%, var(--bg-surface)); }
.border-danger   { border-color: var(--accent-danger); }
.border-danger-subtle { border-color: color-mix(in srgb, var(--accent-danger) 30%, transparent); }
```

**Step 2**: Replace inline styles across files:
```bash
# Find all occurrences
search_files(r"style.*accent-danger", target='content', path='src/', file_glob='*.jsx')
# Replace: style={{ color: 'var(--accent-danger, ...)' }} → className="... text-danger"
```

**Step 3**: For conditional colors, use template strings:
```jsx
// Before:
<div className="text-xs" style={{ color: isInstalled ? 'var(--accent-success)' : 'var(--text-muted)' }}>
// After:
<div className={`text-xs ${isInstalled ? 'text-theme-success' : 'text-theme-muted'}`}>
```

**Impact**: Reduces inline style count and improves readability. 12+ replacements typical.

## Responsive Deep Audit (375px A+)

Scan ALL files for non-responsive large paddings:
```bash
# Find px-6/8/10/12 without sm: variant
search_files(r'px-[6-9]|px-1[0-2]', target='content', path='src/', file_glob='*.jsx')
# Check each result: does it have sm:px-N? If not, fix it.
```

**Fix pattern** (mobile-first):
```jsx
// Header/Footer:
className="px-4 sm:px-8 py-3 sm:py-4"
// Main content:
className="px-4 sm:px-8 py-6 sm:py-12"
// Gaps:
className="gap-4 sm:gap-6"
// Grid minmax:
style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))' }}
```

**Target**: sm: count should be 2-3x md: count. If sm: < md:, mobile is underserved.

## Multi-Round Audit Metrics Tracking

Use `execute_code` for batch metric scanning between rounds:
```python
import subprocess
scans = [
    ('aria', ['rg', '-c', 'aria-', 'src/', '-g', '*.jsx']),
    ('aria_pressed', ['rg', '-c', 'aria-pressed', 'src/', '-g', '*.jsx']),
    ('label_htmlFor', ['rg', '-c', '<label|htmlFor', 'src/', '-g', '*.jsx']),
    ('sm_breakpoint', ['rg', '-c', 'sm:', 'src/', '-g', '*.jsx']),
    ('inline_styles', ['rg', '-c', 'style=\\{', 'src/', '-g', '*.jsx']),
    ('span_onClick', ['rg', '-c', '<span[^>]*onClick', 'src/', '-g', '*.jsx']),
]
# Track deltas between rounds to measure improvement velocity
```

## Companion Skills

- **color-contrast-checker**: WCAG AA/AAA 对比率自动验证。扫描 CSS 主题变量，计算所有前景/背景配对的对比度，输出合规报告。用于无障碍维度评分。
- **visual-regression**: browser_vision 截图 diff 对比。建立基线截图 → 变更后截图 → AI 对比差异 → 回归报告。用于迭代验证无 UI 退化。
- **popular-web-designs**: 54 套生产级设计系统参考（Stripe, Linear, Vercel 等）。用于视觉设计维度对标。

## Definition of Done

- [ ] **Outcome**: Scores (A-F) assigned to all 6 dimensions, UIMAX_REPORT.md generated with per-page grades
- [ ] **Process**: Visual audit (browser_vision + browser_console) + code audit (search_files for aria/inline styles/breakpoints) completed for every page
- [ ] **Style**: Report includes prioritized issue list (P0/P1/P2) + optimization roadmap, code quality metrics tracked
- [ ] **Efficiency**: `pnpm test && pnpm build` verified after fixes, regression re-audit shows improvement (not same scores)

## Loop Integration

This skill pairs with `p10` for optimization and `loop` for iterative improvement:
1. UIMax audit → scores
2. P10 strategy → optimization plan
3. Execute fixes
4. UIMax re-audit → verify improvement
5. Loop until all A

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] The Definition of Done items above were explicitly checked, not assumed.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

