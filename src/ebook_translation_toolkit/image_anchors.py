from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import Block, ImageAsset, StructuredChapter
from .paragraph_reflow import normalize_semantic_blocks
from .source_markdown import render_source_markdown
from .utils import chapter_json_path, read_json, read_yaml, sha256_file, write_json


def find_caption_groups(blocks: list[Block], chapter_number: int) -> list[dict[str, Any]]:
    # PDF extraction can prepend short panel labels (for example ``A B``)
    # to a caption when the labels and caption share one coarse text block.
    # Treat those labels as part of the caption rather than losing the figure.
    pattern = re.compile(
        rf"^(?:(?:[A-Z]\s+){{1,6}})?Figure\s+{chapter_number}\.(\d+)\.\s*",
        re.IGNORECASE,
    )
    groups: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        match = pattern.match(block.source_text)
        if not match:
            continue
        ids = [block.block_id]
        parts = [block.source_text]
        cursor = index + 1
        while cursor < len(blocks):
            following = blocks[cursor]
            if following.source_pdf_page_start != block.source_pdf_page_start:
                break
            if pattern.match(following.source_text) or following.type in {"paragraph", "heading"}:
                break
            ids.append(following.block_id)
            parts.append(following.source_text)
            cursor += 1
        groups.append({
            "number": int(match.group(1)),
            "pdf_page": block.source_pdf_page_start,
            "block_ids": ids,
            "caption": " ".join(parts),
        })
    return groups


def extract_project_images(project_root: Path, chapter_number: int) -> StructuredChapter:
    import fitz

    source_path = chapter_json_path(project_root, chapter_number, "source")
    chapter = StructuredChapter.from_dict(read_json(source_path))
    captions = find_caption_groups(chapter.blocks, chapter_number)
    captions_by_page = {item["pdf_page"]: item for item in captions}
    pages: dict[int, dict[str, Any]] = {}
    for line in (project_root / "intermediate" / "ebook-pages.jsonl").read_text(encoding="utf-8").splitlines():
        page = json.loads(line)
        number = int(page["page_index"])
        if chapter.chapter["pdf_start"] <= number <= chapter.chapter["pdf_end"] and page.get("images"):
            pages[number] = page

    assets = project_root / "assets" / f"chapter-{chapter_number:02d}"
    assets.mkdir(parents=True, exist_ok=True)
    images: list[ImageAsset] = []
    document = fitz.open(project_root / "source" / "original.pdf")
    try:
        for pdf_page, page_data in sorted(pages.items()):
            metadata = page_data.get("images", [])
            caption = captions_by_page.get(pdf_page)
            if not caption:
                continue
            figure_number = int(caption["number"])
            image_id = f"figure-{figure_number:03d}"
            if len(metadata) == 1:
                raw = document.extract_image(int(metadata[0]["xref"]))
                extension = raw.get("ext", "png")
                output = assets / f"{image_id}.{extension}"
                output.write_bytes(raw["image"])
                bbox = list(metadata[0].get("bbox", []))
            else:
                boxes = [item.get("bbox", []) for item in metadata]
                boxes = [box for box in boxes if len(box) == 4]
                union = fitz.Rect(
                    min(box[0] for box in boxes), min(box[1] for box in boxes),
                    max(box[2] for box in boxes), max(box[3] for box in boxes),
                )
                pixmap = document[pdf_page - 1].get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72), clip=union, alpha=False)
                extension = "png"
                output = assets / f"{image_id}.png"
                pixmap.save(output)
                bbox = list(union)
            images.append(ImageAsset(
                image_id=image_id,
                path=f"assets/chapter-{chapter_number:02d}/{output.name}",
                pdf_page=pdf_page,
                bbox=bbox,
                caption_source=caption["caption"],
                sha256=sha256_file(output),
            ))
    finally:
        document.close()

    remove_ids = {block_id for item in captions for block_id in item["block_ids"]}
    multi_image_pages = {page for page, data in pages.items() if len(data.get("images", [])) > 1}
    for block in chapter.blocks:
        if block.source_pdf_page_start in multi_image_pages and block.type == "blockquote" and len(block.source_text.strip()) <= 8:
            remove_ids.add(block.block_id)
    chapter.blocks = normalize_semantic_blocks([block for block in chapter.blocks if block.block_id not in remove_ids])
    chapter.images = images
    anchor_images(chapter.blocks, chapter.images, read_yaml(project_root / ".ebook-translation" / "image-overrides.yaml"), project_root)
    for order, block in enumerate(chapter.blocks, 1):
        block.reading_order = order
    chapter.page_anchors = [anchor for block in chapter.blocks for anchor in block.page_anchors]
    write_json(source_path, chapter.to_dict())
    render_source_markdown(chapter, source_path.with_suffix(".md"))
    return chapter


def anchor_images(blocks: list[Block], images: list[ImageAsset], overrides: dict[str, Any] | None = None, root: Path | None = None) -> None:
    overrides = overrides or {}
    mapping = overrides.get("anchors", {}) or {}
    by_id = {block.block_id: block for block in blocks}
    for block in blocks:
        block.image_after = []
    seen: set[str] = set()
    for image in sorted(images, key=lambda item: (item.pdf_page, item.image_id)):
        if image.image_id in seen:
            raise ValueError(f"duplicate image: {image.image_id}")
        seen.add(image.image_id)
        target = mapping.get(image.image_id)
        if not target:
            top_of_page = len(image.bbox) == 4 and float(image.bbox[1]) < 200
            spanning = [block for block in blocks if block.source_pdf_page_start < image.pdf_page <= block.source_pdf_page_end and block.type == "paragraph"]
            eligible = spanning
            if not eligible and top_of_page:
                eligible = [block for block in blocks if block.source_pdf_page_end < image.pdf_page and block.type in {"paragraph", "heading"}]
            if not eligible:
                eligible = [block for block in blocks if block.source_pdf_page_end <= image.pdf_page and block.type in {"paragraph", "heading"}]
            target = eligible[-1].block_id if eligible else blocks[0].block_id
        if target not in by_id:
            raise ValueError(f"unknown image anchor block: {target}")
        image.after_block_id = target
        by_id[target].image_after.append(image.image_id)
        if root and image.path:
            candidate = root / image.path
            if candidate.exists():
                image.sha256 = sha256_file(candidate)


def anchor_project_images(project_root: Path, blocks: list[Block], images: list[ImageAsset]) -> None:
    overrides = read_yaml(project_root / ".ebook-translation" / "image-overrides.yaml")
    anchor_images(blocks, images, overrides, project_root)
