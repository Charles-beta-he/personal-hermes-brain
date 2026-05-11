# Obsidian Skill Setup Notes

## Verified Environment
- macOS, Hermes Agent with local terminal backend
- No Obsidian desktop app required — this skill operates directly on the vault filesystem

## Key Lesson: Environment Variable Persistence

During setup we attempted to persist `OBSIDIAN_VAULT_PATH` to the global agent environment file.
That file is credential-protected and blocked agent writes.

Workaround: create `env.sh` inside the skill directory and `source` it per-session.
This approach is already provided in the SKILL.md instructions.

## Default Path Works Out-of-Box

If you do nothing, the skill defaults to `~/Documents/Obsidian Vault`.
This is sufficient for most users.

## Wikilinks Are Plain Text

`[[Note Name]]` syntax is just markdown content.
No graph-indexing or backlink resolution is performed by this skill.
Use grep to find references:

```bash
grep -rl "Note Name" "$VAULT" --include="*.md"
```

## Space in Pathnames

Always quote the VAULT variable:

```bash
VAULT="${OBSIDIAN_VAULT_PATH:-$HOME/Documents/Obsidian Vault}"
cat "$VAULT/My Note.md"
```
