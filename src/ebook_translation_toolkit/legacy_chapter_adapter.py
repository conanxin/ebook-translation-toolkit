from __future__ import annotations

"""Convert a project-approved legacy Markdown chapter into the internal
structured chapter shape used by the EPUB pipeline.

The first chapter of *The Cybernetic Brain* project only exists as a final
approved `chapter-XX-zh.md` plus `chapter-XX-source.md` and a `chapter-XX-blocks.json`.
This adapter rebuilds the same block ordering as the Markdown without
modifying or re-translating the approved text.
"""

import json
import re
from pathlib import Path
from typing import Any

from .epub_models import EpubChapter, EpubFootnote


_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_MARKDOWN_FN_RE = re.compile(r"^\[\^(\d+)\]:\s*(.*?)(?=^\[\^\d+\]:|\Z)", re.M | re.S)
_INLINE_FN_RE = re.compile(r"\[\^(\d+)\]")
_INLINE_FIG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)")
_INLINE_FIG_LABEL_RE = re.compile(r"图\s*(\d+(?:\.\d+)?)")
_PAGE_MARK_RE = re.compile(r"<!--\s*原书\s*PDF\s*第\s*(\d+)\s*页\s*/\s*印刷页码\s*([^\s]+)\s*-->")
_BLOCKQUOTE_RE = re.compile(r"(^|\n)>\s+", re.M)
_PARAGRAPH_BREAK_RE = re.compile(r"\n{2,}")


def _strip_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    metadata: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        metadata[key.strip()] = value.strip().strip('"')
    return metadata, text[match.end():]


def _split_blocks(text: str) -> list[dict[str, str]]:
    paragraphs = _PARAGRAPH_BREAK_RE.split(text)
    blocks: list[dict[str, str]] = []
    for raw in paragraphs:
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            blocks.append({"type": "chapter_title", "text": stripped[2:].strip()})
        elif stripped.startswith("## "):
            blocks.append({"type": "h2", "text": stripped[3:].strip()})
        elif stripped.startswith("> "):
            joined = "\n".join(re.sub(r"^>\s?", "", line) for line in stripped.splitlines())
            blocks.append({"type": "epigraph", "text": joined.strip()})
        else:
            blocks.append({"type": "body", "text": stripped})
    return blocks


