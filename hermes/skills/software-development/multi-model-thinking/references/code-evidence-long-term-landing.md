# Code-evidence long-term landing pattern

Use this when a user asks to turn an external MCP/code-intelligence idea into a long-term Hermes project, especially with phrases like “长期项目”, “落地融合”, “loop 多模型思考自检”, or “GitNexus-inspired”.

## Goal

Do not stop at an answer or a one-off review. Land the idea as a governed Hermes-native project with durable brain artifacts, a repeatable self-check, and explicit certification caveats.

## Project Workpad landing variant

When the long-term landing target is a specific project working-memory area (not a new runtime system), create a lighter but complete package:

- `05-实践与项目/projects/<project>/Workpad - <project>.md` with North Star, Non-goals, Anchors, Red Lines, Skill Route, Business Flow Matrix, Acceptance Matrix, Evidence Ledger, Known Risks, Next Loop Queue, and Deposition Rules.
- `06-治理与评审/reviews/<date>-<project>-workpad-multimodel-review.md` with model provenance, truth status, caveats, and accepted/rejected recommendations.
- Optional `06-治理与评审/reviews/<date>-<project>-workpad-certification.json` as a machine-readable artifact; if the mirror/sync layer ignores JSON, keep the canonical JSON in `~/Documents/brain` and mention that the git mirror may only commit Markdown + scripts.
- `~/.hermes/scripts/<project>_workpad_selfcheck.py` verifying headings, required terms, searchability, secret patterns, certification caveats, and unresolved anchors.

Before writing the Workpad, run an evidence-request fulfillment pass for any anchor the models ask about: reference repo existence, route/screen inventory, package scripts, test configs, and UI test status counts. If the expected reference repo path is missing but another candidate exists, record the anchor as `unresolved/provisional`; do not claim parity certification until the user confirms the canonical reference.

## Minimal landing package

Create or update these local-brain artifacts under the canonical vault `~/Documents/brain` using the current P10 hierarchy:

- `05-实践与项目/projects/<project>/Project - <Name>.md` — north star, scope, non-goals, success criteria.
- `05-实践与项目/projects/<project>/P10 - Long-term Strategy.md` — architecture principles, phases, risks, stop condition.
- `05-实践与项目/projects/<project>/P9 - Implementation Backlog.md` — P0/P1/P2 tasks with acceptance checks.
- `05-实践与项目/实践方案/<playbook>.md` — executable loop/playbook.
- `06-治理与评审/reviews/<date>-<project>-multimodel-selfcheck.md` — provenance, model caveats, review matrix.
- `06-治理与评审/reviews/<date>-<project>-certification.json` — machine-readable certification/ratification artifact when available.
- `05-实践与项目/tasks/<date>-<project>-landing-log.md` — proof ledger with expiry/lease fields.
- `06-治理与评审/进化日志/<date>-<project>.md` — evolution event.
- `04-知识原子/atoms/<principle>.md` — durable principle/constraint card when the landing establishes a reusable boundary.
- `07-仪表盘/<dashboard>.md` — explicitly derived dashboard/control-plane view when useful.
- `08-模板/<template>.md` — reusable note/contract templates.
- Update the relevant `00-...索引.md` MOCs.

If there is a Hermes-side formal note, sync it to `99-hermes-notes/evolution/` via `brainctl sync` rather than hand-copying only one side.

## Self-check script pattern

For recurring governance projects, add a small local-first script under `~/.hermes/scripts/` that verifies the durable contract. Example checks:

- required project/strategy/backlog/playbook/review files exist;
- the governing skill reference exists and includes required patterns;
- `brainctl status` works;
- `brainctl search` finds the key terms;
- P10 health is available;
- known pre-existing warnings are reported as accepted risks only when explicitly non-blocking.

Example command:

```bash
python3 ~/.hermes/scripts/gitnexus_fusion_selfcheck.py --json
```

A self-check should distinguish:

- `FAIL`: missing required files/patterns/tools;
- `WARN`: non-blocking but new/unexplained warnings;
- `PASS`: all required checks pass, with any accepted risks explicitly listed.

Implementation pitfalls:

- `brainctl.py --json search` may return either a top-level list of hits or a dict containing `results`/`hits` depending on the command/version. Self-check scripts must accept both shapes instead of assuming `data.get(...)`.
- If a self-check requires claim/evidence IDs (for example `C-001` / `E-001`), ensure the landed Workpad/review actually contains a compact claim/evidence index. Do not make the verifier depend on IDs that only exist in `/tmp` state or tick artifacts.
- Run `python3 -m py_compile <selfcheck.py>` before sync/reindex/self-check, because quoting in secret regexes is a common source of late SyntaxError failures.

## Verification loop

Run after every landing iteration:

```bash
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "<project key phrase>" --limit 10
python3 ~/.hermes/scripts/brainctl.py --json search "<gate key phrase>" --limit 10
python3 ~/.hermes/scripts/<project>_selfcheck.py --json
```

Also run a structural audit for:

- empty dirs = 0;
- top-level dirs missing direct MOC/index = 0;
- broken wikilinks = 0;
- sensitive pattern hits = 0.

If scripts changed, run `python3 -m py_compile <script>` and any relevant self-test.

## Certification caveats

- A completed fanout is not ratification. If discussion/ratification timed out, was killed, or produced `dissent`/`not_certified`, say so.
- If a `consult_models.py --discussion` background process hangs after all planner outputs and `merged_plan.json` are present but no `discussion_result.json` appears, inspect the tick directory before waiting indefinitely. Record `fanout_status`, `consensus_verdict`, `consensus_score`, `unanimous_count`, `majority_count`, `minority_count`, and `arbitration_needed` from `merged_plan.json`; if necessary kill the stuck process and mark the artifact as provenance-only / weak consensus.
- Exit code `-15` from a background multi-model process means SIGTERM; if the orchestrator killed it after useful artifacts were created, treat artifacts as provenance only.
- Do not retroactively promote historical fanout artifacts to certified consensus.
- For GitNexus-style systems, say “Hermes-native methodology extraction” or “GitNexus-inspired code-evidence pattern,” not “adopted GitNexus runtime.”

## Git hygiene

After verification, make a scoped local commit containing only the relevant script/skill/brain artifacts. Do not push unless the user explicitly asks.

If `~/Documents/brain` is not itself a git repository, do not `git init` it automatically. Check whether the vault is mirrored inside the Hermes repo (for example `~/.hermes/notes/brain`) and make the scoped commit there instead. Before committing, stage only paths for the current landing and explicitly avoid `.env`, auth files, cache, checkpoints, screenshots, and unrelated brain changes.

If task logs move from `running` to `done` during finalization, rerun the self-check afterward. Update any self-check phrase assertions that still expect the pre-finalization lifecycle state; a stale verifier should fail closed, then be patched and rerun.
