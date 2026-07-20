from __future__ import annotations

from pathlib import Path

from .models import Block, StructuredChapter
from .page_anchors import markdown_anchor
from .utils import atomic_write_text


def _inline_source(block: Block) -> str:
    events = [(anchor.offset, markdown_anchor(anchor)) for anchor in block.page_anchors]
    events += [(reference.offset, f"[^{reference.number}]") for reference in block.footnote_refs]
    cursor = 0
    parts: list[str] = []
    for offset, marker in sorted(events, key=lambda item: item[0]):
        offset = max(cursor, min(offset, len(block.source_text)))
        parts.extend([block.source_text[cursor:offset], marker])
        cursor = offset
    parts.append(block.source_text[cursor:])
    return "".join(parts)


def render_source_markdown(chapter: StructuredChapter, output: Path) -> str:
    parts = [f"# {chapter.chapter.get('number')}. {chapter.chapter.get('title_en')}", ""]
    for block in chapter.blocks:
        prefix = {"heading": "## ", "blockquote": "> ", "attribution": "— "}.get(block.type, "")
        parts.extend([f"<!-- BLOCK_ID: {block.block_id} -->", prefix + _inline_source(block), ""])
    for note in sorted(chapter.footnotes, key=lambda item: item.number):
        parts.append(f"[^{note.number}]: {note.source_text}")
    text = "\n".join(parts).rstrip() + "\n"
    atomic_write_text(output, text)
    return text
