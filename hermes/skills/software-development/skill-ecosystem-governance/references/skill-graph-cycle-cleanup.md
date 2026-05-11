# Skill Graph Cycle Cleanup Reference

Use this when `skill-steward.py --graph-check --json` reports cycles or excessive depth in the Hermes skill ecosystem.

## Workflow

1. Generate the graph report:
   ```bash
   python3 ~/.hermes/scripts/skill-steward.py --graph-check --json --warn-only > /tmp/skill-graph.json
   ```
2. Group cycles by strongly connected component (SCC), not by individual cycle. A dense SCC can produce many cycle paths; fix the component once.
3. For each SCC, choose a single direction of dependency flow:
   - umbrella/orchestrator -> implementation variants
   - workflow stage N+1 -> prerequisite stage N
   - specialized skill -> lower-level primitive
   - never peer <-> peer
4. Edit only `related_skills` frontmatter first. Prefer removing or inverting edges over changing body content.
5. Preserve discoverability with a DAG chain when useful, e.g. `claude-code -> codex -> opencode`, instead of clearing every edge.
6. Re-run strict gate:
   ```bash
   python3 ~/.hermes/scripts/skill-steward.py --graph-check --json
   ```
7. Regenerate the checked-in report only after strict gate is OK. Do not redirect stdout to the same report path that `skill-steward.py` also writes internally; write to a temp file, validate, then copy:
   ```bash
   python3 ~/.hermes/scripts/skill-steward.py --graph-check --json > /tmp/skill-graph-report.json
   python3 -m json.tool /tmp/skill-graph-report.json >/dev/null
   cp /tmp/skill-graph-report.json ~/.hermes/skills/steward/skill-graph-report.json
   ```
8. Run self-test and diff check, then commit.

## Pitfalls

- Do not stop at `--warn-only` if the user asked for exhaustive loop / no missing progress. Warn-only is diagnostic; strict OK is the closure condition.
- Do not fix 24 cycle paths one by one. They may collapse to a handful of SCCs.
- Do not over-prune. Claude/peer review may flag discoverability regressions if all peer links are removed. Convert mutual links into one-way DAG links.
- Do not introduce environment-specific account/model facts while editing shared skills. Provider mappings belong in config or memory, not generic SKILL.md body.
- A transient self-test failure should be isolated by running the failing subtest directly, then self-test again; do not declare success from a failed aggregate run.

## Verification closure

A complete cleanup should show:

```text
status=OK
cycles=0
depth_max <= HERMES_SKILL_GRAPH_MAX_DEPTH
typed_violations=[]
excessive_depth=[]
Self-Test Results: 64/64 passed  # or current expected total
```
