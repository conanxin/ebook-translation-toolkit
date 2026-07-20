from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .utils import atomic_write_text, ensure_within, read_json, write_json


TITLE_ZH = {
    1: "适应性大脑",
    2: "本体论剧场",
    3: "格雷·沃尔特：从电休克到迷幻六十年代",
    4: "罗斯·阿什比：精神病学、合成大脑与控制论",
    5: "格雷戈里·贝特森与 R. D. 莱因：对称性、精神病学与六十年代",
    6: "斯塔福德·比尔：从控制论工厂到密宗瑜伽",
    7: "戈登·帕斯克：从化学计算机到适应性建筑",
    8: "另一种未来的速写",
}
STATUS_VALUES = {"NOT_STARTED", "EXTRACTED", "TRANSLATED", "RENDERED", "QA_PASS", "OBSIDIAN_SYNCED", "WARN", "FAIL"}
CHINESE_NUMERALS = {1: "第一章", 2: "第二章", 3: "第三章", 4: "第四章", 5: "第五章", 6: "第六章", 7: "第七章", 8: "第八章"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def detect_book_plan(project_root: Path) -> dict[str, Any]:
    structure = read_json(project_root / "intermediate" / "ebook-structure.json")
    toc = structure.get("toc", [])
    chapter_entries = []
    for toc_index, item in enumerate(toc):
        match = re.match(r"^\s*(\d+)\s*[.:]\s*(.+)$", item.get("title", ""))
        if match:
            chapter_entries.append((int(match.group(1)), match.group(2).strip(), int(item["pdf_page"]), toc_index))
    pages = {}
    pages_path = project_root / "intermediate" / "ebook-pages.jsonl"
    for line in pages_path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        pages[int(value["page_index"])] = value
    existing_path = project_root / "reports" / "BOOK_TRANSLATION_PROGRESS.json"
    existing = read_json(existing_path) if existing_path.exists() else {}
    existing_by_number = {int(item["number"]): item for item in existing.get("chapters", [])}
    chapters = []
    for number, title, start, toc_index in chapter_entries:
        later = [int(item["pdf_page"]) for item in toc[toc_index + 1:] if int(item.get("pdf_page", 0)) > start]
        end = (min(later) - 1) if later else int(structure["pdf_total_pages"])
        prior = existing_by_number.get(number, {})
        status = prior.get("status", "NOT_STARTED")
        qa = prior.get("qa", "")
        if number == 1 and not prior:
            status, qa = "OBSIDIAN_SYNCED", "PASS"
        chapter = {
            "number": number,
            "title_en": title,
            "title_zh": prior.get("title_zh", TITLE_ZH.get(number, title)),
            "pdf_start": start,
            "pdf_end": end,
            "printed_start": str(pages.get(start, {}).get("printed_page_number", "")),
            "printed_end": str(pages.get(end, {}).get("printed_page_number", "")),
            "status": status,
            "qa": qa,
            "html": prior.get("html", f"output/html/chapter-{number:02d}-zh.html"),
            "markdown": prior.get("markdown", f"output/markdown/chapter-{number:02d}-zh.md"),
            "obsidian": prior.get("obsidian", ""),
            "images": prior.get("images", 2 if number == 1 else 0),
            "footnotes": prior.get("footnotes", 7 if number == 1 else 0),
            "source_words": prior.get("source_words", 7728 if number == 1 else 0),
            "translated_characters": prior.get("translated_characters", 11366 if number == 1 else 0),
            "qa_report": prior.get("qa_report", "reports/TRANSLATION_QA.md" if number == 1 else f"reports/chapter-{number:02d}/QA_REPORT.md"),
            "updated_at": prior.get("updated_at", now()),
        }
        chapters.append(chapter)
    progress = {
        "book_title": structure.get("title", ""),
        "author": structure.get("author", ""),
        "pdf_total_pages": int(structure.get("pdf_total_pages", 0)),
        "chapters_detected": len(chapters),
        "non_body_sections_skipped": ["Acknowledgments", "Part divider pages", "Notes (assigned to chapters)", "References", "Index", "Copyright/front matter"],
        "chapters": chapters,
        "updated_at": now(),
    }
    save_progress(project_root, progress)
    return progress


def save_progress(project_root: Path, progress: dict[str, Any]) -> None:
    reports = project_root / "reports"
    progress["updated_at"] = now()
    write_json(reports / "BOOK_TRANSLATION_PROGRESS.json", progress)
    lines = ["# Book Translation Progress", "", f"- PDF pages: {progress['pdf_total_pages']}", f"- Chapters detected: {progress['chapters_detected']}", f"- Updated: {progress['updated_at']}", "", "| Chapter | English | 中文 | PDF | Printed | Status | QA | Images | Notes |", "|---:|---|---|---|---|---|---|---:|---:|"]
    for item in progress["chapters"]:
        lines.append(f"| {item['number']} | {item['title_en']} | {item['title_zh']} | {item['pdf_start']}-{item['pdf_end']} | {item['printed_start']}-{item['printed_end']} | {item['status']} | {item['qa']} | {item['images']} | {item['footnotes']} |")
    next_item = next((item for item in progress["chapters"] if not (item.get("status") == "OBSIDIAN_SYNCED" and item.get("qa") == "PASS")), None)
    lines.extend(["", "## Resume", ""])
    if next_item:
        toolkit = Path(r"D:\home\conanxin\workspace\ebook-translation-toolkit\scripts\ebook-translate.ps1")
        lines.append(f"`& '{toolkit}' prepare -ProjectRoot '{project_root}' -Chapter {next_item['number']}`")
    else:
        lines.append("All detected chapters are complete.")
    atomic_write_text(reports / "BOOK_TRANSLATION_PROGRESS.md", "\n".join(lines) + "\n")


def update_chapter(project_root: Path, chapter_number: int, status: str, **fields: Any) -> dict[str, Any]:
    if status not in STATUS_VALUES:
        raise ValueError(f"invalid status: {status}")
    path = project_root / "reports" / "BOOK_TRANSLATION_PROGRESS.json"
    progress = read_json(path) if path.exists() else detect_book_plan(project_root)
    chapter = next(item for item in progress["chapters"] if int(item["number"]) == chapter_number)
    chapter.update(fields)
    chapter["status"] = status
    chapter["updated_at"] = now()
    save_progress(project_root, progress)
    return chapter


def render_book_indices(project_root: Path, *, vault: Path | None = None, destination: Path | None = None) -> dict[str, str]:
    progress = read_json(project_root / "reports" / "BOOK_TRANSLATION_PROGRESS.json")
    html_rows = []
    markdown_lines = ["# 《控制论大脑》中文翻译目录", "", f"作者：{progress['author']}", "", "## 章节", ""]
    obsidian_lines = ["# 《控制论大脑》中文翻译目录", "", f"作者：{progress['author']}", "", "## 章节", ""]
    for item in progress["chapters"]:
        html_link = f"chapter-{item['number']:02d}-zh.html" if item["status"] in {"RENDERED", "QA_PASS", "OBSIDIAN_SYNCED", "WARN"} or item["number"] == 1 else ""
        link = f'<a href="{html_link}">阅读</a>' if html_link else "—"
        html_rows.append(f"<tr><td>{item['number']}</td><td>{html.escape(item['title_en'])}</td><td>{html.escape(item['title_zh'])}</td><td>{item['pdf_start']}-{item['pdf_end']}</td><td>{html.escape(item['status'])}</td><td>{item['images']}</td><td>{item['footnotes']}</td><td>{link}</td></tr>")
        markdown_link = f"[chapter-{item['number']:02d}-zh.md](chapter-{item['number']:02d}-zh.md)" if html_link else "尚未完成"
        markdown_lines.append(f"- {CHINESE_NUMERALS.get(item['number'], str(item['number']))}：{item['title_zh']}（{item['title_en']}）— {markdown_link} — {item['status']}")
        if html_link:
            obsidian_lines.append(f"- [[{CHINESE_NUMERALS.get(item['number'], str(item['number']))}-{item['title_zh']}]]")
    html_text = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>《控制论大脑》中文翻译</title><style>body{max-width:1100px;margin:2rem auto;padding:0 1rem;font-family:'Microsoft YaHei',sans-serif;color:#25211b;background:#f8f4eb}table{width:100%%;border-collapse:collapse;background:#fff}th,td{padding:.7rem;border:1px solid #cdbb9f;text-align:left}a{color:#195f83}@media(max-width:700px){table{display:block;overflow-x:auto}}</style></head><body><h1>《控制论大脑》中文翻译</h1><p>Andrew Pickering</p><p>进度：%s / %s 章已完成 QA</p><table><thead><tr><th>章</th><th>English</th><th>中文</th><th>PDF</th><th>状态</th><th>图片</th><th>注释</th><th>HTML</th></tr></thead><tbody>%s</tbody></table></body></html>""" % (sum(1 for item in progress["chapters"] if item["qa"] == "PASS"), progress["chapters_detected"], "".join(html_rows))
    html_path = project_root / "output" / "html" / "index.html"
    md_path = project_root / "output" / "markdown" / "README.md"
    atomic_write_text(html_path, html_text)
    atomic_write_text(md_path, "\n".join(markdown_lines) + "\n")
    result = {"html": str(html_path), "markdown": str(md_path)}
    if vault is not None and destination is not None:
        target_dir = ensure_within(vault, vault / destination)
        if ".obsidian" in {part.lower() for part in target_dir.parts}:
            raise ValueError("refusing to write index inside .obsidian")
        target = target_dir / "《控制论大脑》中文翻译目录.md"
        atomic_write_text(target, "\n".join(obsidian_lines) + "\n")
        result["obsidian"] = str(target)
    return result
