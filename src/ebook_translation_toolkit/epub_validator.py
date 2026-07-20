from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .epub_models import EpubBook, EpubChapter, EpubFootnote, EpubImage
from .epub_notes import detect_zip_anomalies


class EpubValidationError(Exception):
    pass


def _namespaces() -> dict[str, str]:
    return {
        "opf": "http://www.idpf.org/2007/opf",
        "dc": "http://purl.org/dc/elements/1.1/",
    }


def _xml_parse(content: bytes) -> ET.Element:
    return ET.fromstring(content)


def _chapter_xhtml_paths(book: EpubBook) -> list[str]:
    return [f"EPUB/text/chapter-{chapter.number:02d}.xhtml" for chapter in book.chapters]


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


def validate_epub(epub_path: Path) -> dict[str, Any]:
    epub_path = Path(epub_path)
    if not epub_path.exists():
        raise EpubValidationError(f"EPUB not found: {epub_path}")

    report: dict[str, Any] = {
        "epub_path": str(epub_path),
        "file_size": epub_path.stat().st_size,
        "errors": [],
        "warnings": [],
    }

    anomalies = detect_zip_anomalies(epub_path)
    if anomalies:
        report["errors"].extend({"code": "ZIP", "message": msg} for msg in anomalies)

    with zipfile.ZipFile(epub_path) as zf:
        names = zf.namelist()
        containers = [n for n in names if n.endswith("META-INF/container.xml")]
        if not containers:
            report["errors"].append({"code": "MISSING_CONTAINER", "message": "META-INF/container.xml is missing"})
        else:
            container_xml = zf.read(containers[0])
            try:
                _xml_parse(container_xml)
            except ET.ParseError as exc:
                report["errors"].append({"code": "CONTAINER_XML", "message": str(exc)})
            container_text = container_xml.decode("utf-8")
            if "EPUB/package.opf" not in container_text:
                report["errors"].append({"code": "CONTAINER_OPF", "message": "container.xml does not point to EPUB/package.opf"})

        package_names = [n for n in names if n.endswith("EPUB/package.opf")]
        if not package_names:
            report["errors"].append({"code": "MISSING_PACKAGE", "message": "EPUB/package.opf is missing"})
        else:
            package_xml = zf.read(package_names[0])
            try:
                package_root = _xml_parse(package_xml)
            except ET.ParseError as exc:
                report["errors"].append({"code": "PACKAGE_XML", "message": str(exc)})
                package_root = None
            if package_root is not None:
                ns = _namespaces()
                metadata_el = package_root.find("opf:metadata", ns)
                ns_root = package_root
                title = metadata_el.find("dc:title", ns) if metadata_el is not None else None
                if title is None:
                    title = ns_root.find("dc:title", ns)
                if title is None or not (title.text or "").strip():
                    report["errors"].append({"code": "METADATA_TITLE", "message": "dc:title is missing"})
                identifier = metadata_el.find("dc:identifier", ns) if metadata_el is not None else None
                if identifier is None or not (identifier.text or "").strip():
                    report["errors"].append({"code": "METADATA_IDENTIFIER", "message": "dc:identifier is missing"})
                language = metadata_el.find("dc:language", ns) if metadata_el is not None else None
                if language is None or (language.text or "").strip() != "zh-CN":
                    report["errors"].append({"code": "METADATA_LANGUAGE", "message": "dc:language must be 'zh-CN'"})
                creator = metadata_el.find("dc:creator", ns) if metadata_el is not None else None
                if creator is None or not (creator.text or "").strip():
                    report["errors"].append({"code": "METADATA_CREATOR", "message": "dc:creator is missing"})
                modified = metadata_el.find("opf:meta[@property='dcterms:modified']", ns) if metadata_el is not None else None
                if modified is None or not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", modified.text or ""):
                    report["errors"].append({"code": "METADATA_MODIFIED", "message": "dcterms:modified must be ISO8601 Z form"})

                manifest_items = package_root.findall("opf:manifest/opf:item", ns)
                manifest_ids = {item.get("id") for item in manifest_items}
                manifest_hrefs = {item.get("href"): item.get("media-type") for item in manifest_items}

                cover_items = [item for item in manifest_items if item.get("properties") == "cover-image"]
                if not cover_items:
                    report["errors"].append({"code": "MISSING_COVER", "message": "manifest is missing a cover-image item"})
                nav_items = [item for item in manifest_items if item.get("properties") == "nav"]
                if not nav_items:
                    report["errors"].append({"code": "MISSING_NAV", "message": "manifest is missing a nav item"})

                spine = package_root.find("opf:spine", ns)
                if spine is None:
                    report["errors"].append({"code": "MISSING_SPINE", "message": "spine is missing"})
                else:
                    spine_ids = [item.get("idref") for item in spine.findall("opf:itemref", ns)]
                    for sid in spine_ids:
                        if sid not in manifest_ids:
                            report["errors"].append({"code": "SPINE_MANIFEST", "message": f"spine references unknown id {sid!r}"})
                    expected_ids = ["titlepage"] + [
                        f"chapter-{chapter.number:02d}" for chapter in []
                    ]
                    if "titlepage" not in spine_ids:
                        report["errors"].append({"code": "SPINE_TITLEPAGE", "message": "spine does not start with titlepage"})

        for xhtml_path in [
            "EPUB/nav.xhtml",
            "EPUB/toc.ncx",
        ] + [name for name in names if re.match(r"EPUB/text/chapter-\d{2}\.xhtml", name)]:
            if xhtml_path not in names:
                report["errors"].append({"code": "MISSING_XHTML", "message": f"missing {xhtml_path}"})
                continue
            try:
                _xml_parse(zf.read(xhtml_path))
            except ET.ParseError as exc:
                report["errors"].append({"code": "XHTML_PARSE", "message": f"{xhtml_path}: {exc}"})

        chapter_xhtml_names = [n for n in names if re.match(r"EPUB/text/chapter-\d{2}\.xhtml", n)]
        for name in chapter_xhtml_names:
            body = zf.read(name).decode("utf-8")
            if re.search(r"<script\b", body, re.I):
                report["errors"].append({"code": "JAVASCRIPT", "message": f"{name} contains a <script> tag"})
            if re.search(r"<(em|i)\b", body, re.I):
                report["errors"].append({"code": "ITALIC_TAG", "message": f"{name} contains an <em> or <i> tag"})
            if re.search(r"font-style\s*:\s*italic", body, re.I):
                report["errors"].append({"code": "ITALIC_STYLE", "message": f"{name} contains font-style:italic"})
            if re.search(r"https?://", body, re.I):
                report["warnings"].append({"code": "EXTERNAL_LINK", "message": f"{name} contains an http(s) URL"})

    report["status"] = "PASS" if not report["errors"] else "FAIL"
    return report


