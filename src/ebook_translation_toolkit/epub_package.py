from __future__ import annotations

import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .epub_models import EpubBook
from .epub_navigation import render_nav_xhtml, render_toc_ncx
from .epub_notes import deterministic_path, sha256_of
from .render_epub import render_chapter_xhtml, render_titlepage_xhtml


CONTAINER_XML = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

MIMETYPE = "application/epub+zip"


@dataclass
class PackageResult:
    output_path: Path
    sha256: str
    size: int
    file_count: int
    manifest: list[str]


def _manifest_item(rel: str, media_type: str, *, properties: str | None = None, fallback: str | None = None) -> str:
    attrs = f"href=\"{rel}\" media-type=\"{media_type}\""
    if properties:
        attrs += f" properties=\"{properties}\""
    if fallback:
        attrs += f" fallback=\"{fallback}\""
    return f'<item {attrs}/>'


def build_package_opf(book: EpubBook) -> str:
    metadata = book.metadata
    items: list[str] = []
    spine: list[str] = []

    items.append(_manifest_item("nav.xhtml", "application/xhtml+xml", properties="nav"))
    items.append(_manifest_item("toc.ncx", "application/x-dtbncx+xml"))
    items.append(_manifest_item("styles/book.css", "text/css"))
    if metadata.cover_path:
        cover_rel = f"images/{Path(metadata.cover_path).name}"
        items.append(_manifest_item(cover_rel, _media_type_for(metadata.cover_path), properties="cover-image"))
    for image in book.images:
        items.append(_manifest_item(f"images/{image.file_name}", image.mime_type))
    items.append(_manifest_item("text/titlepage.xhtml", "application/xhtml+xml"))
    for chapter in book.chapters:
        items.append(_manifest_item(f"text/chapter-{chapter.number:02d}.xhtml", "application/xhtml+xml"))
        spine.append(f'<itemref idref="chapter-{chapter.number:02d}"/>')

    spine_xml = (
        '<spine toc="ncx">'
        + '<itemref idref="titlepage"/>'
        + "".join(spine)
        + "</spine>"
    )

    manifest = (
        '<manifest>'
        + f'<item id="titlepage" href="text/titlepage.xhtml" media-type="application/xhtml+xml"/>'
        + f'<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
        + f'<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
        + f'<item id="css" href="styles/book.css" media-type="text/css"/>'
        + (f'<item id="cover" href="images/{Path(metadata.cover_path).name}" media-type="{_media_type_for(metadata.cover_path)}" properties="cover-image"/>' if metadata.cover_path else "")
        + "".join(f'<item id="image-{i}" href="images/{img.file_name}" media-type="{img.mime_type}"/>' for i, img in enumerate(book.images))
        + "".join(f'<item id="chapter-{chapter.number:02d}" href="text/chapter-{chapter.number:02d}.xhtml" media-type="application/xhtml+xml"/>' for chapter in book.chapters)
        + "</manifest>"
    )

    package = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">'
        '<metadata>'
        f'<dc:identifier id="bookid">urn:uuid:{_escape(metadata.uuid)}</dc:identifier>'
        f'<dc:title>{_escape(metadata.title_zh)}</dc:title>'
        f'<meta refines="#bookid" property="title-type">main</meta>'
        f'<dc:title id="original-title">{_escape(metadata.title_en)}</dc:title>'
        f'<meta refines="#original-title" property="title-type">original</meta>'
        f'<dc:creator id="creator">{_escape(metadata.author)}</dc:creator>'
        f'<meta refines="#creator" property="role">aut</meta>'
        f'<dc:language>{_escape(metadata.language)}</dc:language>'
        f'<meta property="dcterms:modified">{_escape(metadata.modified)}</meta>'
        + (f'<meta name="cover" content="cover"/>' if metadata.cover_path else "")
        + (f'<dc:source>{_escape(metadata.source_pdf)}</dc:source>' if metadata.source_pdf else "")
        + "</metadata>"
        + manifest
        + spine_xml
        + "</package>"
    )
    return package


def _media_type_for(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }
    return mapping.get(suffix, "application/octet-stream")


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def write_epub(book: EpubBook, *, output_path: Path, css_path: Path) -> PackageResult:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    files: list[tuple[str, Path | str, int]] = []

    files.append(("mimetype", MIMETYPE, zipfile.ZIP_STORED))

    files.append(("META-INF/container.xml", CONTAINER_XML, zipfile.ZIP_DEFLATED))

    files.append(("EPUB/package.opf", build_package_opf(book), zipfile.ZIP_DEFLATED))
    files.append(("EPUB/nav.xhtml", render_nav_xhtml(book), zipfile.ZIP_DEFLATED))
    files.append(("EPUB/toc.ncx", render_toc_ncx(book), zipfile.ZIP_DEFLATED))
    files.append(("EPUB/styles/book.css", css_path.read_text(encoding="utf-8"), zipfile.ZIP_DEFLATED))

    if book.metadata.cover_path:
        cover_rel = f"EPUB/images/{Path(book.metadata.cover_path).name}"
        files.append((deterministic_path(cover_rel), Path(book.metadata.cover_path).read_bytes(), zipfile.ZIP_DEFLATED))

    for image in book.images:
        rel = deterministic_path(f"EPUB/images/{image.file_name}")
        files.append((rel, image.payload, zipfile.ZIP_DEFLATED))

    files.append(("EPUB/text/titlepage.xhtml", render_titlepage_xhtml(book), zipfile.ZIP_DEFLATED))
    for chapter in book.chapters:
        rel = deterministic_path(f"EPUB/text/chapter-{chapter.number:02d}.xhtml")
        files.append((rel, render_chapter_xhtml(chapter, book_title_zh=book.metadata.title_zh), zipfile.ZIP_DEFLATED))

    with zipfile.ZipFile(output_path, "w", allowZip64=True) as zf:
        for name, content, compress in files:
            data = content if isinstance(content, bytes) else content.encode("utf-8")
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = compress
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)

    sha = sha256_of(output_path)
    manifest = [name for name, _, _ in files]
    return PackageResult(
        output_path=output_path,
        sha256=sha,
        size=output_path.stat().st_size,
        file_count=len(files),
        manifest=manifest,
    )


def build_release_timestamp(book: EpubBook) -> str:
    if book.metadata.modified:
        return book.metadata.modified
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")