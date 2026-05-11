# Image / Social-Post Architecture Idea → Taskpool Optimization Advisory

Use this when the user provides a screenshot/infographic/social post and asks for multi-model analysis plus adding an optimization plan to the local-brain task pool.

## Pattern

1. Extract image facts first with vision/OCR.
   - Save the exact image path.
   - Extract visible claims, named components, dates/authors if shown, and metrics only as visible metadata.
   - Do not treat popularity metrics as truth of technical merit.
2. Build a claim-linked evidence bundle for `consult_models.py state`.
   - Claims should cover what the image visibly proposes and the orchestrator's mapping to Hermes-native concepts.
   - Evidence objects must explicitly support exact claim IDs.
   - Include constraints such as: no wholesale runtime adoption, preserve fail-closed taskpool safety, no duplicate canonical memory/skill/plugin stack.
3. Run T2/T3 fan-out when the request affects Hermes architecture, taskpool automation, hooks, plugins, or subagents.
4. If `run --discussion` times out, inspect the matching tick and resume discussion only for the tick whose `state.json.question` and claim texts match the image task.
5. Distinguish result classes:
   - `truth-grounded advisory`: image claims and high-level mapping are grounded, but implementation patches are not certified.
   - `implementation-certified`: discussion_result exists, ratification gates pass, and patch-family claims have deterministic/file evidence.
6. When adding to local-brain taskpool, record the certification class honestly.
   - A task can be created from a truth-grounded advisory.
   - The task must say follow-up implementation needs evidence-request fulfillment and a second certification pass.

## Recommended task note sections

- Source image path.
- OCR/vision extracted architecture.
- Consult state path and tick path.
- Models reached in fan-out.
- Truth gate status and certification status.
- Adopt / Reject boundary.
- P0/P1/P2 implementation plan.
- Execution protocol: fulfill evidence_requests → rebuild implementation claims → rerun ratification → smallest patch → deterministic checks → scoped commit.
- Blocker: do not claim implementation certification from a not_certified discussion.

## Pitfalls

- Do not upgrade `fanout_quorum_met` to full certification; require `discussion_result.json` and certification manifest gates.
- If `planner_patch_summary.certification_intent=implementation_required` but `merged_plan.patches=[]`, treat it as not-certified or advisory until issue ledger is resolved.
- A social-post architecture idea is usually a design prompt, not an authoritative source. Validate against current Hermes files before changing runtime behavior.
- Keep taskpool automation fail-closed: no Markdown arbitrary execution and no direct `done` without proof + review.

## Minimal verification after task creation

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
```
