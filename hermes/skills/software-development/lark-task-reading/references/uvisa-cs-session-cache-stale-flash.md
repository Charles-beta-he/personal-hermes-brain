# UVISA CS Session Stale Cache Flash

## Problem

`src/data/csSession.ts` uses module-level in-memory variables (`msgs`, `active`, `loading`) that persist across page navigations. When the user navigates to the Customer Service chat screen, `useCsMsgs()` initializes with the stale `msgs` array, then calls `refreshCsSession()` which fetches fresh data. The result: a flash of old messages before the UI updates.

## Root cause

```typescript
// Module-level state — persists across navigations
let msgs: CsMsg[] = [];
let active = false;

export function useCsMsgs(): CsMsg[] {
  const [s, set] = useState<CsMsg[]>(msgs); // ← starts with stale data
  useEffect(() => {
    void refreshCsSession(); // ← fetches fresh, but UI already rendered stale
    // ...
  }, []);
  return s;
}
```

## Fix

Clear stale messages at the start of `refreshCsSession()` before the API call:

```typescript
export async function refreshCsSession(): Promise<void> {
  if (loading) return loading;
  loading = (async () => {
    try {
      // Clear stale in-memory messages before fetching fresh data
      if (msgs.length > 0) {
        msgs = [];
        notify(); // ← triggers re-render with empty state
      }
      const res = await csService.getSession();
      if (res.success) applySession(res.data);
    // ...
```

## General pattern

When a module-level cache persists across navigations and a hook initializes from it:
1. Clear the cache at the start of the refresh function, not in the hook mount
2. Call `notify()` after clearing so subscribers re-render with empty state
3. The API response fills in fresh data moments later

This is better than initializing with `[]` in the hook (which would break the shared-state contract) or adding a `loading` flag (which changes the hook's return type).
