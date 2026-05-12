# Local brain hierarchy overlay and keypoint routing

Use this when the user asks whether to rewrite the Obsidian/local-brain main hierarchy, asks to make a theory/control model “一步到位”, or asks to land keypoint coverage into the canonical brain.

## Core decision pattern

Do not rewrite the Obsidian main hierarchy in one step just because a new theory, memory system, or multi-model routing layer looks better. Treat the existing `~/Documents/brain` top-level layout as a human navigation contract until a migration is proven better.

Prefer a semantic/control-plane overlay first:

- project/P10/P9 files under `20-projects/<project>/`;
- executable playbook under `08-实践方案/`;
- stable atoms under `10-atoms/`;
- provenance/review under `60-reviews/`;
- proof ledger under `30-tasks/`;
- evolution event under `05-进化日志/`;
- MOC updates and compact Chinese/English search aliases.

## Why overlay before rewrite

1. Main hierarchy anchors MOCs, wikilinks, historical proof logs, sync mirrors, scripts, and user browsing habits.
2. If structural gates already pass (`empty_dirs=[]`, `top_level_no_index=[]`, `broken_wikilinks_count=0`), there is no evidence-based reason to incur migration blast radius.
3. Multi-model or control-theory intervention is usually controller/routing logic, not an ontology replacement.
4. A one-shot hierarchy rewrite turns an architecture hypothesis into an irreversible information migration.

## Migration gates before any main hierarchy rewrite

Require all of these before recommending a real directory migration:

| Gate | Requirement | Evidence |
|---|---|---|
| G1 | overlay has run long enough to observe value | review/task/evolution logs, typically 4+ weeks |
| G2 | retrieval or decision quality improves measurably | before/after query benchmark |
| G3 | no structural regressions | empty dirs, hollow parents, broken wikilinks, secrets all clear |
| G4 | mapping is reversible | migration map + rollback script |
| G5 | shadow/double-write period works | old and new semantic paths both searchable |
| G6 | P10/P9 risk acceptance exists | review ledger records dissent/not_certified if present |
| G7 | user explicitly approves destructive reorganization | no implicit directory moves |

## Keypoint-to-multimodel routing landing

When covering theory points such as requisite variety, feedback stability, confidence calibration, double-loop learning, skill governance, evidence boundaries, entropy, homeostasis, reliability, or modularity:

1. Define a routing matrix with T0/T1/T2/T3, not “all four models for everything”.
2. Include first-order gate, second-order gate, and tool-evidence requirements per keypoint.
3. Add bilingual search aliases so Chinese multi-term queries hit the matrix.
4. Update the relevant self-check to assert the matrix exists and contains the required keypoints.
5. Verify with `brainctl sync`, `brainctl reindex`, Chinese search, English search, structural self-check, and a scoped local commit.

## Verification commands

```bash
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "关键点多模型介入路由矩阵 主层级不一步到位" --limit 8
python3 ~/.hermes/scripts/brainctl.py --json search "semantic overlay before hierarchy rewrite keypoint multimodel routing" --limit 8
python3 ~/.hermes/scripts/<project>_selfcheck.py --json
```

## Pitfalls

- Do not record multi-model `dissent`, `timeout`, or `truth_not_certified` as ratified evidence. It is provenance only.
- Do not embed the commit hash into the same proof note before creating the commit; report the final hash in the final response or a later commit.
- Do not stage unrelated Hermes runtime/cache/log/config churn when committing local-brain artifacts. Add only scoped paths.
