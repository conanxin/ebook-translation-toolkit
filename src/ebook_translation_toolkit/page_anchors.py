from __future__ import annotations

from html import escape

from .models import Block, PageAnchor


def build_page_anchors(blocks: list[Block]) -> list[PageAnchor]:
    anchors: list[PageAnchor] = []
    for block in blocks:
        for anchor in block.page_anchors:
            anchor.within_block = block.block_id
            anchors.append(anchor)
    return anchors


def html_anchor(anchor: PageAnchor) -> str:
    printed = escape(str(anchor.printed_page), quote=True)
    label = f"PDF page {anchor.pdf_page}" + (f" / printed page {printed}" if printed else "")
    return (
        f'<span class="page-anchor" data-pdf-page="{anchor.pdf_page}" '
        f'data-printed-page="{printed}" data-within-paragraph="{escape(anchor.within_block)}" '
        f'title="{label}" aria-label="{label}"></span>'
    )


def markdown_anchor(anchor: PageAnchor) -> str:
    return f"<!-- PDF_PAGE: {anchor.pdf_page} | PRINTED_PAGE: {anchor.printed_page} | WITHIN_PARAGRAPH: {anchor.within_block} -->"


def insert_anchors(text: str, anchors: list[PageAnchor], renderer) -> str:
    result = text
    for anchor in sorted(anchors, key=lambda item: item.offset, reverse=True):
        offset = max(0, min(anchor.offset, len(result)))
        result = result[:offset] + renderer(anchor) + result[offset:]
    return result
