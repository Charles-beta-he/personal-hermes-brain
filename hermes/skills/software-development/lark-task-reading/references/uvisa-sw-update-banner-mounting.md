# UVISA ServiceWorker UpdateBanner — Defined But Never Mounted

## Problem

`src/components/UpdateBanner.tsx` exists and correctly uses `useServiceWorkerUpdate('forced')` to auto-reload when a new ServiceWorker version is available. But it was never rendered in `App.tsx` or any screen.

## Impact

After an app update changes the login UI (e.g., phone login → email login), the ServiceWorker's `StaleWhileRevalidate` cache strategy serves the old JS/CSS first. Without the UpdateBanner mounted, there's no mechanism to force-reload the page when a new version is available. Users see the old login method until they manually hard-refresh.

## Fix

Mount `<UpdateBanner />` in `App.tsx` alongside `<OfflineBanner />`:

```tsx
import UpdateBanner from "./components/UpdateBanner";

// In the render tree:
<OfflineBanner />
<UpdateBanner />
```

## General pattern

When a component is created for SW update handling but never mounted:
1. Check `src/components/UpdateBanner.tsx` (or similar) exists
2. Verify it's imported and rendered in `App.tsx`
3. The `useServiceWorkerUpdate('forced')` hook handles the lifecycle: register SW → detect update → countdown → auto-reload

## Detection

```bash
# Find components that use useServiceWorkerUpdate but aren't mounted
grep -r "useServiceWorkerUpdate" src/components/ src/screens/ --include="*.tsx" -l
grep -r "UpdateBanner" src/App.tsx
# If the second grep returns nothing, the component is orphaned
```
