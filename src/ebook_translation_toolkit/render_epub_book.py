"""High-level EPUB orchestration.

Builds the internal book model from project structured JSON (or legacy
Markdown), validates, and writes the EPUB package.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .epub_models import EpubBook, EpubBookMetadata, EpubChapter, EpubImage, EpubFootnote
from .epub_notes import _media_type_for as media_type_for  # noqa: F401  (re-export)
from .epub_package import PackageResult, write_epub
from .utils import load_project_config


PAGE_PATTERN = re.compile(r"\[\[\s*PAGE\s*:\s*(\d+)(?:\s*\|\s*(\d+))?\s*\]\]")
FN_PATTERN = re.compile(r"\[\s*FN\s*:\s*([^\]]+)\s*\]")


def _load_structured_chapter(path: Path) -> EpubChapter:
    data = json.loads(path.read_text(encoding="utf-8"))
    chapter_meta = data.get("chapter", {})
    number = int(chapter_meta.get("number") or path.stem.split("-")[-2])
    title_zh = chapter_meta.get("title_zh") or ""
    title_en = chapter_meta.get("title_en") or ""

    blocks = []
    for block in data.get("blocks", []):
        text = block.get("translated_text") or block.get("source_text") or ""
        if not text.strip():
            continue
        blocks.append(
            {
                "block_id": block.get("block_id"),
                "type": block.get("type", "paragraph"),
                "translated_text": text,
                "source_text": block.get("source_text", ""),
            }
        )

    footnotes = [
        {
            "number": int(footnote.get("number")),
            "block_id": footnote.get("block_id"),
            "text": footnote.get("translated_text") or footnote.get("source_text") or "",
        }
        for footnote in data.get("footnotes", [])
        if footnote.get("number") is not None
    ]

    images = []
    for index, image in enumerate(data.get("images", []), start=1):
        if not image.get("path"):
            continue
        project_root = path.parent.parent.parent
        candidate = project_root / image["path"]
        if not candidate.exists():
            candidate = project_root / "assets" / f"chapter-{number:02d}" / Path(image["path"]).name
        file_name = Path(image["path"]).name
        images.append(
            {
                "figure_id": image.get("image_id") or f"figure-{index:03d}",
                "file_name": file_name,
                "label": image.get("caption_zh") or image.get("caption_source") or f"图 {index}",
                "alt": image.get("caption_zh") or "",
                "caption_zh": image.get("caption_zh") or "",
                "mime_type": _media_type_for(file_name),
                "path": str(candidate),
                "sha256": _hash_file(candidate),
            }
        )

    page_anchors: list[dict[str, Any]] = []
    for block in blocks:
        for match in PAGE_PATTERN.finditer(block.get("translated_text", "")):
            pdf_page = match.group(1)
            printed = match.group(2) or pdf_page
            page_anchors.append(
                {
                    "printed_page": printed,
                    "pdf_page": pdf_page,
                    "block_id": block["block_id"],
                    "anchor_id": f"ch{number:02d}-page-{printed}",
                }
            )

    return EpubChapter(
        number=number,
        title_zh=title_zh,
        title_en=title_en,
        blocks=blocks,
        footnotes=footnotes,
        images=images,
        page_anchors=page_anchors,
        source_path=str(path),
    )


def _media_type_for(file_name: str) -> str:
    suffix = Path(file_name).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")


def _hash_file(path: Path) -> str:
    if not path.exists():
        return ""
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_epub_book(project_root: Path) -> EpubBook:
    config = load_project_config(project_root)
    book_config = config.get("book", {})
    epub_config = config.get("epub", {})
    title_zh = book_config.get("title_zh") or book_config.get("title") or ""
    title_en = book_config.get("title") or ""
    author = book_config.get("author") or ""

    identifier_path = project_root / epub_config.get("identifier_file", ".ebook-translation/epub-identifier.txt")
    identifier_path.parent.mkdir(parents=True, exist_ok=True)
    if identifier_path.exists():
        uuid_text = identifier_path.read_text(encoding="utf-8").strip()
        if not uuid_text:
            uuid_text = str(uuid.uuid4())
            identifier_path.write_text(uuid_text, encoding="utf-8")
    else:
        uuid_text = str(uuid.uuid4())
        identifier_path.write_text(uuid_text, encoding="utf-8")

    # Persist the modified timestamp alongside the UUID so that
    # consecutive builds produce byte-identical ZIP archives.
    modified_path = identifier_path.with_name("epub-modified.txt")
    if modified_path.exists():
        modified_text = modified_path.read_text(encoding="utf-8").strip()
        if not modified_text:
            modified_text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            modified_path.write_text(modified_text, encoding="utf-8")
    else:
        modified_text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        modified_path.write_text(modified_text, encoding="utf-8")

    metadata = EpubBookMetadata(
        title_zh=title_zh,
        title_en=title_en,
        author=author,
        language=book_config.get("language", {}).get("target", "zh-CN"),
        uuid=uuid_text,
        modified=modified_text,
        source_pdf=str(project_root / "source" / "original.pdf"),
        cover_path=str(project_root / epub_config.get("cover", "assets/epub/cover.jpg")),
    )

    book = EpubBook(metadata=metadata)

    chapters_root = project_root / "intermediate"
    chapter_paths: list[Path] = []
    for path in sorted((chapters_root / "chapters").glob("chapter-*-zh.json")):
        chapter_paths.append(path)

    for path in chapter_paths:
        chapter = _load_structured_chapter(path)
        if chapter.number == 1:
            continue
        book.chapters.append(chapter)

    # Legacy chapter 1 path
    chapter1_md = project_root / "output" / "markdown" / "chapter-01-zh.md"
    if chapter1_md.exists():
        legacy_chapter = _load_legacy_chapter1(project_root, chapter1_md)
        if legacy_chapter is not None:
            book.chapters.insert(0, legacy_chapter)

    book.chapters.sort(key=lambda ch: ch.number)
    for chapter in book.chapters:
        for image in chapter.images:
            book.images.append(_to_image(chapter.number, image))
    return book


def _to_image(chapter: int, image: dict[str, Any]) -> EpubImage:
    asset_path = Path(image.get("path", ""))
    if not asset_path.exists():
        raise FileNotFoundError(f"asset not found: {asset_path}")
    payload = asset_path.read_bytes()
    file_name = f"ch{chapter:02d}-{image['file_name']}"
    image_obj = EpubImage(
        chapter=chapter,
        figure_id=image["figure_id"],
        file_name=file_name,
        mime_type=image.get("mime_type") or _media_type_for(image["file_name"]),
        relative_path=f"images/{file_name}",
        alt_text_zh=image.get("alt") or image.get("caption_zh") or "",
        sha256=_hash_file(asset_path),
        caption_zh=image.get("caption_zh") or "",
    )
    image_obj.payload = payload  # type: ignore[attr-defined]
    return image_obj


def _load_legacy_chapter1(project_root: Path, markdown_path: Path) -> EpubChapter | None:
    from .legacy_chapter_adapter import parse_legacy_chapter_markdown, load_legacy_footnotes
    blocks_path = project_root / "intermediate" / "chapter-01-blocks.json"
    if not blocks_path.exists():
        return None
    blocks_data = json.loads(blocks_path.read_text(encoding="utf-8"))
    image_records: list[dict[str, Any]] = list(blocks_data.get("images", []) or [])
    assets_dir = project_root / "assets" / "chapter-01"
    chapter = _build_chapter1_from_approved(markdown_path, image_records=image_records, assets_dir=assets_dir)
    if chapter is None:
        return None
    if not chapter.title_en:
        chapter.title_en = "The Adaptive Brain"
    return chapter


def _build_chapter1_from_approved(
    markdown_path: Path,
    *,
    image_records: list[dict[str, Any]],
    assets_dir: Path,
) -> EpubChapter | None:
    from .legacy_chapter_adapter import parse_legacy_chapter_markdown, load_legacy_footnotes

    parsed = parse_legacy_chapter_markdown(markdown_path)
    metadata = parsed["metadata"]
    blocks: list[dict[str, Any]] = []
    footnotes: list[dict[str, Any]] = []

    title_zh = metadata.get("title", "第一章")
    title_en = metadata.get("original_title", "")

    for block in parsed["blocks"]:
        text = block.get("text") or "\n".join(block.get("lines", []))
        block["translated_text"] = text
        blocks.append(block)

    for raw in load_legacy_footnotes(markdown_path):
        target_block = blocks[-1]["block_id"] if blocks else "p001"
        footnotes.append(
            EpubFootnote(
                chapter=1,
                number=raw["number"],
                block_id=target_block,
                text=raw["text"],
            ).__dict__
        )

    images: list[dict[str, Any]] = []
    for idx, image in enumerate(image_records, start=1):
        file_name = Path(image.get("file", "")).name
        if not file_name:
            continue
        asset_path = assets_dir / file_name
        if not asset_path.exists():
            continue
        images.append(
            {
                "figure_id": image.get("image_id") or f"figure-{idx:03d}",
                "file_name": file_name,
                "label": image.get("caption_zh") or image.get("caption_en") or f"图 {idx}",
                "alt": image.get("caption_zh") or "",
                "caption_zh": image.get("caption_zh") or "",
                "mime_type": "image/jpeg" if file_name.endswith((".jpg", ".jpeg")) else "image/png",
                "path": str(asset_path),
            }
        )

    return EpubChapter(
        number=1,
        title_zh=title_zh,
        title_en=title_en,
        blocks=blocks,
        footnotes=footnotes,
        images=images,
    )


def write_book_epub(project_root: Path, *, output_path: Path | None = None, css_path: Path | None = None) -> PackageResult:
    config = load_project_config(project_root)
    epub_config = config.get("render", {}).get("epub", {})
    if not epub_config.get("enabled", False):
        raise RuntimeError("EPUB rendering is not enabled in project config")
    book = build_epub_book(project_root)
    output = Path(output_path or project_root / epub_config.get("output", "output/epub/the-cybernetic-brain-zh.epub"))
    css = Path(css_path or project_root.parent.parent / "ebook-translation-toolkit" / "templates" / "epub" / "book.css")
    if not css.exists():
        css = Path("/mnt/d/home/conanxin/workspace/ebook-translation-toolkit/templates/epub/book.css")
    return write_epub(book, output_path=output, css_path=css)