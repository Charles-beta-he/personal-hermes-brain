# Local Brain Theory Foundation Fill

Use when the user notices a theory/category folder exists in the local brain but lacks actual conceptual support, e.g. `01-控制论基础/` is empty while downstream notes link to it.

## Workflow

1. Audit the target folder first:
   ```bash
   python3 ~/.hermes/scripts/brainctl.py --json status
   find "$HOME/Documents/brain/<folder>" -name '*.md' -type f
   find "$HOME/Documents/brain" -path '*<related-topic>*' -name '*.md' -type f
   ```
2. Distinguish three layers:
   - foundation folder: core concepts and MOC, e.g. `01-控制论基础/`.
   - related theory folders: wider/thematic notes, e.g. `03-系统理论/`.
   - Hermes logs/mirrors: historical implementation notes, e.g. `99-hermes-notes/engineering-cybernetics/`.
3. If the foundation folder is empty or hollow, create at minimum:
   - `00-<topic>索引.md` MOC/theory map.
   - 5-10 core concept notes with frontmatter, source boundary, theory→Agent mapping, and wikilinks.
   - `参考书目与证据.md` documenting source boundaries and what still needs stronger citations.
   - `30-tasks/YYYY-MM-DD-<topic>理论补齐日志.md` proof log with expiry.
   - optional `05-进化日志/YYYY-MM-DD-<topic>内容补齐.md` if this is local-brain governance/evolution.
4. Run verification and record outputs in the proof log:
   ```bash
   python3 ~/.hermes/scripts/brainctl.py --json sync
   python3 ~/.hermes/scripts/brainctl.py --json reindex
   python3 ~/.hermes/scripts/brainctl.py --json search '<topic> foundation' --limit 8
   python3 ~/.hermes/scripts/brainctl.py --json search '<specific core concept>' --limit 8
   ```
5. If `~/.hermes` is a git repo, commit only scoped artifacts:
   ```bash
   cd ~/.hermes
   git diff --check -- notes/brain/<folder> notes/brain/30-tasks/<log>.md logs/evolve.log notes/engineering-cybernetics/autonomous-evolution-log.jsonl
   git add -- <same scoped paths>
   git commit -m "docs(brain): fill <topic> foundations"
   ```

## Content shape for each theory note

Each foundation note should include:

- `type: theory-note` frontmatter.
- `concepts:` keywords in English if possible, improving FTS search.
- `primary_sources:` or `local_sources:`.
- Core concept in plain language.
- Formalism or control-loop sketch when useful.
- Theory → Agent/Hermes mapping table.
- Design implications and anti-patterns.
- Related wikilinks.

## Pitfalls

- Do not leave category folders as empty architecture. If a folder is introduced, populate it with at least a MOC and one concrete content card.
- Do not pretend reconstructed theory notes are exact source excerpts. Mark source boundaries and add a bibliography/evidence note.
- Chinese-only terms may not always search well in the current index. Include English concept keywords in frontmatter and verification queries, e.g. `cybernetics foundation`, `control loop stability feedback`, `requisite variety regulator`.
- After editing proof logs with final verification results, run sync/reindex again; the final indexed block count can change and should be updated before committing.
