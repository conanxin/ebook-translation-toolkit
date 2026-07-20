from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import StructuredChapter
from .utils import chapter_json_path, chapter_stem, read_json, write_json


_PAGE_MARKER = re.compile(r"\[\[PAGE:(\d+)(?:\|[^\]]*)?\]\]")
_FOOTNOTE_MARKER = re.compile(r"\[\[FN:(\d+)\]\]")
_WORD = re.compile(r"\b[A-Za-z][A-Za-z'’\-]*\b")
_CJK = re.compile(r"[\u3400-\u9fff]")
_LONG_ENGLISH_RUN = re.compile(
    r"(?:\b[A-Za-z][A-Za-z'’\-]*\b(?:[\s,;:()–—-]+|$)){12,}"
)


def _source_words(text: str) -> int:
    return len(_WORD.findall(text or ""))


def _translated_characters(text: str) -> int:
    clean = _PAGE_MARKER.sub("", _FOOTNOTE_MARKER.sub("", text or ""))
    return len(_CJK.findall(clean))


def _reviewed_ids(project_root: Path, chapter_number: int) -> set[str]:
    path = project_root / "reports" / chapter_stem(chapter_number) / "RETRANSLATION_PROGRESS.json"
    if not path.exists():
        return set()
    try:
        progress = read_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return set()
    return {
        str(item.get("block_id"))
        for item in progress.get("blocks", [])
        if item.get("review_status") == "PASS" and item.get("translation_status") == "PASS"
    }


