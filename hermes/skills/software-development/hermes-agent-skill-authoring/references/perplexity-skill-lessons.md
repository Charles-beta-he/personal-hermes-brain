# Perplexity-inspired skill lessons for Hermes

Condensed lessons extracted from the Perplexity article on designing, refining, and maintaining agent skills, rewritten for Hermes authoring and review.

## Core ideas worth borrowing

1. **A skill is a directory, not just `SKILL.md`**
   - Keep the root body dense and short.
   - Put long domain notes, branchy procedures, and reference material into `references/`.
   - Put deterministic actions into `scripts/` and copyable outputs into `templates/`.

2. **Descriptions are routing triggers**
   - Write the description as a load condition.
   - Favor the user's phrasing over implementation phrasing.
   - Avoid writing a mini workflow summary in the description.

3. **Context has three budgets**
   - Index: everyone pays for `name` + `description` every session.
   - Load: the root body competes with every other loaded skill.
   - Runtime: support files are cheapest because they are conditional.

4. **README-style prose is often bad skill prose**
   - Do not spend root-body budget on command sequences the model already knows.
   - Spend it on judgment, branch conditions, anti-patterns, and failure modes.

5. **Gotchas are the highest-value maintenance surface**
   - Prefer append-mostly updates for repeated failure modes.
   - Add negative examples, pitfalls, and sharper verification before adding more general prose.

6. **Eval routing, not just output**
   - Positive prompts test recall.
   - Negative and neighbor-confusion prompts test precision.
   - If the description changes, rerun routing evals even if the workflow body does not.

## Suggested review prompts

Use these during skill review:

- Would the agent get this wrong without this sentence?
- Is this line telling the model something it already knows?
- Should this detail live in `references/` instead of the root body?
- Does the description tell me when to load this, or only what it does?
- What is the nearest neighboring skill this could accidentally steal routing from?
