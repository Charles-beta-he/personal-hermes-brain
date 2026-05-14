#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def apply_maps(value: Any, mappings: list[tuple[str, str]]) -> Any:
    if isinstance(value, dict):
        return {k: apply_maps(v, mappings) for k, v in value.items()}
    if isinstance(value, list):
        return [apply_maps(v, mappings) for v in value]
    if isinstance(value, str):
        for old, new in mappings:
            if value == old:
                return new
            prefix = old.rstrip('/') + '/'
            if value.startswith(prefix):
                return new.rstrip('/') + value[len(old.rstrip('/')):]
        return value
    return value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--profiles-dir', required=True)
    ap.add_argument('--map', action='append', default=[])
    args = ap.parse_args()
    mappings: list[tuple[str, str]] = []
    for item in args.map:
        if '=' not in item:
            raise SystemExit(f'invalid mapping: {item}')
        old, new = item.split('=', 1)
        mappings.append((old, new))
    profiles_dir = Path(args.profiles_dir).expanduser()
    changed_files: list[str] = []
    for path in sorted(profiles_dir.rglob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        rewritten = apply_maps(data, mappings)
        if rewritten != data:
            path.write_text(json.dumps(rewritten, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            changed_files.append(str(path))
    print(json.dumps({
        'schema': 'project_profile_path_rewrite_v1',
        'profiles_dir': str(profiles_dir),
        'mapping_count': len(mappings),
        'changed_files': changed_files,
        'changed_count': len(changed_files),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
