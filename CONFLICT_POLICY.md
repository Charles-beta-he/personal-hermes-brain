# Conflict Policy

Primary machine is the writer by default. Secondary machines are consumers unless explicitly promoted.

Rules:

1. Brain Markdown conflicts are never silently overwritten. Import creates timestamped backups first.
2. Skills/scripts conflicts halt if local files differ and no backup was made.
3. `.env`, auth, OAuth, and machine-local config are never imported from Git.
4. Runtime state is excluded, so there is no runtime conflict resolution.
5. Before exporting from a secondary machine, pull/rebase and run validation first.
