# Bulk rehabilitation playbook for Hermes skill libraries

Use this when a user asks for full-library cleanup rather than one-off skill surgery.

## Safe bulk edits first

These edits are high-confidence and can be applied across many skills with scripted normalization:

1. Frontmatter completeness
   - add `version: 1.0.0` when missing
   - add `author: Hermes Agent` when missing
   - add `license: MIT` when missing
   - ensure `metadata.hermes` exists

2. Metadata shape normalization
   - move top-level `tags` into `metadata.hermes.tags`
   - move top-level `related_skills` into `metadata.hermes.related_skills`
   - ensure `metadata.hermes.related_skills` exists even if it needs a conservative fallback

3. Heading normalization
   - `## Pitfalls` -> `## Common Pitfalls`
   - `## Verification` -> `## Verification Checklist`
   - normalize common `When to Use` capitalization variants

4. Parseability repair
   - if frontmatter YAML is invalid, repair it manually before running any bulk serializer
   - common failure mode: pseudo-YAML trigger lists written as comma-separated inline prose under block-list syntax

5. Conservative `related_skills` fallback
   - if a leaf skill has no obvious links, fall back to its category umbrella rather than inventing speculative peers
   - prefer empty only temporarily; finish the pass by removing empty `related_skills`

## Do NOT batch-rewrite blindly

Avoid scripted global rewrites for these until you review skill semantics:

1. `description` trigger text
   - `Use when ...` is a good target shape, but automatic rewrites often damage routing semantics
   - treat description changes as trigger-contract edits, not formatting cleanup

2. Primary mode / body structure
   - do not force Wrapper / Generator / Reviewer / Inversion / Pipeline labels by regex alone
   - infer the dominant mode per skill, then reshape deliberately

3. Section shell injection
   - adding `Overview` / `When to Use` / `Verification Checklist` everywhere can help, but only after checking the current body shape

## Recommended execution order

1. Inventory the whole library
2. Count parse/metadata/heading defects
3. Repair YAML parse failures manually
4. Run scripted safe normalization
5. Backfill empty `related_skills`
6. Re-run structural verification and report exact counts
7. Only then queue semantic rewrites like `description` modernization or umbrella slimming

## Verification pattern

After a bulk pass, verify with code rather than spot confidence:

- total `SKILL.md` count
- YAML parse failures = 0
- missing `version` / `author` / `license` = 0
- missing `metadata.hermes` = 0
- top-level-only `tags` / `related_skills` = 0
- empty `related_skills` = 0
- remaining heading variants = 0
- separately report how many descriptions still do not start with `Use when`

## Why this matters

A skill-library cleanup should improve the entry contract without destroying routing quality. Contract-layer normalization is scriptable. Trigger semantics are not.
