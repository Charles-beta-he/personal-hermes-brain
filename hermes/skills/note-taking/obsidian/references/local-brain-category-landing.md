# Local-brain category landing pattern

Use this when a task designs, modifies, or audits the Hermes/Obsidian local brain hierarchy.

## Principle

A hierarchy design note is not enough. Leave an auditable chain:

source/evidence -> multi-model/review provenance -> evolution note -> concrete category artifacts -> sync/reindex/search proof.

## Minimal category-fill checklist

1. Confirm current control plane:
   ```bash
   date '+%Y-%m-%d %H:%M:%S %Z'
   python3 ~/.hermes/scripts/brainctl.py --json status
   ```
2. Ensure the relevant layer folders exist in `~/Documents/brain`. For the 7-layer layout these are commonly:
   - `00-evidence/`
   - `10-atoms/`
   - `20-projects/<project>/`
   - `30-tasks/`
   - `40-skills/`
   - `50-prefs/`
   - `60-reviews/`
3. Write a category-fill/task ledger under `30-tasks/` with:
   - trigger / user requirement
   - files created per layer
   - proof checklist
   - `expires_at` so WIP does not become a future-session ghost
4. Put only stable, evidence-linked claims into `10-atoms/`. Multi-model agreement alone is not evidence.
5. Put multi-model provenance, dissent, timeouts, and certification caveats in `60-reviews/`.
6. If the task is a Hermes self-evolution event, write a formal note under `~/.hermes/notes/evolution/` and sync it so the mirror appears under `~/Documents/brain/99-hermes-notes/evolution/`.
7. Verify:
   ```bash
   python3 ~/.hermes/scripts/verify-evolution-event.py <evolution-note> <artifacts...> --repo=/Users/charles/.hermes/hermes-agent
   python3 ~/.hermes/scripts/brainctl.py --json sync
   python3 ~/.hermes/scripts/brainctl.py --json reindex
   python3 ~/.hermes/scripts/brainctl.py --json search '<distinctive category fill phrase>' --limit 8
   ```
8. If `~/.hermes` is a git repo, commit only the scoped artifacts. Sync may create mirrored files under `~/.hermes/notes/brain/...`; include them intentionally if they are part of the local-brain record.

## Pitfalls

- Do not treat a multi-model timeout/dissent artifact as ratified consensus. Record it as provenance with a caveat.
- Do not leave L3 task logs without expiry.
- Do not leave theory/category folders as empty architecture: if a folder exists, it needs a MOC plus concrete support notes, or a task/evolution log explaining why it is intentionally empty.
- Do not write secrets or credential material into brain notes. If a scanner flags only a negative policy sentence, reword it to avoid audit noise.
- `brainctl sync` returning 0 is insufficient: verify with `reindex` and `search`.
