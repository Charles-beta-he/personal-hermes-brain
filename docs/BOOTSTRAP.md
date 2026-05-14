# Bootstrap

Run:

```bash
bash bootstrap/verify.sh
bash bootstrap/sync_import.sh
```

This restores portable Hermes artifacts into `~/.hermes`:
- `hermes/project-profiles/*.json`
- selected `hermes/scripts/*`
- reviewed `hermes/skills/*`

Then selectively copy reviewed Markdown notes into a new `~/Documents/brain` vault if needed.
Credentials must be restored manually outside Git.
