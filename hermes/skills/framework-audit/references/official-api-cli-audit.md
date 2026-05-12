# Official API CLI audit pattern

Use this when evaluating a vendor's official API/admin CLI (for example a new `openai/openai-cli`) for Hermes workflows, provider quota checks, or local automation.

## Evidence to collect

1. Fix identity and version:
   - GitHub repo URL, commit SHA, latest release/tag, license, created/pushed dates.
   - Package manager identities and possible impostors/stale packages (`npm view`, Homebrew tap, binary names).
   - Installation channels and checksums/assets where available.
2. Distinguish runtime class:
   - API/admin CLI vs coding-agent CLI vs SDK bin vs old similarly named package.
   - Does it execute local code, call external APIs only, or act as an agent runtime?
3. Read command surface from source, not README only:
   - Parse command registry/resources and count command groups.
   - Identify admin/usage/rate-limit/project/API-key endpoints separately from normal user endpoints.
4. Inspect secret and logging boundaries:
   - Env vars, config files, admin keys vs normal API keys, org/project scoping.
   - Debug logging redaction: headers may be redacted while request/response bodies remain sensitive.
   - Base URL / proxy flags and whether they can route secrets to non-vendor endpoints.
5. Assess local integration fit:
   - Binary name conflicts in PATH.
   - Whether global install or shell profile changes are required.
   - Whether it duplicates existing SDK/provider wrappers or fills a real automation gap.

## Safe default decision

Do not install or write global credentials during the audit. Prefer `evaluate in sandbox` unless there is an immediate, evidence-backed need.

Good P1 task-pool acceptance criteria:
- Pin exact repo/release/checksum and reject stale similarly named packages.
- Run `--help`, `--version`, representative resource help, `--format json`/transform, file input syntax with no real secrets.
- Record PATH/binary conflicts and admin-key handling.
- Decide whether to add a Hermes wrapper/skill/cron, keep it as an external optional tool, or monitor only.

## OpenAI openai-cli observed pattern (2026-05)

- Official repo: `openai/openai-cli`, Apache-2.0, Go module `github.com/openai/openai-cli`.
- It is an OpenAI REST API CLI, not the `@openai/codex` coding-agent CLI.
- There is naming confusion with the official npm `openai` SDK bin (`openai`) and an old unrelated npm `openai-cli` package.
- Useful surfaces include Responses, Models, Files, Vector Stores, Fine-tuning, Realtime, Conversations, Containers, Skills, Videos, and admin organization/project/usage/rate-limit/API-key resources.
- README warns `--debug` logs request/response details and bodies; source redacts sensitive headers, but bodies can still leak payloads.
