from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .epub_models import EpubBook, EpubChapter
from .epub_notes import build_chapter_text_blocks, build_footnote_id, build_image_id, build_page_anchor_id


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _split_inline_segments(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"@@(FN|IMG|PAGE):([^@]+)@@")
    out: list[tuple[str, str]] = []
    pos = 0
    for match in pattern.finditer(text):
        if match.start() > pos:
            out.append(("text", text[pos:match.start()]))
        out.append((match.group(1).lower(), match.group(2)))
        pos = match.end()
    if pos < len(text):
        out.append(("text", text[pos:]))
    return out


def render_chapter_xhtml(chapter: EpubChapter, *, book_title_zh: str) -> str:
    lines: list[str] = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN">',
        "<head>",
        '<meta charset="utf-8"/>',
        f"<title>{_escape(book_title_zh)} — {_escape(chapter.title_zh)}</title>",
        '<link rel="stylesheet" type="text/css" href="../styles/book.css"/>',
        "</head>",
        "<body>",
        f'<section id="chapter-{chapter.number:02d}" epub:type="chapter" role="doc-chapter">',
        '<header class="chapter-header">',
        f'<p class="chapter-eyebrow">第 {_numeral(chapter.number)} 章</p>',
        f'<h1 class="chapter-title" id="chapter-title-{chapter.number:02d}">{_escape(chapter.title_zh)}</h1>',
        f'<p class="chapter-original-title">{_escape(chapter.title_en)}</p>',
        "</header>",
    ]

    image_lookup = {_image_id(image): image for image in chapter.images}
    fn_lookup: dict[tuple[str, int], dict[str, Any]] = {}
    fn_number_lookup: dict[int, dict[str, Any]] = {}
    for fn in chapter.footnotes:
        bid = _fn_block_id(fn)
        num = _fn_number(fn)
        if num is None:
            continue
        as_dict = _fn_as_dict(fn)
        if bid is not None:
            fn_lookup[(bid, num)] = as_dict
        # Fallback lookup keyed only by number so inline markers that
        # omit the block_id (e.g. ``@@FN:6@@``) still resolve.
        fn_number_lookup.setdefault(num, as_dict)

    pending_anchors: list[tuple[str, int]] = []

    def render_inline(text: str) -> str:
        buf: list[str] = []
        for kind, payload in _split_inline_segments(text):
            if kind == "text":
                buf.append(_escape(payload))
            elif kind == "fn":
                block_id, _, number = payload.partition("::")
                if not number:
                    # The renderer supports two inline marker shapes:
                    # ``@@FN:<n>@@`` (number only) and ``@@FN:<block>::<n>@@``
                    # (block-scoped).  When only the number is present we
                    # preserve it verbatim and rely on the footnote lookup
                    # to resolve the actual footnote text.
                    number = block_id
                    block_id = ""
                try:
                    n_int = int(number)
                except ValueError:
                    continue
                ref_id = f"ch{chapter.number:02d}-fnref-{n_int:03d}"
                href = build_footnote_id(chapter.number, n_int)
                buf.append(
                    f'<a href="#{_escape(href)}" id="{_escape(ref_id)}" '
                    f'epub:type="noteref" role="doc-noteref">{n_int}</a>'
                )
                pending_anchors.append((block_id, n_int))
            elif kind == "img":
                info = image_lookup.get(payload)
                if info is None:
                    continue
                anchor = build_image_id(chapter.number, payload)
                label = _image_label(info)
                buf.append(
                    f'<a href="#{_escape(anchor)}" epub:type="noteref">{_escape(label)}</a>'
                )
            elif kind == "page":
                anchor = build_page_anchor_id(chapter.number, payload, payload)
                buf.append(
                    f'<span id="{_escape(anchor)}" epub:type="pagebreak" role="doc-pagebreak" '
                    f'aria-label="原书第{_escape(payload)}页"></span>'
                )
        return "".join(buf)

    current_block_id: str | None = None
    block_open = False

    def flush_block() -> None:
        nonlocal block_open
        block_open = False
        if not pending_anchors:
            return
        for block_id, number in pending_anchors:
            fn = fn_lookup.get((block_id, number))
            if fn is None:
                fn = fn_number_lookup.get(number)
            if fn is None:
                continue
            fn_id = build_footnote_id(chapter.number, number)
            ref_id = f"ch{chapter.number:02d}-fnref-{number:03d}"
            fn_text = fn.get("text", "") if isinstance(fn, dict) else getattr(fn, "text", "")
            lines.append(
                f'<aside id="{_escape(fn_id)}" epub:type="footnote" role="doc-footnote">'
                f'<p class="footnote-text">{_escape(fn_text)} '
                f'<a href="#{_escape(ref_id)}" epub:type="backlink" role="doc-backlink" '
                f'class="footnote-backlink">返回</a></p>'
                f"</aside>"
            )
        pending_anchors.clear()

    for seg in build_chapter_text_blocks(chapter):
        seg_type = seg["type"]
        block_id = seg.get("block_id")
        if seg_type == "pagebreak":
            anchor = build_page_anchor_id(chapter.number, seg["pdf_page"], seg["printed_page"])
            lines.append(
                f'<span id="{_escape(anchor)}" epub:type="pagebreak" role="doc-pagebreak" '
                f'aria-label="原书第{_escape(seg["printed_page"])}页" '
                f'data-pdf-page="{_escape(seg["pdf_page"])}"></span>'
            )
            continue
        if seg_type == "subsection":
            lines.append(
                f'<h2 class="subsection">{_escape(seg["title_zh"])}</h2>'
            )
            continue
        if block_id != current_block_id and block_open:
            flush_block()
        current_block_id = block_id
        block_open = True

        if seg_type == "paragraph":
            rendered = render_inline(seg["text"])
            if rendered.strip():
                lines.append(f"<p>{rendered}</p>")
        elif seg_type == "epigraph":
            buf = "".join(f"<p>{_escape(line)}</p>" for line in seg["lines"])
            lines.append(f'<blockquote class="epigraph">{buf}</blockquote>')
        elif seg_type == "image_ref":
            info = image_lookup.get(seg["marker"])
            if info is None:
                continue
            anchor = build_image_id(chapter.number, seg["marker"])
            file_name = _image_file_name(info)
            mime_type = _image_mime_type(info)
            alt_text = _image_alt(info)
            caption = _image_caption(info)
            lines.append(
                f'<figure id="{_escape(anchor)}">'
                f'<img src="../images/{_escape(file_name)}" alt="{_escape(alt_text)}" '
                f'media-type="{_escape(mime_type)}"/>'
                f'<figcaption>{_escape(caption)}</figcaption>'
                f"</figure>"
            )

    if block_open:
        flush_block()

    lines.append("</section>")
    lines.append("</body>")
    lines.append("</html>")
    return "\n".join(lines) + "\n"


