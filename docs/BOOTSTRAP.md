# Bootstrap

Run:

```bash
bash bootstrap/bootstrap_machine.sh
# or with cross-machine path rewrite
bash bootstrap/bootstrap_machine.sh --rewrite-prefix /old/checkout=/new/checkout
```

This performs one-click restore + validation:
- verifies the sanitized repo
- restores `hermes/project-profiles/*.json`
- restores selected `hermes/scripts/*`
- restores reviewed `hermes/skills/*`
- optionally rewrites project-profile path prefixes for the new machine
- runs reindex / selfcheck / boundary-check when prerequisites are available

Then selectively copy reviewed Markdown notes into a new `~/Documents/brain` vault if needed.
Credentials must be restored manually outside Git.
