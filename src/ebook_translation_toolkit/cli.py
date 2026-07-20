from __future__ import annotations

import argparse
import json
import sys
import re
from pathlib import Path

from .bilingual_terms import check_terms, load_terminology, write_report
from .apply_translation import apply_translation_map
from .compile_translation import compile_translation_workfiles
from .book_progress import detect_book_plan, render_book_indices, update_chapter
from .chapter_detect import detect_chapter
from .endnotes import attach_project_endnotes
from .image_anchors import anchor_project_images, extract_project_images
from .models import StructuredChapter
from .page_anchors import build_page_anchors
from .paragraph_reflow import normalize_project
from .pdf_extract import extract_pdf
from .pre_render_gate import run_pre_render_gate
from .project import initialize_project
from .qa import run_qa
from .render_html import render_html
from .render_markdown import render_markdown
from .translation_packets import write_translation_packets
from .terminology_lock import check_terminology_lock
from .render_epub_book import write_book_epub
from .epub_validator import validate_epub
from .utils import chapter_data_dir, chapter_json_path, chapter_stem, load_project_config, read_json, write_json


def _root(args: argparse.Namespace) -> Path:
    return Path(args.project_root).resolve()


def _chapter_json(root: Path, chapter: int, suffix: str) -> Path:
    return chapter_json_path(root, chapter, suffix)


def _add_project(parser: argparse.ArgumentParser, *, chapter: bool = True) -> None:
    parser.add_argument("--project-root", required=True)
    if chapter:
        parser.add_argument("--chapter", type=int, default=1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ebook-translate")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--pdf", required=True)
    init.add_argument("--project-root", required=True)
    init.add_argument("--obsidian-vault")
    init.add_argument("--book-slug", required=True)
    init.add_argument("--chapter", type=int, default=1)
    init.add_argument("--language", default="zh-CN")
    extract = sub.add_parser("extract")
    _add_project(extract)
    extract.add_argument("--pdf")
    extract.add_argument("--ocr-missing", action="store_true")
    for name in ("detect-chapter", "detect", "normalize-paragraphs", "normalize", "extract-notes", "extract-images", "build-page-anchors", "anchor-images", "prepare-translation", "prepare", "compile-translation", "check-bilingual-terms", "render-html", "render-markdown", "render"):
        _add_project(sub.add_parser(name))
    qa_parser = sub.add_parser("qa")
    _add_project(qa_parser)
    qa_parser.add_argument("--obsidian-markdown")
    terminology_lock = sub.add_parser("check-terminology-lock")
    _add_project(terminology_lock, chapter=False)
    terminology_lock.add_argument("--obsidian-dir")
    render_epub = sub.add_parser("render-epub")
    _add_project(render_epub, chapter=False)
    render_epub.add_argument("--output")
    render_epub.add_argument("--css-path")
    validate_epub_cmd = sub.add_parser("validate-epub")
    validate_epub_cmd.add_argument("--epub", required=True)
    validate_epub_cmd.add_argument("--report")
    sync = sub.add_parser("sync-obsidian", aliases=["sync"])
    _add_project(sync)
    sync.add_argument("--vault")
    sync.add_argument("--destination")
    sync.add_argument("--copy-assets", action="store_true")
    sync.add_argument("--dry-run", action="store_true")
    sync.add_argument("--output-name")
    all_parser = sub.add_parser("all")
    _add_project(all_parser)
    all_parser.add_argument("--pdf")
    all_parser.add_argument("--ocr-missing", action="store_true")
    all_parser.add_argument("--sync", action="store_true")
    all_parser.add_argument("--book-slug")
    all_parser.add_argument("--obsidian-vault")
    all_parser.add_argument("--language", default="zh-CN")
    all_parser.add_argument("--vault")
    all_parser.add_argument("--destination")
    all_parser.add_argument("--copy-assets", action="store_true")
    all_parser.add_argument("--dry-run", action="store_true")
    plan_book = sub.add_parser("plan-book")
    _add_project(plan_book, chapter=False)
    render_index = sub.add_parser("render-index")
    _add_project(render_index, chapter=False)
    progress = sub.add_parser("progress")
    _add_project(progress)
    progress.add_argument("--status", required=True)
    progress.add_argument("--field", action="append", default=[])
    apply_translation = sub.add_parser("apply-translation")
    _add_project(apply_translation)
    apply_translation.add_argument("--translations", required=True)
    return parser


def _load(root: Path, chapter: int, suffix: str) -> StructuredChapter:
    return StructuredChapter.from_dict(read_json(_chapter_json(root, chapter, suffix)))


