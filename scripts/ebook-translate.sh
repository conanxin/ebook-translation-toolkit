#!/usr/bin/env bash
set -euo pipefail
toolkit="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$toolkit/src${PYTHONPATH:+:$PYTHONPATH}"
action="${1:?action required}"
shift
case "$action" in
  init|extract|detect|normalize|prepare|render|qa|sync|all|plan-book|render-index|progress|extract-notes|extract-images|anchor-images|build-page-anchors|compile-translation|apply-translation|check-bilingual-terms|render-epub|validate-epub|check-terminology-lock|test) exec python3 -m ebook_translation_toolkit "$action" "$@" ;;
  *) echo "Unsupported action: $action" >&2; exit 2 ;;
esac
