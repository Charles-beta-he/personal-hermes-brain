#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
target_home="${HERMES_HOME:-$HOME/.hermes}"
rewrite_args=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --rewrite-prefix)
      [ "$#" -ge 2 ] || { echo "missing value for --rewrite-prefix" >&2; exit 2; }
      rewrite_args+=("--rewrite-prefix" "$2")
      shift 2
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 2
      ;;
  esac
done
bash "$repo_root/bootstrap/verify.sh"
bash "$repo_root/bootstrap/sync_import.sh" "${rewrite_args[@]}"
python3 - <<'PY'
import json
import os
import subprocess
from pathlib import Path

def run(cmd):
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, check=False)
        out = (p.stdout or '').strip()
        err = (p.stderr or '').strip()
        payload = None
        if out.startswith('{') or out.startswith('['):
            try:
                payload = json.loads(out)
            except Exception:
                payload = None
        return {"cmd": cmd, "returncode": p.returncode, "stdout": out[-2000:], "stderr": err[-2000:], "payload": payload}
    except Exception as exc:
        return {"cmd": cmd, "returncode": -1, "stdout": "", "stderr": str(exc), "payload": None}

target_home = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes'))).expanduser()
brain_vault = Path(os.environ.get('HERMES_BRAIN_VAULT', str(Path.home() / 'Documents' / 'brain'))).expanduser()
profiles_dir = target_home / 'project-profiles'
scripts_dir = target_home / 'scripts'
summary = {
    'schema': 'portable_restore_validation_v1',
    'target_home': str(target_home),
    'profiles_dir': str(profiles_dir),
    'checks': {},
}
profile_files = sorted(str(p.name) for p in profiles_dir.glob('*.json'))
summary['checks']['project_profiles_present'] = {'passed': bool(profile_files), 'count': len(profile_files), 'files': profile_files[:20]}
summary['checks']['hermes_profile_present'] = {'passed': (profiles_dir / 'hermes.json').exists()}
summary['checks']['brainctl_present'] = {'passed': (scripts_dir / 'brainctl.py').exists()}
summary['checks']['orchestrator_present'] = {'passed': (scripts_dir / 'brain_task_orchestrator.py').exists()}
if summary['checks']['brainctl_present']['passed'] and brain_vault.exists():
    summary['reindex'] = run(['python3', str(scripts_dir / 'brainctl.py'), '--json', 'reindex'])
else:
    summary['reindex'] = {'status': 'SKIP', 'reason': 'brainctl_or_vault_missing', 'brain_vault_exists': brain_vault.exists()}
if summary['checks']['orchestrator_present']['passed']:
    summary['selfcheck'] = run(['python3', str(scripts_dir / 'brain_task_orchestrator.py'), 'selfcheck', '--json'])
    summary['boundary_check'] = run(['python3', str(scripts_dir / 'brain_task_orchestrator.py'), 'boundary-check', '--json'])
else:
    summary['selfcheck'] = {'status': 'SKIP', 'reason': 'orchestrator_missing'}
    summary['boundary_check'] = {'status': 'SKIP', 'reason': 'orchestrator_missing'}
required = [
    summary['checks']['project_profiles_present']['passed'],
    summary['checks']['hermes_profile_present']['passed'],
    summary['checks']['brainctl_present']['passed'],
    summary['checks']['orchestrator_present']['passed'],
]
optional_ok = True
for key in ('reindex', 'selfcheck', 'boundary_check'):
    value = summary[key]
    if isinstance(value, dict) and value.get('status') == 'SKIP':
        continue
    if value.get('returncode') != 0:
        optional_ok = False
summary['status'] = 'PASS' if all(required) and optional_ok else 'FAIL'
print(json.dumps(summary, ensure_ascii=False, indent=2))
raise SystemExit(0 if summary['status'] == 'PASS' else 2)
PY