def render_titlepage_xhtml(book: EpubBook) -> str:
    metadata = book.metadata
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN">\n'
        "<head>\n"
        '<meta charset="utf-8"/>\n'
        f"<title>{_escape(metadata.title_zh)}</title>\n"
        '<link rel="stylesheet" type="text/css" href="../styles/book.css"/>\n'
        "</head>\n"
        "<body>\n"
        f'<section id="titlepage" epub:type="titlepage" role="doc-titlepage">\n'
        f'<h1 class="title-zh">{_escape(metadata.title_zh)}</h1>\n'
        f'<p class="title-en">{_escape(metadata.title_en)}</p>\n'
        f'<p class="author">{_escape(metadata.author)}</p>\n'
        f'<p class="edition">中文版</p>\n'
        "</section>\n"
        "</body>\n"
        "</html>\n"
    )


def _numeral(n: int) -> str:
    numerals = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    if 0 <= n < len(numerals):
        return numerals[n]
    return str(n)


def _image_id(image: Any) -> str:
    """Return the figure_id for an image, supporting dict or EpubImage."""
    if isinstance(image, dict):
        return image.get("figure_id") or image.get("image_id") or ""
    return getattr(image, "figure_id", "")


def _image_file_name(image: Any) -> str:
    if isinstance(image, dict):
        return image.get("file_name") or ""
    return getattr(image, "file_name", "")


def _image_mime_type(image: Any) -> str:
    if isinstance(image, dict):
        return image.get("mime_type") or "image/jpeg"
    return getattr(image, "mime_type", "image/jpeg")


def _image_alt(image: Any) -> str:
    if isinstance(image, dict):
        return image.get("alt_text_zh") or image.get("alt") or image.get("caption_zh") or ""
    return getattr(image, "alt_text_zh", "") or ""


def _image_caption(image: Any) -> str:
    if isinstance(image, dict):
        return image.get("caption_zh") or image.get("alt_text_zh") or image.get("alt") or ""
    return getattr(image, "caption_zh", "") or ""


def _image_label(image: Any) -> str:
    if isinstance(image, dict):
        return (
            image.get("figure_label")
            or image.get("label")
            or image.get("caption_zh")
            or image.get("alt_text_zh")
            or "图"
        )
    return getattr(image, "figure_label", None) or getattr(image, "caption_zh", "") or "图"


def _fn_block_id(fn: Any) -> str | None:
    if isinstance(fn, dict):
        return fn.get("block_id")
    return getattr(fn, "block_id", None)


def _fn_number(fn: Any) -> int | None:
    if isinstance(fn, dict):
        n = fn.get("number")
        try:
            return int(n) if n is not None else None
        except (TypeError, ValueError):
            return None
    n = getattr(fn, "number", None)
    try:
        return int(n) if n is not None else None
    except (TypeError, ValueError):
        return None


def _fn_as_dict(fn: Any) -> dict[str, Any]:
    if isinstance(fn, dict):
        return fn
    return {
        "number": getattr(fn, "number", None),
        "block_id": getattr(fn, "block_id", None),
        "text": getattr(fn, "text", ""),
    }