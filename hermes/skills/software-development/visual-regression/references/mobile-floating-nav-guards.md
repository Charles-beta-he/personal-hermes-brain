# Mobile floating navigation visual guards

Session-derived pattern from a mobile finance app UI regression sweep.

Problem:
- A full-page screenshot can make fixed/floating bottom navigation look like it is covering lower content even when the scroll container can reveal it.
- Conversely, a DOM-only overflow check can pass while the initial viewport still visually hides important content behind a translucent TabBar.
- A single home screenshot is insufficient when a page has mid-page sections such as wallets, cards, recent transactions, or other scroll-dependent blocks.

Recommended guard shape:
1. Capture viewport screenshots, not only full-page screenshots, for fixed/floating nav checks.
2. Capture at least three states for long mobile tab pages:
   - initial viewport
   - target section positioned near top (e.g. Crypto Wallets / 加密钱包)
   - scroll bottom
3. Add a deterministic DOM check that the scroll container bottom does not extend underneath the TabBar unless intentional:

```js
const tabBar = document.querySelector('nav[aria-label]');
const scroll = document.querySelector('[data-screen-scroll]');
const tabBarRect = tabBar?.getBoundingClientRect();
const scrollRect = scroll?.getBoundingClientRect();
const tabBarOverlap = tabBarRect && scrollRect ? {
  overlaps: scrollRect.bottom > tabBarRect.top + 2,
  scrollBottom: Math.round(scrollRect.bottom),
  tabBarTop: Math.round(tabBarRect.top),
  tabBarBottom: Math.round(tabBarRect.bottom),
} : null;
```

4. Use a targeted scroll helper for named sections. Choose the smallest text-containing element so the whole page wrapper is not selected:

```js
async function scrollTextNearTop(page, needle) {
  await page.evaluate((text) => {
    const scroll = document.querySelector('[data-screen-scroll]');
    if (!scroll) return;
    const target = Array.from(scroll.querySelectorAll('*'))
      .filter((el) => String(el.textContent || '').includes(text))
      .sort((a, b) => String(a.textContent || '').length - String(b.textContent || '').length)[0];
    if (!target) return;
    const scrollRect = scroll.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    scroll.scrollBy(0, targetRect.top - scrollRect.top - 12);
  }, needle);
}
```

5. Pair deterministic checks with vision review for the specific section screenshot. Ask explicitly:
   - Are the target rows/text/amounts fully readable?
   - Is the bottom nav covering content?
   - Is truncation intentional ellipsis or layout overflow?
   - Are light/dark and i18n variants readable?

Implementation fix pattern:
- If a tab-page `main` scrolls under a fixed TabBar, make the scroll container end above it, e.g. `bottom-[calc(<tabbar-space>+var(--safe-bottom))]`, rather than relying only on padding inside content.
- Still test scroll-bottom and target-section screenshots after the fix; initial viewport may legitimately not show lower sections.