def evaluate_pre_render_gate(
    source: StructuredChapter,
    translated: StructuredChapter,
    *,
    reviewed_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Evaluate canonical source/translation JSON before any formal render.

    The gate intentionally reads only canonical ``chapter-XX-source.json`` and
    ``chapter-XX-zh.json`` data supplied by its caller. Rejected drafts and
    ``.tmp`` caches are outside this data path and can never satisfy the gate.
    """

    source_ids = [block.block_id for block in source.blocks]
    translated_ids = [block.block_id for block in translated.blocks]
    source_set = set(source_ids)
    translated_set = set(translated_ids)
    duplicates = sorted({block_id for block_id in translated_ids if translated_ids.count(block_id) > 1})
    missing = [block_id for block_id in source_ids if block_id not in translated_set]
    unexpected = [block_id for block_id in translated_ids if block_id not in source_set]
    translated_by_id = {block.block_id: block for block in translated.blocks}
    source_by_id = {block.block_id: block for block in source.blocks}

    empty: list[str] = []
    abnormal_short: list[str] = []
    marker_mismatches: list[str] = []
    english_residue: list[str] = []
    pass_ids: list[str] = []
    for block_id in source_ids:
        block = translated_by_id.get(block_id)
        if block is None:
            continue
        text = (block.translated_text or "").strip()
        if not text:
            empty.append(block_id)
            continue
        source_block = source_by_id[block_id]
        source_words = _source_words(source_block.source_text)
        translated_characters = _translated_characters(text)
        if source_block.type in {"paragraph", "quote", "blockquote"} and source_words >= 80:
            if translated_characters < source_words * 0.65:
                abnormal_short.append(block_id)
        expected_pages = [anchor.pdf_page for anchor in source_block.page_anchors]
        actual_pages = [int(value) for value in _PAGE_MARKER.findall(text)]
        expected_notes = [reference.number for reference in source_block.footnote_refs]
        actual_notes = [int(value) for value in _FOOTNOTE_MARKER.findall(text)]
        if expected_pages != actual_pages or expected_notes != actual_notes:
            marker_mismatches.append(block_id)
        if _LONG_ENGLISH_RUN.search(_PAGE_MARKER.sub("", _FOOTNOTE_MARKER.sub("", text))):
            english_residue.append(block_id)
        if block_id not in abnormal_short and block_id not in marker_mismatches and block_id not in english_residue:
            pass_ids.append(block_id)

    source_notes = {note.number: note for note in source.footnotes}
    translated_notes = {note.number: note for note in translated.footnotes}
    missing_notes = sorted(set(source_notes) - set(translated_notes))
    unexpected_notes = sorted(set(translated_notes) - set(source_notes))
    empty_notes = sorted(
        number for number in source_notes
        if number in translated_notes and not (translated_notes[number].translated_text or "").strip()
    )
    short_notes = sorted(
        number for number, note in source_notes.items()
        if number in translated_notes
        and _source_words(note.source_text) >= 80
        and _translated_characters(translated_notes[number].translated_text) < _source_words(note.source_text) * 0.50
    )

    source_images = {image.image_id: image for image in source.images}
    translated_images = {image.image_id: image for image in translated.images}
    missing_images = sorted(set(source_images) - set(translated_images))
    unexpected_images = sorted(set(translated_images) - set(source_images))
    empty_captions = sorted(
        image_id for image_id in source_images
        if image_id in translated_images and not (translated_images[image_id].caption_zh or "").strip()
    )

    reviewed_ids = reviewed_ids or set()
    reviewed_blocks = len(source_set & reviewed_ids) if reviewed_ids else len(pass_ids)
    failures = {
        "missing_blocks": missing,
        "unexpected_blocks": unexpected,
        "duplicated_blocks": duplicates,
        "empty_translations": empty,
        "abnormal_short_translations": abnormal_short,
        "marker_mismatches": marker_mismatches,
        "english_residue_blocks": english_residue,
        "missing_footnotes": missing_notes,
        "unexpected_footnotes": unexpected_notes,
        "empty_footnotes": empty_notes,
        "abnormal_short_footnotes": short_notes,
        "missing_images": missing_images,
        "unexpected_images": unexpected_images,
        "empty_image_captions": empty_captions,
    }
    decision = "PASS" if not any(failures.values()) else "FAIL"
    return {
        "source_blocks": len(source_ids),
        "translated_blocks": len(translated_ids),
        "reviewed_blocks": reviewed_blocks,
        "pass_blocks": len(pass_ids),
        "source_footnotes": len(source_notes),
        "footnotes_translated": len(source_notes) - len(missing_notes) - len(empty_notes),
        "source_images": len(source_images),
        "image_captions_translated": len(source_images) - len(missing_images) - len(empty_captions),
        "ignored_rejected_cache": True,
        **failures,
        "translation_completeness": decision,
        "pre_render_decision": decision,
    }


def _write_gate_report(path: Path, result: dict[str, Any]) -> None:
    def count(name: str) -> int:
        return len(result[name])

    english = "0" if not result["english_residue_blocks"] else ", ".join(result["english_residue_blocks"])
    lines = [
        "# PRE-RENDER GATE",
        "",
        f"SOURCE_BLOCKS: {result['source_blocks']}",
        f"TRANSLATED_BLOCKS: {result['translated_blocks']}",
        f"REVIEWED_BLOCKS: {result['reviewed_blocks']}",
        f"PASS_BLOCKS: {result['pass_blocks']}",
        f"EMPTY_TRANSLATIONS: {count('empty_translations')}",
        f"MISSING_BLOCKS: {count('missing_blocks')}",
        f"DUPLICATED_BLOCKS: {count('duplicated_blocks')}",
        f"UNEXPECTED_BLOCKS: {count('unexpected_blocks')}",
        f"FOOTNOTES_TRANSLATED: {result['footnotes_translated']}/{result['source_footnotes']}",
        f"IMAGE_CAPTIONS_TRANSLATED: {result['image_captions_translated']}/{result['source_images']}",
        f"ENGLISH_RESIDUE_EXCEPT_PROPER_NOUNS: {english}",
        f"TRANSLATION_COMPLETENESS: {result['translation_completeness']}",
        f"PRE_RENDER_DECISION: {result['pre_render_decision']}",
        "",
        "## Failure details",
        "",
    ]
    for key in (
        "missing_blocks", "unexpected_blocks", "duplicated_blocks", "empty_translations",
        "abnormal_short_translations", "marker_mismatches", "english_residue_blocks",
        "missing_footnotes", "unexpected_footnotes", "empty_footnotes", "abnormal_short_footnotes",
        "missing_images", "unexpected_images", "empty_image_captions",
    ):
        value = result[key]
        lines.append(f"- {key}: {', '.join(map(str, value)) if value else 'None'}")
    lines.extend(["", "Rejected `.tmp` and rejected-draft caches are outside the canonical gate input and were ignored.", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_pre_render_gate(project_root: Path, chapter_number: int, *, require_pass: bool = False) -> dict[str, Any]:
    project_root = project_root.resolve()
    report_dir = project_root / "reports" / chapter_stem(chapter_number)
    source_path = chapter_json_path(project_root, chapter_number, "source")
    translated_path = chapter_json_path(project_root, chapter_number, "zh")
    if not source_path.exists() or not translated_path.exists():
        missing = "source" if not source_path.exists() else "translation"
        result = {
            "source_blocks": 0, "translated_blocks": 0, "reviewed_blocks": 0, "pass_blocks": 0,
            "source_footnotes": 0, "footnotes_translated": 0, "source_images": 0,
            "image_captions_translated": 0, "ignored_rejected_cache": True,
            "missing_blocks": [f"canonical {missing} JSON"], "unexpected_blocks": [],
            "duplicated_blocks": [], "empty_translations": [], "abnormal_short_translations": [],
            "marker_mismatches": [], "english_residue_blocks": [], "missing_footnotes": [],
            "unexpected_footnotes": [], "empty_footnotes": [], "abnormal_short_footnotes": [],
            "missing_images": [], "unexpected_images": [], "empty_image_captions": [],
            "translation_completeness": "FAIL", "pre_render_decision": "FAIL",
        }
    else:
        source = StructuredChapter.from_dict(read_json(source_path))
        translated = StructuredChapter.from_dict(read_json(translated_path))
        result = evaluate_pre_render_gate(
            source, translated, reviewed_ids=_reviewed_ids(project_root, chapter_number)
        )
    report_dir.mkdir(parents=True, exist_ok=True)
    write_json(report_dir / "pre-render-gate.json", result)
    _write_gate_report(report_dir / "PRE_RENDER_GATE.md", result)
    if require_pass and result["pre_render_decision"] != "PASS":
        raise RuntimeError(
            f"PRE_RENDER_GATE FAIL for chapter {chapter_number}; see "
            f"{report_dir / 'PRE_RENDER_GATE.md'}"
        )
    return result
