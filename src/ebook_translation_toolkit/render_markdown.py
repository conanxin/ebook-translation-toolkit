from __future__ import annotations

from pathlib import Path
import re

import yaml

from .models import Block, StructuredChapter
from .page_anchors import markdown_anchor
from .utils import atomic_write_text, read_json


def _inline_markdown(block: Block) -> str:
    text = block.translated_text or block.source_text
    def escaped(value: str) -> str:
        return value.replace("*", "\\*").replace("_", "\\_")
    token_pattern = re.compile(r"\[\[(FN):(\d+)\]\]|\[\[(PAGE):(\d+)\|([^\]]*)\]\]")
    if token_pattern.search(text):
        cursor = 0
        parts: list[str] = []
        for match in token_pattern.finditer(text):
            parts.append(escaped(text[cursor:match.start()]))
            if match.group(1) == "FN":
                parts.append(f"[^{match.group(2)}]")
            else:
                parts.append(f"<!-- PDF_PAGE: {match.group(4)} | PRINTED_PAGE: {match.group(5)} | WITHIN_PARAGRAPH: {block.block_id} -->")
            cursor = match.end()
        parts.append(escaped(text[cursor:]))
        return "".join(parts)
    events: list[tuple[int, int, str]] = []
    for anchor in block.page_anchors:
        events.append((anchor.offset, 0, markdown_anchor(anchor)))
    for reference in block.footnote_refs:
        events.append((reference.offset, 1, f"[^{reference.number}]"))
    cursor = 0
    parts: list[str] = []
    for offset, _, marker in sorted(events, key=lambda value: (value[0], value[1])):
        offset = max(cursor, min(offset, len(text)))
        parts.extend([escaped(text[cursor:offset]), marker])
        cursor = offset
    parts.append(escaped(text[cursor:]))
    return "".join(parts)


def render_markdown(chapter: StructuredChapter, output: Path) -> str:
    metadata = {
        "title": chapter.chapter.get("title_zh", ""),
        "original_title": chapter.chapter.get("title_en", ""),
        "book_title": chapter.book.get("title", ""),
        "book_title_zh": chapter.book.get("title_zh", ""),
        "author": chapter.book.get("author", ""),
        "chapter": chapter.chapter.get("number", 1),
        "language": "zh-CN",
        "source_language": "en",
        "source_pdf_pages": f"{chapter.chapter.get('pdf_start', '')}-{chapter.chapter.get('pdf_end', '')}",
        "translation_status": "complete",
    }
    parts = ["---", yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).rstrip(), "---", ""]
    images = {image.image_id: image for image in chapter.images}
    for block in chapter.blocks:
        content = _inline_markdown(block)
        prefix = {"heading": "## ", "quote": "> ", "blockquote": "> ", "attribution": "— ", "caption": ""}.get(block.type, "")
        parts.extend([f"<!-- BLOCK_ID: {block.block_id} -->", prefix + content, ""])
        for image_id in block.image_after:
            image = images[image_id]
            source = Path(image.path)
            path = "../../" + source.as_posix().lstrip("./")
            parts.extend([f"![{image.caption_zh}]({path})", ""])
    for note in sorted(chapter.footnotes, key=lambda item: item.number):
        parts.append(f"[^{note.number}]: {note.translated_text or note.source_text}")
    content = "\n".join(parts).rstrip() + "\n"
    atomic_write_text(output, content)
    return content


def render_markdown_file(chapter_json: Path, output: Path) -> str:
    return render_markdown(StructuredChapter.from_dict(read_json(chapter_json)), output)
