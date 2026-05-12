# Local Brain Theory Folder Content Governance

Use when an Obsidian/local-brain category folder exists but lacks real support notes.

Checklist:

1. Audit the folder and related folders before writing:
   ```bash
   find "$HOME/Documents/brain/<folder>" -name '*.md' -type f
   python3 ~/.hermes/scripts/brainctl.py --json search '<topic>' --limit 8
   ```
2. Minimum fill:
   - MOC/index note.
   - core concept notes with frontmatter and wikilinks.
   - bibliography/evidence-boundary note.
   - `30-tasks/` proof log with expiry.
   - optional `05-进化日志/` log for governance/evolution changes.
3. Search reliability:
   - Include English concept keywords in frontmatter even for Chinese notes.
   - Verify with both Chinese and English queries.
4. Final verification:
   ```bash
   python3 ~/.hermes/scripts/brainctl.py --json sync
   python3 ~/.hermes/scripts/brainctl.py --json reindex
   python3 ~/.hermes/scripts/brainctl.py --json search '<topic> foundation' --limit 8
   python3 ~/.hermes/scripts/brainctl.py --json search '<specific concept>' --limit 8
   ```
5. Write final observed sync/reindex/search outputs back into the proof log before committing.

For theory-to-Agent mapping details, load `theory-driven-evolution` and read `references/local-brain-theory-foundation-fill.md`.
