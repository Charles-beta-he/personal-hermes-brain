---
name: api-and-interface-design
description: Use when you need guidance on design principles for REST, GraphQL, tRPC, and internal APIs.
version: 1.0.0
author: Hermes Agent
license: MIT
triggers:
- design an API
- create endpoint
- add route
- new tRPC router
- GraphQL schema change
- before exposing any new interface to consumers
model: strong (DeepSeek/Claude) — API design mistakes are expensive
metadata:
  hermes:
    tags:
    - api
    - interface
    - design
    related_skills:
    - domain
    - email
    - router
---

# api-and-interface-design

## Overview


Good APIs are consistent, predictable, and self-documenting. Bad APIs multiply maintenance cost linearly with each consumer.

## When to Use

- You need guidance on design principles for REST, GraphQL, tRPC, and internal APIs
- design an API
- create endpoint
- add route
- new tRPC router
- GraphQL schema change
- before exposing any new interface to consumers
- Don't use for: requests that do not need you need guidance on design principles for REST, GraphQL, tRPC, and internal APIs; choose a more specific child skill or a broader routing skill that actually matches the task.
## Universal Principles (all API types)

### Naming
- Resource names: plural nouns (`/users`, not `/getUser`)
- Actions: HTTP methods (GET/POST/PUT/DELETE), not verbs in URL
- Consistent casing: camelCase (JS/TS), snake_case (Python)
- No abbreviations unless universally understood (`id`, not `identifier`)

### Versioning
- URL prefix: `/v1/users` (explicit, no surprise)
- Or header: `Accept: application/vnd.api+json;version=1`
- Never: silent breaking changes without version bump

### Error Handling
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": [{ "field": "email", "issue": "invalid format" }]
  }
}
```
- Always return structured errors, never raw stack traces
- Use HTTP status codes correctly (400=client, 500=server)
- Never: `{ "error": "something went wrong" }`

### Pagination
- Cursor-based (preferred): `?cursor=xxx&limit=20`
- Offset-based (simpler): `?offset=0&limit=20`
- Always return `hasMore` or `total` so consumers know when to stop

### Performance
- Support field selection: `?fields=id,name,avatar`
- Default limits: never return unlimited results
- Consider rate limiting on expensive endpoints

### Stateful Mutations and Source-of-Truth Contracts
When an endpoint changes persisted state that the client may also cache locally (trust flags, device/session state, feature entitlements, KYC/profile status, wallet/card state):
- Make the server the explicit source of truth. Client-side fallback/cache may fill missing fields for old backends, but must not override an explicit server `false`, revoked state, or authoritative value.
- Validate mutation bodies strictly. Missing/null booleans must be `400 VALIDATION_ERROR`, not silently coerced to `false`.
- Scope updates by owner/authz and active status (`WHERE user_id = :uid AND revoked = 0`), then check affected row count. `0` rows should return `404`/`403`/domain error, not success.
- Return the database/resulting state, not merely the requested value. Future policy may reject or normalize the request.
- Include contract tests for success, validation failure, wrong owner, already-revoked/not-found, unauthenticated access, and read-after-write/list/login consistency.
- When deprecating an old local fallback, add tests that explicit server values win over stale localStorage/session cache.

## tRPC-Specific (matrimonial project)
- Input validation: zod schema on every procedure
- Output typing: infer from return type, not manual
- Router organization: one router per domain (user.router, match.router)
- Middleware: auth, logging, rate-limit as reusable middlewares

## Anti-patterns
- Endpoint that does too much: `POST /processEverything`
- Inconsistent response shapes: some return `{data}`, others return raw array
- Breaking change without version: changing field type silently
- No pagination on list endpoints
- Secrets or stack traces in error responses
- Stateful mutation returns success without checking affected row count
- Local fallback/cache masks explicit server source-of-truth values

## Verification Checklist
- [ ] Naming consistent across all endpoints
- [ ] All list endpoints have pagination
- [ ] Error responses follow structured format
- [ ] No breaking changes without version bump
- [ ] Input validation on every endpoint
- [ ] Stateful mutations validate input, enforce authz/ownership, check affected rows, and return resulting persisted state
- [ ] Contract tests cover read-after-write and stale-client-cache edge cases

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

