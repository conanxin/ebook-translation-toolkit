#!/usr/bin/env bash
set -euo pipefail
toolkit="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="$toolkit/skill/ebook-translation-zh"
target="/home/conanxin/.agents/skills/ebook-translation-zh"
mkdir -p "$(dirname "$target")"
mode=COPY
if [[ -L "$target" ]]; then
  ln -sfn "$source_dir" "$target"
  mode=LINK
elif [[ -d "$target" ]]; then
  cp -a "$source_dir/." "$target/"
else
  if ln -s "$source_dir" "$target" 2>/dev/null; then mode=LINK; else mkdir -p "$target"; cp -a "$source_dir/." "$target/"; fi
fi
mkdir -p /home/conanxin/.codex
python3 "$toolkit/scripts/update-global-route.py" /home/conanxin/.codex/AGENTS.md
printf 'WSL_SKILL_PATH=%s\nWSL_SKILL_INSTALL_MODE=%s\n' "$target" "$mode"
