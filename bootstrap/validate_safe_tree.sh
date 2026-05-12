#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -gt 0 ]; then
  root="$1"
else
  script_dir="$(cd "$(dirname "$0")" && pwd)"
  root="$(cd "$script_dir/.." && pwd)"
fi
cd "$root"
fail=0
bad_paths=$(find . \( -name '.env*' -o -name 'auth.json' -o -iname '*oauth*' -o -iname 'credentials.json' -o -iname 'secrets.json' -o -iname 'token*.json' -o -name 'MEMORY.md' -o -name 'USER.md' -o -name '*.sqlite' -o -name '*.db' -o -name '*.db-wal' -o -name '*.db-shm' -o -name '*.pem' -o -name '*.key' \) -print | sed 's#^./##' || true)
if [ -n "$bad_paths" ]; then
  echo "Forbidden paths:" >&2
  echo "$bad_paths" >&2
  fail=1
fi
if [ -d hermes/memory ]; then
  extra_memory=$(find hermes/memory -type f ! -name README.md -print | sed 's#^./##' || true)
  if [ -n "$extra_memory" ]; then
    echo "Forbidden raw memory files:" >&2
    echo "$extra_memory" >&2
    fail=1
  fi
fi
secret_hits=$(python3 - <<'PY'
from pathlib import Path
import re
root=Path('.')
patterns=[
 re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
 re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
 re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
 re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
 re.compile(r"AKIA[0-9A-Z]{16}"),
 re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"),
 re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*['\"]?(?!\[REDACTED\]|changeme|example|your_|<)[^\s'\"]{8,}"),
]
allow_suffix={'.md','.txt','.json','.yaml','.yml','.toml','.py','.sh','.bash','.example','.template'}
hits=[]
for p in root.rglob('*'):
 if not p.is_file() or '.git' in p.parts or p.suffix.lower() not in allow_suffix: continue
 try: txt=p.read_text(encoding='utf-8', errors='replace')
 except Exception: continue
 for pat in patterns:
  if pat.search(txt):
   hits.append(str(p))
   break
print('\n'.join(sorted(set(hits))))
PY
)
if [ -n "$secret_hits" ]; then
  echo "Secret-like content hits:" >&2
  echo "$secret_hits" >&2
  fail=1
fi
exit "$fail"
