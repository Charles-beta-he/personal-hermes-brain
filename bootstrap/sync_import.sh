#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
target_home="${HERMES_HOME:-$HOME/.hermes}"
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
printf 'imported portable Hermes artifacts into %s\n' "$target_home"