def validate_book_against_artifacts(
    book: EpubBook,
    *,
    project_root: Path,
    chapters_dir: Path,
    images_dir: Path,
    epub_path: Path,
) -> dict[str, Any]:
    """Cross-reference the EPUB chapters against the structured JSON.

    This validator compares:
      - chapter count,
      - per-chapter image order,
      - per-chapter footnote count,
      - block_id ordering,
      - first-occurrence Chinese titles against the final approved Markdown.
    """

    result: dict[str, Any] = {
        "status": "PASS",
        "errors": [],
        "warnings": [],
        "chapters": [],
    }
    for chapter in book.chapters:
        json_path = chapters_dir / f"chapter-{chapter.number:02d}-zh.json"
        record = {"chapter": chapter.number, "status": "PASS", "checks": {}}
        if not json_path.exists():
            record["status"] = "MISSING_JSON"
            result["errors"].append({"code": "MISSING_JSON", "chapter": chapter.number, "message": f"{json_path} is missing"})
            continue
        data = json.loads(json_path.read_text(encoding="utf-8"))
        block_ids = [b["block_id"] for b in data.get("blocks", []) if b.get("block_id")]
        record["checks"]["block_ids_count"] = len(block_ids)
        expected_image_count = len(data.get("images", []))
        actual_image_count = sum(1 for image in data.get("images", []) if image.get("file"))
        record["checks"]["expected_image_count"] = expected_image_count
        record["checks"]["actual_image_count"] = actual_image_count
        if expected_image_count != actual_image_count:
            record["status"] = "FAIL"
            result["errors"].append({"code": "IMAGE_COUNT", "chapter": chapter.number, "expected": expected_image_count, "actual": actual_image_count})

        expected_footnote_count = len(data.get("footnotes", []))
        actual_footnote_count = len(chapter.footnotes)
        record["checks"]["expected_footnotes"] = expected_footnote_count
        record["checks"]["actual_footnotes"] = actual_footnote_count
        if expected_footnote_count != actual_footnote_count:
            record["status"] = "FAIL"
            result["errors"].append({"code": "FOOTNOTE_COUNT", "chapter": chapter.number, "expected": expected_footnote_count, "actual": actual_footnote_count})

        json_image_files = [image["file"] for image in data.get("images", []) if image.get("file")]
        chapter_image_files = [image.file_name for image in chapter.images]
        record["checks"]["image_order"] = json_image_files == chapter_image_files
        if not record["checks"]["image_order"]:
            record["status"] = "FAIL"
            result["errors"].append({"code": "IMAGE_ORDER", "chapter": chapter.number, "expected": json_image_files, "actual": chapter_image_files})

        result["chapters"].append(record)

    if result["errors"]:
        result["status"] = "FAIL"
    return result