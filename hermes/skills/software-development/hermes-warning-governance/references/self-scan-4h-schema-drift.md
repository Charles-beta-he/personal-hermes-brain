# 4H Self-Scan Schema Drift Closeout

Use when a cron job asks to run `~/.hermes/scripts/self-scan-4h.py`, inspect `~/.hermes/notes/engineering-cybernetics/self-scan-log.jsonl`, and refresh the engineering-cybernetics dashboard.

## Proven workflow

1. Run the actual scan, even if the prompt includes pre-run output:
   ```bash
   python3 ~/.hermes/scripts/self-scan-4h.py
   ```
2. Read the log and dashboard:
   ```bash
   tail -20 ~/.hermes/notes/engineering-cybernetics/self-scan-log.jsonl
   sed -n '1,80p' ~/.hermes/notes/engineering-cybernetics/evolution-dashboard.md
   ```
3. For root-cause analysis, inspect the scripts and source data:
   - `~/.hermes/scripts/self-scan-4h.py`
   - `~/.hermes/scripts/refresh-dashboard.py`
   - `~/.hermes/notes/engineering-cybernetics/health-history.jsonl`
   - `~/.hermes/skills/bayesian-agent/confidence-db.json`
   - `~/.hermes/skills/darwin-skill/results.tsv`
4. Compute an alias-aware summary; health history has used both `Vdot` and `V_dot`:
   ```python
   def get_vdot(record):
       return record.get("Vdot", record.get("V_dot", 0))
   ```
5. If a script reads only one alias, patch the canonical helper into every consumer that computes V̇ trends or dashboard display.
6. Verify with compile + live scan + dashboard readback:
   ```bash
   python3 -m py_compile ~/.hermes/scripts/self-scan-4h.py ~/.hermes/scripts/refresh-dashboard.py
   python3 ~/.hermes/scripts/self-scan-4h.py
   sed -n '1,40p' ~/.hermes/notes/engineering-cybernetics/evolution-dashboard.md
   ```
7. If files are tracked under `~/.hermes`, commit code fixes separately from volatile log/dashboard refreshes when possible:
   ```bash
   git -C ~/.hermes add scripts/self-scan-4h.py scripts/refresh-dashboard.py
   git -C ~/.hermes commit -m "fix: handle V_dot health schema alias"
   git -C ~/.hermes add notes/engineering-cybernetics/evolution-dashboard.md notes/engineering-cybernetics/self-scan-log.jsonl
   git -C ~/.hermes commit -m "chore: refresh self-scan health dashboard"
   ```
8. For unattended cron prompts with a delivery rule such as “respond `[SILENT]` if nothing new,” still complete the stateful closeout first: run the live scan, read the latest JSONL row, refresh/read back the dashboard, and commit the expected log/dashboard changes if they are tracked. Only after that, if `issue_count == 0` and all four dimensions are clean, return exactly `[SILENT]`. Do not send a chatty success report for a healthy scheduled run.

## Acceptance evidence

- Latest `self-scan-log.jsonl` row has `issue_count: 0`, or warnings/errors are explicitly reported.
- Recent V̇ values are computed alias-aware, not silently defaulted to zero.
- Dashboard timestamp updates and shows current health/skill ecosystem counts.
- Darwin coverage and D-grade counts are derived from `confidence-db.json`.
- Core script missing list is empty and `results.tsv` exists/writable.

## Pitfall

Do not treat a clean pre-run script output as sufficient. The cron task explicitly asks for a live scan, log read, warning/error analysis, and dashboard update. Run and verify the live path end-to-end.
