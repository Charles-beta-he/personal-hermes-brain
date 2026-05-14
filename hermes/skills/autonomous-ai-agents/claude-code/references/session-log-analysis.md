# Claude Code session log analysis

Use this when the user asks to analyze past Claude Code conversations to infer work habits, workflow, project goals, recurring requirements, or project governance. Keep this evidence-first: logs are private development history, not generic telemetry.

## Where Claude Code stores project sessions

For a project path such as:

`/Users/charles/Desktop/folder/work/uvisa-app-2.0`

Claude Code's global session directory commonly normalizes the path into:

`~/.claude/projects/-Users-charles-Desktop-folder-work-uvisa-app-2-0/`

Look for `*.jsonl` files. Also inspect in-repo Claude context:

- `CLAUDE.md`
- `.claude/skills/**/SKILL.md`
- `.claude/rules/*.md`
- `.claude/agents/*.md`
- docs that the sessions created or repeatedly reference, e.g. `docs/UI_TEST_CASES.md`, `docs/decisions/*.md`

## Safe extraction pattern

1. Inventory first, do not dump whole logs into the final answer.
2. Parse JSONL and separate:
   - direct user prompts: `type=user`, `message.content` is a string
   - tool results: `message.content` is usually a list; keep out of user-habit inference unless needed as evidence
   - assistant text summaries: `type=assistant`, `message.content[].type=text`
   - agent dispatch prompts: assistant `tool_use` with `name=Agent` or `Task`
   - AI titles: `type=ai-title`, `aiTitle`
3. Redact secrets before writing any extracted corpus:
   - tokens, API keys, passwords, auth headers, JWTs, connection strings
4. Build a compact evidence file with IDs rather than raw transcript dumps:
   - session count, prompt count, key user quotes, theme counts
   - project structure facts from code/docs/git
   - claim→evidence links
5. Cross-check claims against project artifacts, not only conversation text:
   - `package.json` scripts/dependencies
   - route/screen inventory
   - testing docs
   - ADRs
   - recent git log/status
6. If the user requested multi-model analysis, run the compact state through `consult_models.py` with explicit claims and evidence links; avoid sending huge raw logs.

## Evidence categories that worked well

- E1 session inventory: number of JSONL sessions and direct user prompts
- E2 project stack from `package.json`
- E3 routes/screens inventory from source
- E4 testing/governance docs such as `docs/UI_TEST_CASES.md`
- E5 ADR index / project decisions
- E6 recent git log themes
- E7 selected direct user prompt quotes
- E8 in-repo Claude skills/rules that encode workflow

## Useful derived signals

Count themes over direct user prompts, selected assistant summaries, and agent dispatch prompts:

- long-running autonomy: `loop`, `pua-loop`, `continue`, `until`, `no next pass`
- quality gates: `P10`, `A+`, `verification`, `build`, `test`, `Playwright`, `browser-harness`
- closure gaps: `dead UI`, `missing`, `unclosed`, `state page`, `dead route`, `decorative button`
- drift constraints: `do not change UI`, `preserve fields`, `parity`, `reference project`, `prototype drift`
- backend alignment: `mock`, `service`, `real backend`, `API`, `404`, `route-aligned`

Theme counts are supporting evidence, not proof by themselves. Pair them with direct quotes and code/docs.

## Multi-model state shape

A compact state works better than raw logs:

```json
{
  "question": "Analyze Claude Code session records to infer user work habits, workflow, and project goals.",
  "constraints": [
    "Do not expose secrets",
    "Use evidence from session prompts, project files, git log, and docs",
    "Separate habits/workflow/project goals",
    "Mark uncertainty"
  ],
  "evidence": [
    {"id": "E1", "summary": "5 sessions; 217 direct prompts", "supports": ["C-001"]},
    {"id": "E2", "summary": "package.json stack/scripts", "supports": ["C-003"]}
  ],
  "claims": [
    {"id": "C-001", "claim": "User drives long-running autonomous loops", "severity": 2}
  ]
}
```

Make sure `claims` are in the top-level field expected by the truth gate, not merely a `claims_to_check` note. A prior run with only `claims_to_check` produced `truth_status=no_claims`; adding proper `claims` and `evidence[].supports` produced grounded verification.

## Output guidance

- Final answer should summarize the strongest findings with confidence and caveats.
- Provide artifact paths: compact evidence, raw parsed analysis if created, multi-model tick, and any local-brain note.
- Do not paste private transcript dumps.
- If the analysis yields stable user preferences, update memory and/or the user's local-brain profile, but keep the durable memory compact.

## Project profile update workflow from a resumed session

When the user asks to analyze a specific `resume <session-id>` or Claude Code JSONL session and update a project profile:

1. Locate the exact JSONL by session id first; do not assume the normalized project directory. Claude may store a resumed session under a broader directory such as `~/.claude/projects/-Users-charles/<session-id>.jsonl` even when the work spans a specific repo.
2. Parse, redact, and summarize into a compact evidence artifact. Include counts, cwd distribution, selected direct user quotes, tool-use counts, project-file cross-checks, and git/doc evidence. Keep raw transcript text out of final answers and persistent notes.
3. Convert candidate updates into explicit top-level claims and claim-linked evidence. Evidence must use exact claim ids in `supports`; otherwise multi-model truth gates can report unsupported/no-claims even when the files were read.
4. Run multi-model analysis when requested, but distinguish `truth_status=grounded` from full ratification. If `discussion_result.status=not_certified` or the certification manifest fails approval/agreement gates, treat the result as advisory: apply only low-risk durable profile clarifications that are directly evidence-grounded, and record the caveat in profile update history/local-brain notes.
5. Update both the machine profile (for example `~/.hermes/project-profiles/<project>.json`) and the human Workpad/brain handoff note when the profile is used by future agents. Then run JSON validation, project/workpad self-checks when available, `brainctl sync`, `brainctl reindex`, and search verification for the new anchors.

## Pitfalls

- Do not treat assistant summaries as equivalent to direct user preferences; direct user prompts outrank assistant descriptions.
- Do not infer broad life preferences from one project unless the user asks for a long-term profile and evidence repeats across sessions.
- Do not expose credentials or demo secrets from tool results in the final summary.
- Do not rely on multi-model consensus alone; use the truth gate claim/evidence grounding.
- For large logs, avoid feeding raw JSONL to models. Extract, redact, sample, and link evidence first.
