from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .utils import atomic_write_text, load_project_config, read_json, write_json


CHAPTER_PATTERN = re.compile(r"^(?:chapter\s+)?(?:\d+|[ivxlcdm]+)\b", re.I)


def detect_chapter(project_root: Path, chapter_number: int) -> dict[str, Any]:
    config = load_project_config(project_root)
    structure_path = project_root / "intermediate" / "ebook-structure.json"
    structure = read_json(structure_path)
    chapter_cfg = config.get("chapter", {})
    use_manual = int(chapter_cfg.get("number", 0) or 0) == chapter_number
    manual_start = chapter_cfg.get("pdf_start") if use_manual else None
    manual_end = chapter_cfg.get("pdf_end") if use_manual else None
    candidates = [item for item in structure.get("toc", []) if CHAPTER_PATTERN.search(item.get("title", "").strip())]
    selected: dict[str, Any] | None = None
    selected_index = None
    if manual_start:
        selected = {"title": chapter_cfg.get("title_en", ""), "pdf_start": int(manual_start), "basis": "project.yaml override"}
    elif len(candidates) >= chapter_number:
        item = candidates[chapter_number - 1]
        selected_index = structure.get("toc", []).index(item)
        selected = {"title": item["title"], "pdf_start": int(item["pdf_page"]), "basis": "PDF bookmark and TOC"}
    else:
        pages_path = project_root / "intermediate" / "ebook-pages.jsonl"
        for line in pages_path.read_text(encoding="utf-8").splitlines():
            page = __import__("json").loads(line)
            for heading in page.get("headings", []):
                if CHAPTER_PATTERN.search(heading.get("text", "")):
                    if chapter_number == 1:
                        selected = {"title": heading["text"], "pdf_start": page["page_index"], "basis": "page heading size and text"}
                        break
            if selected:
                break
    if not selected:
        raise RuntimeError(f"unable to detect chapter {chapter_number}; set chapter.pdf_start/pdf_end in project.yaml")
    start = selected["pdf_start"]
    if manual_end:
        end = int(manual_end)
        next_start = end + 1
    else:
        # Part title pages and Notes are real structural boundaries even though
        # they are not numbered chapters.
        later = [int(item["pdf_page"]) for item in structure.get("toc", []) if int(item.get("pdf_page", 0)) > start]
        next_start = min(later) if later else int(structure["pdf_total_pages"]) + 1
        end = next_start - 1
    pages_path = project_root / "intermediate" / "ebook-pages.jsonl"
    printed: dict[int, str] = {}
    if pages_path.exists():
        for line in pages_path.read_text(encoding="utf-8").splitlines():
            page = __import__("json").loads(line)
            number = int(page["page_index"])
            if number in {start, end}:
                printed[number] = str(page.get("printed_page_number", ""))
    result = {
        "chapter_number": chapter_number,
        "title": selected["title"],
        "pdf_start": start,
        "pdf_end": end,
        "printed_start": printed.get(start, ""),
        "printed_end": printed.get(end, ""),
        "next_chapter_start": next_start,
        "basis": selected["basis"],
        "uncertainty": "none" if manual_start or candidates else "heading-only detection",
    }
    normalized = []
    for index, item in enumerate(candidates, 1):
        existing = next((value for value in structure.get("chapters", []) if value.get("chapter_number") == index), None)
        normalized.append(existing or {"chapter_number": index, "title": item["title"], "pdf_start": int(item["pdf_page"])})
    normalized = [item for item in normalized if item.get("chapter_number") != chapter_number] + [result]
    structure["chapters"] = sorted(normalized, key=lambda item: int(item["chapter_number"]))
    write_json(structure_path, structure)
    report = (
        f"# Chapter boundary report\n\n- Chapter: {chapter_number}\n- Title: {result['title']}\n"
        f"- PDF range: {start}-{end}\n- Printed range: {result['printed_start']}-{result['printed_end']}\n- Next structural section: {next_start}\n- Basis: {result['basis']}\n"
        f"- Uncertainty: {result['uncertainty']}\n"
    )
    report_dir = project_root / "reports" / f"chapter-{chapter_number:02d}"
    atomic_write_text(report_dir / "CHAPTER_BOUNDARY_REPORT.md", report)
    return result
