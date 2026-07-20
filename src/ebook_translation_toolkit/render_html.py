from __future__ import annotations

from collections import OrderedDict
from html import escape
from pathlib import Path
import re

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from .footnotes import html_template, html_trigger
from .models import Block, StructuredChapter
from .page_anchors import html_anchor
from .utils import atomic_write_text, read_json


TOOLKIT_ROOT = Path(__file__).resolve().parents[2]


def _inline_html(block: Block) -> str:
    text = block.translated_text or block.source_text
    token_pattern = re.compile(r"\[\[(FN):(\d+)\]\]|\[\[(PAGE):(\d+)\|([^\]]*)\]\]")
    if token_pattern.search(text):
        cursor = 0
        parts: list[str] = []
        for match in token_pattern.finditer(text):
            parts.append(escape(text[cursor:match.start()]))
            if match.group(1) == "FN":
                parts.append(html_trigger(int(match.group(2))))
            else:
                pdf_page, printed = int(match.group(4)), match.group(5)
                parts.append(f'<span class="page-anchor" data-pdf-page="{pdf_page}" data-printed-page="{escape(printed, quote=True)}" aria-label="PDF page {pdf_page}"></span>')
            cursor = match.end()
        parts.append(escape(text[cursor:]))
        return "".join(parts)
    events: list[tuple[int, int, str]] = []
    for anchor in block.page_anchors:
        events.append((anchor.offset, 0, html_anchor(anchor)))
    for reference in block.footnote_refs:
        events.append((reference.offset, 1, html_trigger(reference.number)))
    cursor = 0
    parts: list[str] = []
    for offset, _, markup in sorted(events, key=lambda value: (value[0], value[1])):
        offset = max(cursor, min(offset, len(text)))
        parts.append(escape(text[cursor:offset]))
        parts.append(markup)
        cursor = offset
    parts.append(escape(text[cursor:]))
    return "".join(parts)


def _block_html(block: Block, images: dict[str, object]) -> str:
    body = _inline_html(block)
    tag = {"heading": "h2", "quote": "blockquote", "blockquote": "blockquote", "attribution": "p", "caption": "p"}.get(block.type, "p")
    class_name = {"caption": "figure-caption", "attribution": "quote-attribution"}.get(block.type)
    class_name = f' class="{class_name}"' if class_name else ""
    result = [f'<{tag}{class_name} data-block-id="{escape(block.block_id)}">{body}</{tag}>']
    for image_id in block.image_after:
        image = images[image_id]
        path = "../../" + str(image.path).replace("\\", "/").lstrip("./")
        result.append(
            '<figure data-image-id="{}"><img src="{}" alt="{}" loading="lazy">{}</figure>'.format(
                escape(image.image_id), escape(path, quote=True), escape(image.caption_zh, quote=True),
                f"<figcaption>{escape(image.caption_zh)}</figcaption>" if image.caption_zh else "",
            )
        )
    return "\n".join(result)


def render_html(chapter: StructuredChapter, output: Path, *, template_root: Path | None = None) -> str:
    template_root = template_root or TOOLKIT_ROOT / "templates"
    environment = Environment(
        loader=FileSystemLoader(str(template_root / "html")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = environment.get_template("chapter.html.j2")
    css = (template_root / "html" / "chapter.css").read_text(encoding="utf-8")
    javascript = (template_root / "html" / "footnotes.js").read_text(encoding="utf-8")
    images = {image.image_id: image for image in chapter.images}
    pages: OrderedDict[int, list[Block]] = OrderedDict()
    for block in chapter.blocks:
        pages.setdefault(block.source_pdf_page_start or 1, []).append(block)
    page_items = []
    for page_number, blocks in pages.items():
        page_items.append({
            "number": page_number,
            "printed": blocks[0].printed_page_start,
            "content": Markup("\n".join(_block_html(block, images) for block in blocks)),
        })
    notes = Markup("\n".join(html_template(note) for note in sorted(chapter.footnotes, key=lambda item: item.number)))
    html = template.render(
        css=Markup(css),
        javascript=Markup(javascript),
        book=chapter.book,
        chapter=chapter.chapter,
        pages=page_items,
        footnote_templates=notes,
    )
    atomic_write_text(output, html)
    return html


def render_html_file(chapter_json: Path, output: Path) -> str:
    return render_html(StructuredChapter.from_dict(read_json(chapter_json)), output)
