#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail() { echo "FAIL: $*" >&2; exit 1; }

# Path-based hard deny. Use git ls-files --others too so untracked leaks are caught.
# macOS ships bash 3.x, so avoid mapfile/readarray.
{ git ls-files -co --exclude-standard 2>/dev/null || find . -type f; } | sed 's#^./##' | sort -u | while IFS= read -r f; do
  case "$f" in
    hermes/memory/README.md) ;;
    hermes/memory/*|hermes/memories/*|*/MEMORY.md|*/USER.md) fail "raw Hermes memory path: $f" ;;
    *.env|*.env.*|*/.env|*/.env.*|*auth.json|auth/*|*/auth/*|*google_oauth*|*witness.key|*/*.key|*.key) fail "secret-like path: $f" ;;
    *sessions/*|*logs/*|*cache/*|*checkpoints/*|*tick-*/*|*state-snapshots/*|*rate_limits/*|*sandboxes/*|*tmp/*) fail "runtime path: $f" ;;
    *.sqlite|*.db|*.db-wal|*.db-shm|*.pid|*.lock|*.pyc|*/__pycache__/*) fail "derived/runtime file: $f" ;;
  esac
done

# Content scan implemented in Python for macOS portability and lower false positives.
python3 - <<'PY'
from pathlib import Path
import re, sys
root = Path('.')
patterns = [
    re.compile(r'(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{24,}'),
    re.compile(r'(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9_]{24,}'),
    re.compile(r'(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{24,}'),
    re.compile(r'(?<![A-Za-z0-9])AIza[0-9A-Za-z_-]{24,}'),
]
# Only flag actual token-looking values. Mere code/docs mentioning env var names is allowed.
# Path deny rules prevent committing .env/auth files; token regexes catch pasted keys.
key_re = re.compile(r'(?i)^\s*(ANTHROPIC_API_KEY|OPENAI_API_KEY|OPENROUTER_API_KEY|DEEPSEEK_API_KEY|XIAOMI_API_KEY|GITHUB_TOKEN|TELEGRAM_BOT_TOKEN)\s*=\s*(.+?)\s*$')
allowed_values = {'', '***', '<REDACTED>', '<SET_LOCALLY>', 'REDACTED', 'CHANGEME', 'TODO'}
skip_dirs = {'.git', '__pycache__'}
skip_files = {'validate_safe_tree.sh'}
violations = []
for p in root.rglob('*'):
    if not p.is_file():
        continue
    if any(part in skip_dirs for part in p.parts) or p.name in skip_files:
        continue
    try:
        data = p.read_bytes()
    except Exception:
        continue
    if b'\0' in data[:4096]:
        continue
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text = data.decode('utf-8', errors='ignore')
        except Exception:
            continue
    for i, line in enumerate(text.splitlines(), 1):
        for pat in patterns:
            if pat.search(line):
                violations.append(f'{p}:{i}: token-like secret')
        m = key_re.match(line)
        if m:
            val = m.group(2).strip().strip('"\'')
            # Flag only literal secret-looking env assignments. Allow code such as
            # KEY = os.environ.get(...), shell parameter expansion, and examples.
            if val in allowed_values or val.startswith('{{') or val.startswith('<'):
                continue
            if any(pat.search(val) for pat in patterns):
                violations.append(f'{p}:{i}: non-placeholder {m.group(1)}')
if violations:
    print('\n'.join(violations[:200]), file=sys.stderr)
    if len(violations) > 200:
        print(f'... {len(violations)-200} more', file=sys.stderr)
    sys.exit(1)
PY
[ $? -eq 0 ] || fail "secret-like content detected"

git diff --check
printf 'PASS: safe tree validation complete\n'
