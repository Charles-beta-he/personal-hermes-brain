---
type: setup-note
status: active
created: 2026-05-06T07:41:43Z
updated: 2026-05-06T07:41:43Z
app: Obsidian 1.12.7
canonical_vault: /Users/charles/Documents/brain
legacy_vault: /Users/charles/Documents/Obsidian Vault
---

# Obsidian Setup - Hermes Local Brain

## Installed

Obsidian.app was installed via Homebrew cask:

`brew install --cask obsidian`

Installed app:

`/Applications/Obsidian.app`

Version observed:

`1.12.7`

Official CLI symlink:

`/opt/homebrew/bin/obsidian -> /Applications/Obsidian.app/Contents/MacOS/obsidian-cli`

## Canonical vault

Canonical local brain vault:

`/Users/charles/Documents/brain`

Obsidian config was updated so this vault is registered/open in:

`/Users/charles/Library/Application Support/obsidian/obsidian.json`

Backup made:

`/Users/charles/Library/Application Support/obsidian/obsidian.json.backup-hermes`

Legacy vault remains registered but not open:

`/Users/charles/Documents/Obsidian Vault`

## CLI caveat

The official CLI binary is installed, and `brainctl.py --json status` detects it, but Obsidian still reports:

`Command line interface is not enabled. Please turn it on in Settings > General > Advanced.`

To fully enable runtime CLI commands, open Obsidian and toggle:

Settings -> General -> Advanced -> Command line interface

Until then, Hermes can still read/write/search the vault via markdown filesystem fallback and `brainctl.py`.

## Useful commands

Status:

`python3 ~/.hermes/scripts/brainctl.py --json status`

Search:

`python3 ~/.hermes/scripts/brainctl.py --json search "query" --limit 10`

Evidence search:

`python3 ~/.hermes/scripts/brainctl.py --json evidence "query" --limit 10`

Sync:

`python3 ~/.hermes/scripts/brainctl.py --json sync`

Reindex:

`python3 ~/.hermes/scripts/brainctl.py --json reindex`
