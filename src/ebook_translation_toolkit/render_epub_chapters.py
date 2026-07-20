from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .epub_models import EpubBook, EpubChapter
from .epub_notes import (
    build_chapter_text_blocks,
    build_footnote_id,
    build_footnote_ref_id,
    build_image_id,
    build_page_anchor_id,
)


class XhtmlWriter:
    def __init__(self) -> None:
        self._lines: list[str] = []

    def open_document(self, *, language: str = "zh-CN") -> None:
        self._lines.append('<?xml version="1.0" encoding="utf-8"?>')
        self._lines.append(
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops" '
            f'lang="{language}">'
        )
        self._lines.append("<head>")
        self._lines.append('<meta charset="utf-8"/>')

    def head_title(self, title: str) -> None:
        self._lines.append(f"<title>{_escape(title)}</title>")
        self._lines.append('<link rel="stylesheet" type="text/css" href="../styles/book.css"/>')

    def close_head_open_body(self) -> None:
        self._lines.append("</head>")
        self._lines.append("<body>")

    def close_document(self) -> str:
        self._lines.append("</body>")
        self._lines.append("</html>")
        return "\n".join(self._lines) + "\n"


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _split_inline_segments(text: str) -> list[tuple[str, str]]:
    """Split a paragraph string into ordered (kind, payload) segments.

    kinds: 'text', 'fn' (footnote ref marker), 'img' (image marker),
    'page' (inline pagebreak marker)
    """

    pattern = re.compile(r"@@(FN|IMG|PAGE):([^@]+)@@")
    segments: list[tuple[str, str]] = []
    pos = 0
    for match in pattern.finditer(text):
        if match.start() > pos:
            segments.append(("text", text[pos:match.start()]))
        kind = match.group(1)
        marker = match.group(2)
        segments.append((kind.lower(), marker))
        pos = match.end()
    if pos < len(text):
        segments.append(("text", text[pos:]))
    return segments


def _render_inline_segments(text: str, *, image_map: dict[str, dict[str, str]], footnote_ref_map: dict[str, dict[str, str]]) -> str:
    out: list[str] = []
    for kind, payload in _split_inline_segments(text):
        if kind == "text":
            out.append(_escape(payload))
        elif kind == "fn":
            info = footnote_ref_map.get(payload)
            if info is None:
                continue
            out.append(
                f'<a href="#{_escape(info["href"])}" id="{_escape(info["ref_id"])}" '
                f'epub:type="noteref" role="doc-noteref">{_escape(info["label"])}</a>'
            )
        elif kind == "img":
            info = image_map.get(payload)
            if info is None:
                continue
            out.append(
                f'<a href="#{_escape(info["image_anchor_id"])}" epub:type="noteref">{_escape(info["label"])}</a>'
            )
        elif kind == "page":
            out.append(
                f'<span id="{_escape(payload)}" epub:type="pagebreak" role="doc-pagebreak" '
                f'aria-label="{_escape(payload)}"></span>'
            )
    return "".join(out)


