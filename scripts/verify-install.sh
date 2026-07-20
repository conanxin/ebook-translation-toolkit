#!/usr/bin/env bash
set -euo pipefail
toolkit="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test -f /home/conanxin/.agents/skills/ebook-translation-zh/SKILL.md
python3 "$toolkit/skill/ebook-translation-zh/scripts/locate_toolkit.py"
test "$(grep -c '<!-- BEGIN EBOOK_TRANSLATION_ZH -->' /home/conanxin/.codex/AGENTS.md)" -eq 1
echo PASS