def _convert_epigraph(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Return inline-rendered text plus collected (marker, label) for inline figures."""
    collected: list[tuple[str, str]] = []
    page_anchors: list[tuple[str, str]] = []

    # convert ![alt](src) to inline figure marker @@IMG:fig-1@@
    def img_sub(match: re.Match[str]) -> str:
        src = match.group("src").split("/")[-1]
        figure_label_match = re.search(r"图\s*(\d+(?:\.\d+)?)", match.group("alt") or "")
        label = figure_label_match.group(0) if figure_label_match else f"图 {match.group('alt') or src}"
        marker = f"fig-{len(collected) + 1}"
        collected.append((marker, label, match.group("alt") or ""))
        return f"\n@@IMG:{marker}@@\n"

    def page_sub(match: re.Match[str]) -> str:
        pdf_page = match.group(1)
        printed = match.group(2)
        page_anchors.append((pdf_page, printed))
        return f"\n@@PAGE:{pdf_page}|{printed}@@\n"

    text = _PAGE_MARK_RE.sub(page_sub, text)
    text = _INLINE_FIG_RE.sub(img_sub, text)
    return text, collected, page_anchors


def _normalize_text(text: str) -> str:
    text = text.replace("**", "")
    text = re.sub(r"^\s*\*\s*", "", text, flags=re.M)
    text = re.sub(r"\s*\*\s*$", "", text, flags=re.M)
    text = re.sub(r"\*", "", text)
    return text.strip()


def _convert_block(block: dict[str, str]) -> tuple[dict[str, Any], list[dict[str, Any]], list[tuple[str, str]]]:
    type_ = block["type"]
    text = _normalize_text(block["text"])
    if type_ == "chapter_title":
        return {"type": "chapter_title", "text": text}, [], []
    if type_ == "h2":
        return {"type": "subsection", "title_zh": text}, [], []
    if type_ == "epigraph":
        converted, figures, pages = _convert_epigraph(text)
        return {"type": "epigraph", "lines": converted.split("\n"), "raw_text": text}, figures, pages
    converted, figures, pages = _convert_epigraph(text)
    return {"type": "paragraph", "text": converted, "raw_text": text}, figures, pages


def parse_legacy_chapter_markdown(markdown_path: Path) -> dict[str, Any]:
    text = markdown_path.read_text(encoding="utf-8")
    metadata, body = _strip_front_matter(text)
    raw_blocks = _split_blocks(body)

    blocks: list[dict[str, Any]] = []
    figures: list[dict[str, Any]] = []
    page_anchors: list[tuple[str, str]] = []

    counter = 0
    for raw in raw_blocks:
        block, block_figures, block_pages = _convert_block(raw)
        counter += 1
        block["block_id"] = f"p{counter:03d}"
        if "raw_text" in block:
            del block["raw_text"]
        blocks.append(block)
        for marker, label, alt in block_figures:
            figures.append({"block_id": block["block_id"], "marker": marker, "label": label, "alt": alt})
        page_anchors.extend(block_pages)

    return {
        "metadata": metadata,
        "blocks": blocks,
        "figures": figures,
        "page_anchors": page_anchors,
    }


def load_legacy_footnotes(markdown_path: Path) -> list[dict[str, Any]]:
    text = markdown_path.read_text(encoding="utf-8")
    _, body = _strip_front_matter(text)
    footnotes = []
    for match in _MARKDOWN_FN_RE.finditer(body):
        footnotes.append({"number": int(match.group(1)), "text": match.group(2).strip()})
    return footnotes


def build_chapter_from_legacy(markdown_path: Path, chapter_number: int) -> EpubChapter:
    parsed = parse_legacy_chapter_markdown(markdown_path)
    metadata = parsed["metadata"]
    blocks: list[dict[str, Any]] = []
    footnotes: list[dict[str, Any]] = []

    title_zh = metadata.get("title", f"第 {chapter_number} 章")
    title_en = metadata.get("original_title", "")

    # Link figures to their nearest preceding block
    last_block_id: str | None = None
    for block in parsed["blocks"]:
        block["translated_text"] = block.get("text") or "\n".join(block.get("lines", []))
        blocks.append(block)
        last_block_id = block["block_id"]

    # Attach figures to nearest preceding block; image lookup will use figure_id
    figures_lookup: dict[str, dict[str, Any]] = {}
    for figure in parsed["figures"]:
        figures_lookup[figure["block_id"]] = {
            "figure_id": "",  # assigned later when emitted as an image
            "label": figure["label"],
            "alt": figure["alt"],
        }

    # Convert footnotes
    for raw_footnote in load_legacy_footnotes(markdown_path):
        block_id = _nearest_footnote_block(raw_footnote["number"], parsed["figures"], blocks)
        footnotes.append(
            EpubFootnote(
                chapter=chapter_number,
                number=raw_footnote["number"],
                block_id=block_id,
                text=raw_footnote["text"],
            ).__dict__
        )

    images: list[dict[str, Any]] = []
    figure_seq = 0
    for image_payload in figures_lookup.values():
        figure_seq += 1
        image_payload["figure_id"] = f"figure-{figure_seq:03d}"
        images.append(image_payload)

    return EpubChapter(
        number=chapter_number,
        title_zh=title_zh,
        title_en=title_en,
        blocks=blocks,
        footnotes=footnotes,
        images=images,
    )


def _nearest_footnote_block(number: int, figures: list[dict[str, Any]], blocks: list[dict[str, Any]]) -> str:
    return blocks[-1]["block_id"] if blocks else "p001"


def load_legacy_image_catalog(assets_dir: Path) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for path in sorted(assets_dir.glob("figure-*.jpg")) + sorted(assets_dir.glob("figure-*.jpeg")):
        catalog[path.name] = {"file_name": path.name, "path": path}
    return catalog


def hydrate_legacy_chapter_images(
    chapter: EpubChapter,
    *,
    assets_dir: Path,
    image_records: list[dict[str, Any]] | None = None,
) -> EpubChapter:
    catalog = load_legacy_image_catalog(assets_dir)
    if image_records:
        # align figures with the canonical image records (preserving order)
        ordered: list[dict[str, Any]] = []
        for idx, image in enumerate(image_records):
            file_name = image["file"]
            asset = catalog.get(file_name)
            if asset is None:
                continue
            ordered.append(
                {
                    "figure_id": f"figure-{idx + 1:03d}",
                    "label": image.get("caption_zh") or f"图 {idx + 1}",
                    "alt": image.get("caption_zh") or "",
                    "file_name": file_name,
                    "mime_type": "image/jpeg" if file_name.endswith((".jpg", ".jpeg")) else "image/png",
                    "path": str(asset["path"]),
                }
            )
        chapter.images = ordered
    return chapter