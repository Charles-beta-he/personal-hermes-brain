# Evidence Request Fulfillment Loop

Use this when multi-model reviewers need factual confirmation during architecture/design/code review.

## Principle

Reviewer models are not the source of truth. They should not silently assert that they verified facts. They either cite existing `state.evidence` / `evidence_bundle.grounding`, or emit structured `evidence_requests` for the orchestrator to fulfill.

This preserves estimator/controller separation:

- Reviewer/planner models: critique, risk analysis, evidence requests.
- Orchestrator: executes tools, records outputs, updates evidence bundle.
- Truth gate: certifies only claims grounded in evidence.

## Loop

1. Build initial `state.json` with claims and any known evidence.
2. Run `consult_models.py --discussion`.
3. Collect model `evidence_requests`:
   - `claim_id`
   - `tool_needed`
   - read-only `command` or query
   - `why`
4. Filter requests through a read-only allowlist.
5. Execute approved requests with tools.
6. Redact secrets and attach outputs as new `state.evidence` entries.
7. Re-run discussion/ratification.
8. Certify only if severity>=3 claims are supported and no unresolved blocker remains.

## Read-only allowlist

Allowed by default, but keep this list deliberately narrow and argument-aware:

- `read_file`, `search_files` for explicitly scoped paths only.
- Non-content git metadata/check commands such as `git status --short`, `git diff --stat`, `git diff --name-only`, `git diff --check`, `git diff --cached --check`, `git log --oneline`, and `git show --stat` for commit-ish arguments only. Use a trusted absolute git executable (not PATH/cwd lookup) and fixed git-safe environment.
- HTTP GET only, for explicitly allowed public URLs/domains.

Rejected by default in automatic model-requested fulfillment:

- `brainctl.py`, even for status/search/evidence/wal. Brain search/evidence can disclose private vault excerpts and status/index/WAL paths; run it only as manual orchestrator-owned evidence collection outside this automatic gate.
- `anti_drift_guard.py`, even for nominally read-only checks. Its path-valued/report flags and historical `--out` behavior make it too easy to turn automatic fulfillment into a write-capable helper runner.
- Commands listed in `state.implementation_target.verify_commands`. They are build/test/orchestrator verification commands, not an evidence execution allowlist. They may be executed elsewhere by the orchestrator, but must not approve model-requested evidence execution.

Forbidden by default:

- File writes, patching, deletion, move/rename, and helper output flags such as `anti_drift_guard.py --out /tmp/x` unless the orchestrator provides a controlled artifact directory and explicit write policy.
- `git reset`, `git clean`, `git commit`, push.
- Content-producing or side-effect-prone git invocations not explicitly allowlisted: bare `git diff`, `git diff --no-index`, `git diff --output=...`, `git diff --ext-diff`, `git show HEAD:path`, or any unknown `--*` option.
- Arbitrary shell pipelines, redirection, command substitution, `&&`, `||`, `;`, glob-expansion assumptions, or commands requiring `shell=True`.
- Env/secret dumps, token inspection, credential files, `.env`, `.ssh/`, `.pem`, service-account JSON, private keys, and paths containing `credential`, `secret`, `token`, `password`, `private_key`, or similar markers.
- HTTP POST/PUT/PATCH/DELETE.
- Plugin install/enable/disable or arbitrary Obsidian commands.

## Local brain integration

For local-brain-backed evidence, do not automatically execute `brainctl.py` from reviewer-provided evidence requests. Treat reviewer requests for brain search/evidence/status as manual evidence requests for the orchestrator. If the orchestrator chooses to gather that evidence, run `brainctl.py` outside the automatic fulfillment gate, then package the resulting excerpts/hashes as normal evidence:

```bash
python3 ~/.hermes/scripts/brainctl.py --json search "query" --limit 10
python3 ~/.hermes/scripts/brainctl.py --json evidence "query" --limit 10
python3 ~/.hermes/scripts/brainctl.py --json status
```

Evidence entries should include path, heading, line range, content hash, excerpt, and command provenance. The Obsidian/brain vault remains canonical; SQLite/FTS is a rebuildable derived index.

## Anti-drift integration

Track A deterministic results should be inserted into evidence before Track B reviewers vote, but do not let reviewer-provided evidence requests automatically run `anti_drift_guard.py`. The orchestrator may run anti-drift checks manually outside the automatic fulfillment gate and then attach the resulting artifact as evidence:

