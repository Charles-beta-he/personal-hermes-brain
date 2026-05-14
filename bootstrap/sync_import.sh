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
      rewrite_args+=("--map" "$2")
      shift 2
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 2
      ;;
  esac
done
mkdir -p "$target_home/project-profiles" "$target_home/scripts" "$target_home/skills"
if [ -d "$repo_root/hermes/project-profiles" ]; then
  rsync -a "$repo_root/hermes/project-profiles/" "$target_home/project-profiles/"
fi
if [ -d "$repo_root/hermes/scripts" ]; then
  rsync -a "$repo_root/hermes/scripts/" "$target_home/scripts/"
fi
if [ -d "$repo_root/hermes/skills" ]; then
  rsync -a "$repo_root/hermes/skills/" "$target_home/skills/"
fi
if [ ${#rewrite_args[@]} -gt 0 ]; then
  python3 "$repo_root/bootstrap/rewrite_project_profile_paths.py" --profiles-dir "$target_home/project-profiles" "${rewrite_args[@]}"
fi
printf 'imported portable Hermes artifacts into %s\n' "$target_home"
