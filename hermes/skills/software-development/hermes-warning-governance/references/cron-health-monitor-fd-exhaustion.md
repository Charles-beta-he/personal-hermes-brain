# Cron Health Monitor: Tool-Host FD Exhaustion

## Session signal

A scheduled Hermes agent health monitor task was requested end-to-end. The normal execution path could not start because the tool host itself failed to open files:

- `python3 ~/.hermes/scripts/agent-health-monitor.py` failed before process start with `OSError: [Errno 24] Too many open files`.
- Retrying with `ulimit -n 4096; ...` also failed before shell start, so raising the shell limit did not help.
- `read_file`, `write_file`, and `patch` against `~/.hermes/...` also failed with `[Errno 24]`.
- MCP filesystem still worked, but was restricted to `/Users/charles/Desktop/folder`, so it could not read/write `~/.hermes/notes/...`.

## Correct handling pattern

1. Stop retrying terminal/read_file/write_file after repeated `[Errno 24]`; the failure is in the tool host, not necessarily the command.
2. Use any still-working constrained channel to preserve an audit artifact, even if it is outside the required report path.
3. Mark the artifact as `blocked`, not successful.
4. Include:
   - commands attempted;
   - exact pre-start/tool-layer errors;
   - required report path attempted;
   - fallback report path actually written;
   - whether the file was verified (for example via MCP `get_file_info`).
5. Final response should keep `V`, `Vdot`, phase goal, and trend as null/blocked if health history and plan files could not be read.

## Example fallback path

`/Users/charles/Desktop/folder/hermes-agent-health-monitor-report-YYYY-MM-DD.blocked.md`

Use a date-specific name and verify file size/mtime when possible.
