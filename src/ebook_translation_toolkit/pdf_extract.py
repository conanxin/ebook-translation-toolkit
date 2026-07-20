from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import fitz

from .utils import atomic_write_text, write_json


def _span_style(span: dict[str, Any]) -> dict[str, Any]:
    font = span.get("font", "")
    flags = int(span.get("flags", 0))
    return {
        "font_name": font,
        "font_size": round(float(span.get("size", 0)), 2),
        "bold": "bold" in font.lower() or bool(flags & 16),
        "italic": "italic" in font.lower() or "oblique" in font.lower() or bool(flags & 2),
    }


def page_has_reliable_text(page: fitz.Page) -> bool:
    text = page.get_text("text").strip()
    if len(text) < 40:
        return False
    printable = sum(character.isprintable() and character != "\ufffd" for character in text)
    alpha = sum(character.isalpha() for character in text)
    return printable / max(len(text), 1) > 0.97 and alpha >= 20


def extract_page(page: fitz.Page, page_index: int) -> dict[str, Any]:
    raw = page.get_text("dict", sort=True)
    blocks: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    headings: list[dict[str, Any]] = []
    order = 0
    for item in raw.get("blocks", []):
        if item.get("type") == 1:
            image = {
                "image_id": f"page-{page_index:04d}-image-{len(images)+1:03d}",
                "bbox": list(item.get("bbox", [])),
                "width": item.get("width", 0),
                "height": item.get("height", 0),
                "extension": item.get("ext", "png"),
            }
            images.append(image)
            continue
        lines = item.get("lines", [])
        spans = [span for line in lines for span in line.get("spans", [])]
        text = "\n".join("".join(span.get("text", "") for span in line.get("spans", [])) for line in lines).strip()
        if not text:
            continue
        order += 1
        largest = max(spans, key=lambda value: value.get("size", 0), default={})
        style = _span_style(largest)
        bbox = list(item.get("bbox", []))
        alignment = "left"
        if bbox and abs((bbox[0] + bbox[2]) / 2 - page.rect.width / 2) < page.rect.width * 0.08:
            alignment = "center"
        block_type = "paragraph"
        if style["font_size"] >= 16 or (style["bold"] and len(text) < 100):
            block_type = "heading"
            headings.append({"text": text, "bbox": bbox, "font_size": style["font_size"]})
        elif bbox and bbox[1] < page.rect.height * 0.08:
            block_type = "header"
        elif bbox and bbox[3] > page.rect.height * 0.92:
            block_type = "footer"
        blocks.append({
            "block_id": f"raw-{page_index:04d}-{order:03d}",
            "bbox": bbox,
            "text": text,
            "reading_order": order,
            **style,
            "alignment": alignment,
            "block_type": block_type,
        })
    return {
        "page_index": page_index,
        "printed_page_number": "",
        "width": page.rect.width,
        "height": page.rect.height,
        "text": "\n\n".join(block["text"] for block in blocks if block["block_type"] not in {"header", "footer"}),
        "blocks": blocks,
        "images": images,
        "tables": [],
        "headings": headings,
        "text_layer_reliable": page_has_reliable_text(page),
    }


def _ocr_missing_pages(pdf: Path, output: Path, pages: list[int]) -> None:
    executable = shutil.which("ocrmypdf")
    if not executable:
        raise RuntimeError("OCR required but ocrmypdf is unavailable")
    page_spec = ",".join(str(page) for page in pages)
    subprocess.run([executable, "--skip-text", "--pages", page_spec, str(pdf), str(output)], check=True)


def extract_pdf(pdf: Path, project_root: Path, *, ocr_missing: bool = False) -> dict[str, Any]:
    intermediate = project_root / "intermediate"
    source = project_root / "source"
    intermediate.mkdir(parents=True, exist_ok=True)
    source.mkdir(parents=True, exist_ok=True)
    with fitz.open(pdf) as document:
        unreliable = [index + 1 for index, page in enumerate(document) if not page_has_reliable_text(page)]
    searchable = source / "searchable.pdf"
    extraction_pdf = pdf
    if unreliable and ocr_missing:
        _ocr_missing_pages(pdf, searchable, unreliable)
        extraction_pdf = searchable
    elif not searchable.exists():
        shutil.copy2(pdf, searchable)

    pages: list[dict[str, Any]] = []
    with fitz.open(extraction_pdf) as document:
        toc = document.get_toc(simple=True)
        metadata = document.metadata or {}
        for index, page in enumerate(document, 1):
            page_data = extract_page(page, index)
            extracted_images: list[dict[str, Any]] = []
            for image_number, image_info in enumerate(page.get_images(full=True), 1):
                xref = int(image_info[0])
                data = document.extract_image(xref)
                extension = data.get("ext", "bin")
                relative = Path("intermediate") / "extracted-images" / f"page-{index:04d}-image-{image_number:03d}.{extension}"
                output = project_root / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                if not output.exists():
                    output.write_bytes(data["image"])
                rects = page.get_image_rects(xref)
                extracted_images.append({
                    "image_id": f"page-{index:04d}-image-{image_number:03d}",
                    "xref": xref,
                    "path": relative.as_posix(),
                    "bbox": list(rects[0]) if rects else [],
                    "width": data.get("width", 0),
                    "height": data.get("height", 0),
                    "extension": extension,
                })
            if extracted_images:
                page_data["images"] = extracted_images
            if hasattr(page, "find_tables"):
                try:
                    page_data["tables"] = [
                        {"bbox": list(table.bbox), "rows": table.extract()}
                        for table in page.find_tables().tables
                    ]
                except Exception:
                    page_data["tables"] = []
            pages.append(page_data)
    jsonl = "\n".join(json.dumps(page, ensure_ascii=False) for page in pages) + "\n"
    atomic_write_text(intermediate / "ebook-pages.jsonl", jsonl)
    markdown_parts: list[str] = []
    for page in pages:
        markdown_parts.append(f"<!-- PDF_PAGE: {page['page_index']} -->\n<!-- PRINTED_PAGE: {page['printed_page_number']} -->\n\n{page['text']}\n")
    atomic_write_text(intermediate / "ebook-fulltext.md", "\n".join(markdown_parts))
    structure = {
        "book": {"title": metadata.get("title", ""), "author": metadata.get("author", "")},
        "pdf_total_pages": len(pages),
        "toc": [{"level": level, "title": title, "pdf_page": page} for level, title, page in toc],
        "text_layer": {"reliable_pages": len(pages) - len(unreliable), "unreliable_pages": unreliable},
        "ocr_used": bool(unreliable and ocr_missing),
        "chapters": [],
    }
    write_json(intermediate / "ebook-structure.json", structure)
    return structure