def render_chapter_xhtml(
    chapter: EpubChapter,
    *,
    book_title_zh: str,
    style_href: str = "../styles/book.css",
) -> str:
    writer = XhtmlWriter()
    writer.open_document()
    writer.head_title(f"{book_title_zh} — {chapter.title_zh}")
    writer.close_head_open_body()

    writer._lines.append(f'<section epub:type="chapter" id="chapter-{chapter.number:02d}" role="doc-chapter">')

    header_block = (
        f'<header class="chapter-header">'
        f'<p class="chapter-eyebrow">第 {_numeral(chapter.number)} 章</p>'
        f'<h1 class="chapter-title" id="chapter-title-{chapter.number:02d}">{_escape(chapter.title_zh)}</h1>'
        f'<p class="chapter-original-title">{_escape(chapter.title_en)}</p>'
        f'</header>'
    )
    writer._lines.append(header_block)

    image_lookup: dict[str, dict[str, str]] = {}
    for image in chapter.images:
        marker = image["figure_id"]
        image_lookup[marker] = {
            "label": f'图 {_escape(image["figure_label"])}',
            "image_anchor_id": build_image_id(chapter.number, marker),
        }

    footnote_ref_map: dict[str, dict[str, str]] = {}
    for fn in chapter.footnotes:
        marker = f"{fn['block_id']}::{fn['number']}"
        footnote_ref_map[marker] = {
            "href": build_footnote_id(chapter.number, fn["number"]),
            "ref_id": build_footnote_ref_id(chapter.number, fn["number"]),
            "label": str(fn["number"]),
        }

    segments = build_chapter_text_blocks(chapter)

    # Group segments by block so the footnote anchors land after the block
    block_buffer: list[dict[str, Any]] = []
    last_block_id: str | None = None

    def flush_block(buffer: list[dict[str, Any]], block_id: str) -> None:
        if not buffer:
            return
        paragraphs: list[str] = []
        for seg in buffer:
            if seg["type"] == "paragraph":
                paragraphs.append(_render_inline_segments(seg["text"], image_map=image_lookup, footnote_ref_map=footnote_ref_map))
            elif seg["type"] == "epigraph":
                paragraphs.append(
                    f'<blockquote class="epigraph">' + "".join(
                        f'<p>{_escape(line)}</p>' for line in seg["lines"]
                    ) + "</blockquote>"
                )
            elif seg["type"] == "image_ref":
                marker = seg["marker"]
                info = image_lookup.get(marker)
                if info:
                    paragraphs.append(
                        f'<a href="#{_escape(info["image_anchor_id"])}" epub:type="noteref">{_escape(info["label"])}</a>'
                    )
        if not paragraphs:
            return
        if len(paragraphs) == 1 and paragraphs[0].startswith("<blockquote"):
            writer._lines.append(paragraphs[0])
        else:
            body = "".join(f"<p>{p}</p>" for p in paragraphs)
            writer._lines.append(body)

    pending_footnote_anchors: list[dict[str, Any]] = []

    for seg in segments:
        seg_type = seg["type"]
        if seg_type == "pagebreak":
            writer._lines.append(
                f'<span id="{_escape(build_page_anchor_id(chapter.number, seg["pdf_page"], seg["printed_page"]))}" '
                f'epub:type="pagebreak" role="doc-pagebreak" '
                f'aria-label="原书第{_escape(seg["printed_page"])}页" '
                f'data-pdf-page="{_escape(seg["pdf_page"])}"></span>'
            )
            continue
        if seg_type == "subsection":
            writer._lines.append(
                f'<h2 id="subsection-{chapter.number:02d}-{len(writer._lines)}" class="subsection">{_escape(seg["title_zh"])}</h2>'
            )
            continue
        block_id = seg.get("block_id")
        if block_id != last_block_id and block_buffer:
            flush_block(block_buffer, last_block_id or "")
            block_buffer = []
        if seg_type in {"paragraph", "epigraph", "image_ref"}:
            block_buffer.append(seg)
            last_block_id = block_id
        elif seg_type == "footnote_ref":
            # Footnote references must be collected and anchored after the block they belong to.
            pending_footnote_anchors.append({"marker": seg["marker"], "block_id": block_id})

        # When the block_id changes, emit pending footnote anchors belonging to the previous block.
        if pending_footnote_anchors and seg.get("block_id") != last_block_id:
            for fn_ref in pending_footnote_anchors:
                info = footnote_ref_map.get(fn_ref["marker"])
                if info is None:
                    continue
                writer._lines.append(
                    f'<aside id="{_escape(info["href"])}" epub:type="footnote" role="doc-footnote">'
                    f'<p class="footnote-text">{_render_footnote_text(chapter, fn_ref["marker"])} '
                    f'<a href="#{_escape(info["ref_id"])}" epub:type="backlink" role="doc-backlink" '
                    f'class="footnote-backlink">返回</a></p>'
                    f"</aside>"
                )
            pending_footnote_anchors = []

    if block_buffer:
        flush_block(block_buffer, last_block_id or "")
    if pending_footnote_anchors:
        for fn_ref in pending_footnote_anchors:
            info = footnote_ref_map.get(fn_ref["marker"])
            if info is None:
                continue
            writer._lines.append(
                f'<aside id="{_escape(info["href"])}" epub:type="footnote" role="doc-footnote">'
                f'<p class="footnote-text">{_render_footnote_text(chapter, fn_ref["marker"])} '
                f'<a href="#{_escape(info["ref_id"])}" epub:type="backlink" role="doc-backlink" '
                f'class="footnote-backlink">返回</a></p>'
                f"</aside>"
            )

    writer._lines.append("</section>")

    return writer.close_document()


def render_footnote_anchor_block(chapter: EpubChapter, block_id: str, footnote_number: int) -> str:
    fn = next(
        (f for f in chapter.footnotes if f.get("block_id") == block_id and int(f.get("number", -1)) == footnote_number),
        None,
    )
    if fn is None:
        return ""
    target_id = build_footnote_id(chapter.number, footnote_number)
    return (
        f'<aside id="{_escape(target_id)}" epub:type="footnote" role="doc-footnote">'
        f'<p class="footnote-text">{_escape(fn.get("text", ""))} '
        f'<a href="#{_escape(build_footnote_ref_id(chapter.number, footnote_number))}" '
        f'epub:type="backlink" role="doc-backlink" class="footnote-backlink">返回</a></p>'
        f"</aside>"
    )


def _render_footnote_text(chapter: EpubChapter, marker: str) -> str:
    block_id, _, number = marker.partition("::")
    try:
        number_int = int(number)
    except ValueError:
        return ""
    for fn in chapter.footnotes:
        if fn.get("block_id") == block_id and int(fn.get("number", -1)) == number_int:
            return _escape(fn.get("text", ""))
    return ""


def _numeral(n: int) -> str:
    numerals = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    if 0 <= n < len(numerals):
        return numerals[n]
    return str(n)