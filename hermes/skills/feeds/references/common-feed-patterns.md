# Common Feed Patterns

## Feed discovery order

1. Parse explicit `<link rel="alternate">` tags from the homepage.
2. Try common paths only after explicit links fail: `/feed`, `/rss`, `/atom.xml`, `/feed.xml`, `/index.xml`.
3. Preserve redirect information and report the final canonical URL.

## Dedupe key preference

1. Stable GUID or Atom id.
2. Canonical item URL.
3. `(title, published)` tuple.
4. Content hash only as a fallback for changed-content detection.

## Monitor state

Keep monitor state small and deterministic: source URL, last successful fetch, seen IDs/hashes, and last error. Do not write state after a failed parse.
