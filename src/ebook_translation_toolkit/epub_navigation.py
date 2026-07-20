from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .epub_models import EpubBook, EpubChapter
from .epub_notes import build_footnote_id, build_page_anchor_id


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def render_nav_xhtml(book: EpubBook) -> str:
    metadata = book.metadata
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN">',
        "<head>",
        '<meta charset="utf-8"/>',
        f"<title>{_escape(metadata.title_zh)} — 目录</title>",
        '<link rel="stylesheet" type="text/css" href="../styles/book.css"/>',
        "</head>",
        "<body>",
        '<nav epub:type="toc" id="toc">',
        f"<h1>{_escape(metadata.title_zh)}</h1>",
        "<ol>",
        f'<li><a href="text/titlepage.xhtml">{_escape(metadata.title_zh)}</a></li>',
    ]
    for chapter in book.chapters:
        lines.append(
            f'<li><a href="text/chapter-{chapter.number:02d}.xhtml">{_escape(chapter.title_zh)}</a>'
            f'<span class="nav-original-title"> · {_escape(chapter.title_en)}</span></li>'
        )
        for subsection in chapter.subsections:
            sid = subsection.get("id") or f"chapter-{chapter.number:02d}-subsection-{subsection.get('index')}"
            lines.append(
                f'<li class="toc-subsection"><a href="text/chapter-{chapter.number:02d}.xhtml#{sid}">{_escape(subsection.get("title_zh", ""))}</a></li>'
            )
    lines.append("</ol>")
    lines.append("</nav>")

    lines.append('<nav epub:type="page-list" id="page-list">')
    lines.append("<h2>原书页码</h2>")
    lines.append("<ol>")
    seen_anchors: set[str] = set()
    for chapter in book.chapters:
        for anchor in chapter.page_anchors:
            anchor_id = anchor.get("anchor_id") or build_page_anchor_id(
                chapter.number, anchor.get("pdf_page", ""), anchor.get("printed_page", "")
            )
            if anchor_id in seen_anchors:
                continue
            seen_anchors.add(anchor_id)
            printed = anchor.get("printed_page", "")
            lines.append(
                f'<li><a href="text/chapter-{chapter.number:02d}.xhtml#{anchor_id}">'
                f'原书第{_escape(printed)}页</a></li>'
            )
    lines.append("</ol>")
    lines.append("</nav>")

    lines.append('<nav epub:type="landmarks" id="landmarks" hidden="hidden">')
    lines.append("<h2>地标</h2>")
    lines.append("<ol>")
    lines.append('<li><a epub:type="cover" href="text/titlepage.xhtml">封面</a></li>')
    lines.append('<li><a epub:type="toc" href="#toc">目录</a></li>')
    for chapter in book.chapters:
        lines.append(
            f'<li><a epub:type="bodymatter" href="text/chapter-{chapter.number:02d}.xhtml">'
            f'{_escape(chapter.title_zh)}</a></li>'
        )
    lines.append("</ol>")
    lines.append("</nav>")
    lines.append("</body>")
    lines.append("</html>")
    return "\n".join(lines) + "\n"


def render_toc_ncx(book: EpubBook) -> str:
    metadata = book.metadata
    nav_points: list[str] = []
    nav_points.append(
        f'<navPoint id="navpoint-titlepage" playOrder="1">'
        f'<navLabel><text>{_escape(metadata.title_zh)}</text></navLabel>'
        f'<content src="text/titlepage.xhtml"/>'
        f'</navPoint>'
    )
    for index, chapter in enumerate(book.chapters, start=2):
        nav_points.append(
            f'<navPoint id="navpoint-chapter-{chapter.number:02d}" playOrder="{index}">'
            f'<navLabel><text>{_escape(chapter.title_zh)}</text></navLabel>'
            f'<content src="text/chapter-{chapter.number:02d}.xhtml"/>'
            f'</navPoint>'
        )

    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
        "<head>\n"
        f'<meta name="dtb:uid" content="{_escape(metadata.uuid)}"/>\n'
        f'<meta name="dtb:depth" content="1"/>\n'
        f'<meta name="dtb:totalPageCount" content="0"/>\n'
        f'<meta name="dtb:maxPageNumber" content="0"/>\n'
        "</head>\n"
        f"<docTitle><text>{_escape(metadata.title_zh)}</text></docTitle>\n"
        "<navMap>\n"
        + "\n".join(nav_points) + "\n"
        "</navMap>\n"
        "</ncx>\n"
    )