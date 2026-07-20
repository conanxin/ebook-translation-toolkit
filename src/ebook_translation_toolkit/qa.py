from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from bs4 import BeautifulSoup

from .bilingual_terms import check_terms
from .footnotes import validate_footnotes
from .models import StructuredChapter
from .utils import atomic_write_text, markdown_visible_text, read_json, sha256_file, write_json


def _issue(level: str, code: str, message: str) -> dict[str, str]:
    return {"level": level, "code": code, "message": message}


def run_qa(
    chapter_json: Path,
    html_path: Path,
    markdown_path: Path,
    reports_dir: Path,
    *,
    obsidian_markdown: Path | None = None,
    project_root: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    chapter = StructuredChapter.from_dict(read_json(chapter_json))
    html = html_path.read_text(encoding="utf-8-sig")
    markdown = markdown_path.read_text(encoding="utf-8-sig")
    soup = BeautifulSoup(html, "html.parser")
    issues: list[dict[str, str]] = []
    for error in chapter.validate():
        issues.append(_issue("FAIL", "schema", error))
    cross_page = [block for block in chapter.blocks if block.source_pdf_page_end > block.source_pdf_page_start]
    for block in cross_page:
        if len(block.page_anchors) < block.source_pdf_page_end - block.source_pdf_page_start:
            issues.append(_issue("FAIL", "cross-page-split", f"missing internal page anchor in {block.block_id}"))
        translated_pages = [int(value) for value in re.findall(r"\[\[PAGE:(\d+)\|", block.translated_text)]
        source_pages = [anchor.pdf_page for anchor in block.page_anchors]
        if translated_pages != source_pages:
            issues.append(_issue("FAIL", "translated-page-anchors", f"translated page anchors differ in {block.block_id}: {translated_pages} != {source_pages}"))
    empty_translations = [block.block_id for block in chapter.blocks if not block.translated_text.strip()]
    if empty_translations:
        issues.append(_issue("FAIL", "empty-translation", ", ".join(empty_translations)))
    image_ids = [image.image_id for image in chapter.images]
    rendered_images = [element.get("data-image-id") for element in soup.select("figure[data-image-id]")]
    if sorted(image_ids) != sorted(rendered_images) or len(rendered_images) != len(set(rendered_images)):
        issues.append(_issue("FAIL", "images", "images are missing, duplicated, or not anchored after a block"))
    references = [ref for block in chapter.blocks for ref in block.footnote_refs]
    for error in validate_footnotes(chapter.footnotes, references):
        issues.append(_issue("FAIL", "footnotes", error))
    translated_references = [int(value) for block in chapter.blocks for value in re.findall(r"\[\[FN:(\d+)\]\]", block.translated_text)]
    if sorted(translated_references) != [note.number for note in chapter.footnotes]:
        issues.append(_issue("FAIL", "translated-footnotes", "translated footnote markers do not match definitions one-to-one"))
    if any(not note.translated_text.strip() for note in chapter.footnotes):
        issues.append(_issue("FAIL", "empty-footnote", "one or more footnotes are untranslated"))
    triggers = soup.select("button.footnote-trigger[aria-expanded][aria-controls]")
    templates = soup.select("template[id^='footnote-template-']")
    if len(triggers) != len(chapter.footnotes) or len(templates) != len(chapter.footnotes):
        issues.append(_issue("FAIL", "inline-footnotes", "not all footnotes have inline accessible bindings"))
    trigger_numbers = [int(element.get("data-footnote")) for element in triggers]
    if trigger_numbers != [note.number for note in chapter.footnotes]:
        issues.append(_issue("FAIL", "footnote-order", "HTML footnote buttons are not consecutive in reading order"))
    if "[[FN:" in html or "[[PAGE:" in html or "[[FN:" in markdown or "[[PAGE:" in markdown:
        issues.append(_issue("FAIL", "marker-leak", "structured inline markers leaked into rendered output"))
    if soup.select("ol.footnotes, .notes-page, section.footnotes"):
        issues.append(_issue("FAIL", "duplicate-footnotes", "HTML contains an appended footnote list"))
    if soup.find("em") or soup.find("i") or re.search(r"font-style\s*:\s*italic", html, re.I):
        issues.append(_issue("FAIL", "italic", "HTML contains visual italic markup or CSS"))
    resource_urls = [
        str(element.get(attribute))
        for element in soup.find_all(True)
        for attribute in ("src", "href")
        if element.get(attribute)
    ]
    if any(value.startswith(("http://", "https://", "//")) for value in resource_urls):
        issues.append(_issue("FAIL", "network", "HTML contains an external network dependency"))
    if re.search(r"(?:[A-Z]:\\|/tmp/|/mnt/[a-z]/)", html, re.I):
        issues.append(_issue("FAIL", "absolute-path", "HTML leaks an absolute or temporary path"))
    term_result = check_terms(chapter.blocks, chapter.terms)
    for term in term_result["missing"]:
        issues.append(_issue("WARN", "bilingual-term", f"first occurrence missing English: {term}"))
    html_ids = [element.get("data-block-id") for element in soup.select("[data-block-id]")]
    markdown_ids = re.findall(r"<!-- BLOCK_ID: ([^ ]+) -->", markdown)
    if html_ids != markdown_ids:
        issues.append(_issue("FAIL", "block-order", "HTML and Markdown block_id order differs"))
    markdown_refs = [int(value) for value in re.findall(r"\[\^(\d+)\](?!:)", markdown)]
    markdown_notes = [int(value) for value in re.findall(r"(?m)^\[\^(\d+)\]:", markdown)]
    expected_notes = [note.number for note in chapter.footnotes]
    if markdown_refs != expected_notes or markdown_notes != expected_notes:
        issues.append(_issue("FAIL", "markdown-footnotes", "Markdown footnote references or definitions are not consecutive and one-to-one"))
    try:
        frontmatter = markdown.split("---", 2)[1]
        yaml.safe_load(frontmatter)
    except Exception as exc:
        issues.append(_issue("FAIL", "yaml", f"invalid Markdown YAML: {exc}"))
    if obsidian_markdown and obsidian_markdown.exists():
        obsidian = obsidian_markdown.read_text(encoding="utf-8-sig")
        if markdown_visible_text(markdown) != markdown_visible_text(obsidian):
            issues.append(_issue("FAIL", "obsidian-text", "Markdown and Obsidian visible text differs"))
    if project_root:
        for image in chapter.images:
            path = project_root / image.path
            if not path.exists():
                issues.append(_issue("FAIL", "asset-missing", image.path))
            elif image.sha256 and sha256_file(path) != image.sha256.upper():
                issues.append(_issue("FAIL", "asset-hash", image.path))
    status = "FAIL" if any(item["level"] == "FAIL" for item in issues) else "WARN" if issues else "PASS"
    code = {"PASS": 0, "WARN": 1, "FAIL": 2}[status]
    result = {"status": status, "exit_code": code, "checks": {"blocks": len(chapter.blocks), "cross_page_blocks": len(cross_page), "images": len(chapter.images), "footnotes": len(chapter.footnotes), "terms": len(chapter.terms)}, "issues": issues}
    reports_dir.mkdir(parents=True, exist_ok=True)
    write_json(reports_dir / "qa.json", result)
    lines = ["# QA Report", "", f"STATUS: {status}", "", "## Counts", ""]
    lines.extend(f"- {key}: {value}" for key, value in result["checks"].items())
    lines.extend(["", "## Issues", ""])
    lines.extend(f"- [{item['level']}] {item['code']}: {item['message']}" for item in issues)
    if not issues:
        lines.append("- None")
    atomic_write_text(reports_dir / "QA_REPORT.md", "\n".join(lines) + "\n")
    return code, result