def _render(root: Path, number: int) -> None:
    run_pre_render_gate(root, number, require_pass=True)
    chapter = _load(root, number, "zh")
    stem = chapter_stem(number)
    render_html(chapter, root / "output" / "html" / f"{stem}-zh.html")
    render_markdown(chapter, root / "output" / "markdown" / f"{stem}-zh.md")


def _sync(args: argparse.Namespace) -> dict:
    from .obsidian_sync import chapter_output_name, sync_obsidian
    root = _root(args)
    config = load_project_config(root)
    vault = Path(args.vault or config.get("obsidian", {}).get("vault", ""))
    destination = Path(args.destination or config.get("obsidian", {}).get("destination", ""))
    markdown = root / "output" / "markdown" / f"{chapter_stem(args.chapter)}-zh.md"
    output_name = getattr(args, "output_name", None)
    if not output_name:
        chapter = _load(root, args.chapter, "zh")
        output_name = chapter_output_name(args.chapter, str(chapter.chapter.get("title_zh", "")).strip())
    return sync_obsidian(markdown, root, vault, destination, copy_assets=args.copy_assets, dry_run=args.dry_run, output_name=output_name)


def execute(args: argparse.Namespace) -> int:
    command = args.command
    if command == "init":
        config = initialize_project(Path(args.pdf), Path(args.project_root), Path(args.obsidian_vault) if args.obsidian_vault else None, args.book_slug, args.chapter, args.language)
        print(json.dumps(config, ensure_ascii=False, indent=2))
        return 0
    if command == "validate-epub":
        code = 0
        result = validate_epub(Path(args.epub))
        report_path = Path(args.report) if args.report else Path(args.epub).parent / "EPUB_VALIDATION.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result["status"] == "FAIL" else (1 if result["status"] == "WARN" else 0)
    root = _root(args)
    number = getattr(args, "chapter", 1)
    if command == "extract":
        pdf = Path(args.pdf) if args.pdf else root / "source" / "original.pdf"
        print(json.dumps(extract_pdf(pdf, root, ocr_missing=args.ocr_missing), ensure_ascii=False, indent=2))
    elif command == "plan-book":
        print(json.dumps(detect_book_plan(root), ensure_ascii=False, indent=2))
    elif command == "render-index":
        config = load_project_config(root)
        vault_value = config.get("obsidian", {}).get("vault", "")
        destination_value = config.get("obsidian", {}).get("destination", "")
        print(json.dumps(render_book_indices(root, vault=Path(vault_value) if vault_value else None, destination=Path(destination_value) if destination_value else None), ensure_ascii=False, indent=2))
    elif command == "progress":
        fields = {}
        for item in args.field:
            key, value = item.split("=", 1)
            fields[key] = int(value) if value.isdigit() else value
        print(json.dumps(update_chapter(root, number, args.status, **fields), ensure_ascii=False, indent=2))
    elif command == "apply-translation":
        chapter = apply_translation_map(root, number, Path(args.translations))
        print(f"applied {len(chapter.blocks)} blocks and {len(chapter.footnotes)} notes")
    elif command == "compile-translation":
        print(compile_translation_workfiles(root, number))
    elif command in {"detect-chapter", "detect"}:
        print(json.dumps(detect_chapter(root, number), ensure_ascii=False, indent=2))
    elif command in {"normalize-paragraphs", "normalize"}:
        chapter = normalize_project(root, number)
        print(f"normalized {len(chapter.blocks)} blocks")
    elif command == "extract-notes":
        chapter = attach_project_endnotes(root, number)
        print(f"attached {len(chapter.footnotes)} notes")
    elif command == "extract-images":
        chapter = extract_project_images(root, number)
        print(f"extracted {len(chapter.images)} images")
    elif command == "build-page-anchors":
        path = _chapter_json(root, number, "source")
        chapter = _load(root, number, "source")
        chapter.page_anchors = build_page_anchors(chapter.blocks)
        write_json(path, chapter.to_dict())
        print(f"built {len(chapter.page_anchors)} page anchors")
    elif command == "anchor-images":
        path = _chapter_json(root, number, "source")
        chapter = _load(root, number, "source")
        anchor_project_images(root, chapter.blocks, chapter.images)
        write_json(path, chapter.to_dict())
        print(f"anchored {len(chapter.images)} images")
    elif command in {"prepare-translation", "prepare"}:
        if command == "prepare":
            detect_chapter(root, number)
            normalize_project(root, number)
            attach_project_endnotes(root, number)
        chapter = _load(root, number, "source")
        terminology = load_terminology(root / ".ebook-translation" / "terminology.tsv")
        chapter.terms = terminology
        write_json(_chapter_json(root, number, "source"), chapter.to_dict())
        output = chapter_data_dir(root, number) / f"{chapter_stem(number)}-translation-packet.json"
        write_translation_packets(chapter, output)
        progress_path = root / "reports" / "BOOK_TRANSLATION_PROGRESS.json"
        if progress_path.exists():
            source_words = sum(len(re.findall(r"\b[\w’'-]+\b", block.source_text)) for block in chapter.blocks)
            source_words += sum(len(re.findall(r"\b[\w’'-]+\b", note.source_text)) for note in chapter.footnotes)
            update_chapter(root, number, "EXTRACTED", source_words=source_words, images=len(chapter.images), footnotes=len(chapter.footnotes))
        print(output)
    elif command == "check-bilingual-terms":
        chapter = _load(root, number, "zh")
        result = check_terms(chapter.blocks, chapter.terms)
        output = root / "reports" / "BILINGUAL_TERMS_REPORT.md"
        write_report(output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["missing"] or result["inconsistent"] else 0
    elif command == "render-html":
        run_pre_render_gate(root, number, require_pass=True)
        chapter = _load(root, number, "zh")
        render_html(chapter, root / "output" / "html" / f"{chapter_stem(number)}-zh.html")
    elif command == "render-markdown":
        run_pre_render_gate(root, number, require_pass=True)
        chapter = _load(root, number, "zh")
        render_markdown(chapter, root / "output" / "markdown" / f"{chapter_stem(number)}-zh.md")
    elif command == "render":
        _render(root, number)
    elif command in {"sync-obsidian", "sync"}:
        print(json.dumps(_sync(args), ensure_ascii=False, indent=2))
    elif command == "check-terminology-lock":
        code, result = check_terminology_lock(root, obsidian_dir=Path(args.obsidian_dir) if args.obsidian_dir else None)
        output = root / "reports" / "TERMINOLOGY_LOCK_QA.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    elif command == "render-epub":
        output = Path(args.output) if args.output else None
        css_path = Path(args.css_path) if args.css_path else None
        result = write_book_epub(root, output_path=output, css_path=css_path)
        report_path = root / "reports" / "EPUB_BUILD_REPORT.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_bytes(
            (json.dumps({
                "output": str(result.output_path),
                "size": result.size,
                "sha256": result.sha256,
                "file_count": result.file_count,
                "manifest": result.manifest,
            }, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )
        print(json.dumps({
            "output": str(result.output_path),
            "size": result.size,
            "sha256": result.sha256,
            "file_count": result.file_count,
        }, ensure_ascii=False, indent=2))
        return 0
    elif command == "qa":
        stem = chapter_stem(number)
        code, result = run_qa(_chapter_json(root, number, "zh"), root / "output" / "html" / f"{stem}-zh.html", root / "output" / "markdown" / f"{stem}-zh.md", root / "reports" / stem, obsidian_markdown=Path(args.obsidian_markdown) if args.obsidian_markdown else None, project_root=root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    elif command == "all":
        pdf = Path(args.pdf) if args.pdf else root / "source" / "original.pdf"
        if not (root / ".ebook-translation" / "project.yaml").exists():
            if not args.pdf or not args.book_slug:
                raise RuntimeError("all requires --pdf and --book-slug when initializing a new project")
            initialize_project(pdf, root, Path(args.obsidian_vault) if args.obsidian_vault else None, args.book_slug, number, args.language)
        extract_pdf(pdf, root, ocr_missing=args.ocr_missing)
        detect_chapter(root, number)
        chapter = normalize_project(root, number)
        chapter = attach_project_endnotes(root, number)
        chapter.page_anchors = build_page_anchors(chapter.blocks)
        write_json(_chapter_json(root, number, "source"), chapter.to_dict())
        write_translation_packets(chapter, chapter_data_dir(root, number) / f"{chapter_stem(number)}-translation-packet.json")
        if not _chapter_json(root, number, "zh").exists():
            print("Translation packets prepared. Codex must translate them and write chapter-XX-zh.json before render/qa/sync.")
            return 1
        run_pre_render_gate(root, number, require_pass=True)
        _render(root, number)
        stem = chapter_stem(number)
        code, result = run_qa(_chapter_json(root, number, "zh"), root / "output" / "html" / f"{stem}-zh.html", root / "output" / "markdown" / f"{stem}-zh.md", root / "reports" / stem, project_root=root)
        if args.sync and code < 2:
            _sync(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    return 0


def main(argv: list[str] | None = None) -> int:
    return execute(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
