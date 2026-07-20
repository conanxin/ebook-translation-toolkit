#!/usr/bin/env bash
set -euo pipefail
toolkit="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="/home/conanxin/.agents/skills/ebook-translation-zh"
if [[ -L "$target" ]]; then echo 'LINK: already synchronized'; elif [[ -d "$target" ]]; then cp -a "$toolkit/skill/ebook-translation-zh/." "$target/"; echo 'COPY: synchronized'; else exec "$toolkit/scripts/install-user-skill.sh"; fi
