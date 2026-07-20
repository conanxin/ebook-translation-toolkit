#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

BEGIN = "<!-- BEGIN EBOOK_TRANSLATION_ZH -->"
END = "<!-- END EBOOK_TRANSLATION_ZH -->"
BLOCK = """<!-- BEGIN EBOOK_TRANSLATION_ZH -->
## Structured ebook translation

- For PDF ebook translation, chapter translation, layout-preserving Chinese editions, PDF-to-HTML, PDF-to-Markdown, or Obsidian book projects, use the user skill `ebook-translation-zh`.
- Reuse the canonical toolkit at `D:\\home\\conanxin\\workspace\\ebook-translation-toolkit`; do not invent a separate pipeline for each book.
- Logical paragraphs take precedence over PDF page boundaries.
- Run the toolkit QA before declaring a translated chapter complete.
<!-- END EBOOK_TRANSLATION_ZH -->"""


def update(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if pattern.search(text):
        text = pattern.sub(lambda _match: BLOCK, text, count=1)
        text = pattern.sub("", text)
    else:
        text = text.rstrip() + ("\n\n" if text.strip() else "") + BLOCK
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    update(Path(sys.argv[1]))
