from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import StructuredChapter
from .utils import atomic_write_text


def marked_source_text(block) -> str:
    """Embed stable page and note tokens for translation-time preservation."""
    events: list[tuple[int, int, str]] = []
    for anchor in block.page_anchors:
        events.append((anchor.offset, 0, f"[[PAGE:{anchor.pdf_page}|{anchor.printed_page}]]"))
    for reference in block.footnote_refs:
        events.append((reference.offset, 1, f"[[FN:{reference.number}]]"))
    text = block.source_text
    for offset, _, token in sorted(events, key=lambda item: (item[0], item[1]), reverse=True):
        position = max(0, min(int(offset), len(text)))
        text = text[:position] + token + text[position:]
    return text


def build_translation_packets(chapter: StructuredChapter) -> list[dict]:
    packets: list[dict] = []
    for index, block in enumerate(chapter.blocks):
        previous = chapter.blocks[index - 1].source_text if index else ""
        following = chapter.blocks[index + 1].source_text if index + 1 < len(chapter.blocks) else ""
        packets.append({
            "block_id": block.block_id,
            "type": block.type,
            "source_text": block.source_text,
            "source_text_marked": marked_source_text(block),
            "previous_context": previous[-240:],
            "next_context": following[:240],
            "pdf_page_range": [block.source_pdf_page_start, block.source_pdf_page_end],
            "styles": block.styles,
            "footnote_refs": [item.number for item in block.footnote_refs],
            "image_after": block.image_after,
            "terms": [asdict(term) for term in chapter.terms if term.first_block_id == block.block_id],
        })
    return packets


def write_translation_packets(chapter: StructuredChapter, path: Path) -> None:
    packets = build_translation_packets(chapter)
    if path.suffix.lower() == ".json":
        content = json.dumps(packets, ensure_ascii=False, indent=2) + "\n"
    else:
        content = "\n".join(json.dumps(packet, ensure_ascii=False) for packet in packets) + "\n"
    atomic_write_text(path, content)