```bash
python3 ~/.hermes/scripts/anti_drift_guard.py --root /path/to/repo scope --contract .omc/state/tasks/TASK.contract.json > /tmp/track-a.json
python3 ~/.hermes/scripts/anti_drift_guard.py --root /path/to/repo judge --track-a /tmp/track-a.json > /tmp/judge.json
python3 ~/.hermes/scripts/anti_drift_guard.py --root /path/to/repo consult-state --track-a /tmp/track-a.json --out /tmp/drift-review-state.json
```

Track A failures cannot be overruled by model agreement.

## Output pattern for fulfilled evidence

```json
{
  "id": "E-fulfill-001",
  "type": "tool_result",
  "summary": "brainctl search found the requested anti-drift note in canonical brain",
  "supports": ["C-001"],
  "contradicts": [],
  "command": "python3 ~/.hermes/scripts/brainctl.py --json search 'anti-drift' --limit 3",
  "artifact": "/tmp/brainctl-search.json",
  "redaction": "secrets redacted if present"
}
```

## Execution hardening requirements

- Parse with `shlex.split`, run `subprocess.run(argv, shell=False)`, and reject shell metacharacters/pipelines/redirection/command substitution before execution.
- Resolve allowed git to a trusted absolute executable and replace `argv[0]`; do not trust user PATH or a cwd fake `git`.
- Run evidence subprocesses with a minimal environment. Do not inherit provider tokens/API keys/user env. For git, include defensive settings such as `GIT_TERMINAL_PROMPT=0`, `GIT_OPTIONAL_LOCKS=0`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`, and `GIT_CONFIG_SYSTEM=/dev/null`.
- Catch `TimeoutExpired` and `OSError` and record auditable failed/timeout results; fulfillment should fail closed, not crash the CLI after partially processing requests.
- Redact credential-shaped values and credential-bearing path-like substrings in command/stdout/stderr excerpts before storing evidence.

## Claim-linking policy

A successful command must not automatically certify the model-provided `claim_id`. Treat reviewer `claim_id` as a candidate link unless an orchestrator-owned policy explicitly maps that exact command/request to that exact claim, for example `state.evidence_fulfillment_policy.claim_command_allowlist`. Without this policy, write `candidate_claim_ids` and mark the truth gate as `needs_link_review` rather than populating `supports`.

Malformed evidence requests must survive collection and appear in the fulfillment report as rejected records. Do not silently drop non-dict entries while loading from a tick directory or request file; otherwise reviewer/planner bugs disappear from the audit trail.

## Redaction requirements

Before inserting output into evidence or showing excerpts, redact at least:

- Shell/env style: `API_KEY=...`, `TOKEN=...`, `PASSWORD=...`, `SECRET=...`, `Authorization: Bearer ...`.
- JSON/YAML/TOML style: `"api_key": "..."`, `'token': '...'`, `password: ...`, `authorization = "Bearer ..."`.
- Common token shapes: GitHub `ghp_...`, Slack `xox...`, AWS access keys, PEM/private-key blocks, service-account material.

Redaction is defense-in-depth, not permission. If a command/path is credential-bearing, reject it before execution even if redaction might catch output.

## Regression tests to keep

- Reject shell metacharacters/pipes/redirection and always execute subprocesses with `shell=False`.
- Reject basename-only helper scripts, non-canonical helper paths, and fake interpreters such as `/tmp/python3` or `./python3`.
- Reject automatic `brainctl.py` fulfillment entirely, including status/search/evidence/wal forms.
- Reject automatic `anti_drift_guard.py` fulfillment entirely, including `--out` and scoped-looking path-valued forms.
- Reject content-producing or side-effect git forms: bare `git diff`, `--no-index`, `--output`, `--ext-diff`, `git show HEAD:path`.
- Verify allowed git commands use a trusted absolute git `argv[0]` and a minimal git-safe environment.
- Verify JSON-style secret redaction, env-style redaction, provider token shapes, PEM/private-key blocks, and credential-bearing output paths.
- Verify malformed requests loaded from files/tick directories are counted as rejected, including scalar top-level files, nested scalar `evidence_requests`, invalid JSON, and scalar items in a list.
- Verify `implementation_target.verify_commands` cannot approve automatic evidence execution.
- Verify no trusted policy means command success yields only candidate claim IDs, not `supports`.
- Verify subprocess `OSError` becomes an auditable failed result rather than a CLI crash.

## Pitfalls

- Do not let every reviewer model run arbitrary tools independently; that destroys reproducibility and can introduce side effects.
- Do not certify because four models agree. Certify because claims are grounded.
- Do not pass raw secrets, full env dumps, browser cookies, or tokens into state/evidence.
- If evidence requests are missing or unsafe, mark the claim unsupported rather than guessing.
- Do not let read-only evidence fulfillment become a write-capable helper runner. Even “report output” flags are side effects unless explicitly scoped and audited.
