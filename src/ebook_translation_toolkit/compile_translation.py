from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .utils import chapter_data_dir, chapter_json_path, chapter_stem, read_json, read_yaml, write_json


def _translation_overrides_for_chapter(raw: dict[str, Any], chapter_number: int) -> dict[str, Any]:
    """Return chapter-local translation overrides, retaining legacy support.

    Stable block IDs intentionally restart in every chapter.  Therefore a
    book-level merge table must never be applied across chapters merely
    because two chapters both contain (for example) ``p-026``.
    """
    chapters = raw.get("chapters")
    if isinstance(chapters, dict):
        selected = chapters.get(chapter_number, chapters.get(str(chapter_number), {}))
        if selected is None:
            return {}
        if not isinstance(selected, dict):
            raise RuntimeError(f"translation overrides for chapter {chapter_number} must be a mapping")
        return selected
    return raw


def _read_jsonl(path: Path, key: str, value: str) -> dict[Any, str]:
    if not path.exists():
        raise FileNotFoundError(path)
    result: dict[Any, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip():
            continue
        item = json.loads(raw)
        item_key = item[key]
        if item_key in result:
            raise RuntimeError(f"duplicate {key} {item_key!r} in {path}:{line_number}")
        text = str(item.get(value, "")).strip()
        if not text:
            raise RuntimeError(f"empty {value} for {item_key!r} in {path}:{line_number}")
        result[item_key] = text
    return result


def _inject_missing_page_markers(text: str, source_text: str, anchors: list[dict[str, Any]]) -> str:
    """Keep translated page anchors complete without creating paragraphs.

    Review workfiles normally carry explicit ``[[PAGE:...]]`` markers.  When a
    later semantic merge creates a new cross-page block, the new boundary may
    be absent.  Insert only missing markers, at the nearest natural translated
    text boundary to the proportional source offset, and preserve source order.
    """
    existing = {int(value) for value in re.findall(r"\[\[PAGE:(\d+)\|", text)}
    insertions: list[tuple[int, str]] = []
    source_length = max(1, len(source_text))
    for anchor in anchors:
        page = int(anchor["pdf_page"])
        if page in existing:
            continue
        approximate = round(len(text) * int(anchor.get("offset", 0)) / source_length)
        lower, upper = max(0, approximate - 80), min(len(text), approximate + 80)
        candidates = [
            index + 1 for index in range(lower, upper)
            if text[index] in "。！？；：.!?;:\n"
        ]
        if not candidates:
            candidates = [index for index in range(lower, upper) if text[index].isspace()]
        position = min(candidates, key=lambda value: abs(value - approximate)) if candidates else approximate
        marker = f"[[PAGE:{page}|{anchor.get('printed_page', '')}]]"
        insertions.append((position, marker))
    for position, marker in sorted(insertions, reverse=True):
        text = text[:position] + marker + text[position:]
    return text


def compile_translation_workfiles(project_root: Path, chapter_number: int) -> Path:
    """Compile review-friendly JSONL workfiles into the strict translation map.

    A translator may retain pre-normalization fragment rows while reviewing a
    chapter. ``translation-overrides.yaml`` declares which fragment rows are
    concatenated into a final stable block. Every row must be consumed exactly
    once, so a stale or accidental translation cannot silently disappear.
    """
    project_root = project_root.resolve()
    data_dir = chapter_data_dir(project_root, chapter_number)
    stem = chapter_stem(chapter_number)
    source = read_json(chapter_json_path(project_root, chapter_number, "source"))
    block_rows = _read_jsonl(data_dir / f"{stem}-blocks-zh.jsonl", "block_id", "translated_text")
    footnote_rows = _read_jsonl(data_dir / f"{stem}-footnotes-zh.jsonl", "number", "translated_text")
    caption_rows = _read_jsonl(data_dir / f"{stem}-image-captions-zh.jsonl", "image_id", "caption_zh")

    overrides = _translation_overrides_for_chapter(
        read_yaml(project_root / ".ebook-translation" / "translation-overrides.yaml"), chapter_number
    )
    merge_config = overrides.get("merge", {}) or {}
    if not isinstance(merge_config, dict):
        raise RuntimeError("translation-overrides.yaml merge must be a mapping")
    consumed: set[str] = set()
    blocks: dict[str, str] = {}
    source_ids = [str(item["block_id"]) for item in source.get("blocks", [])]
    for block_id in source_ids:
        if block_id not in block_rows:
            raise RuntimeError(f"missing translated block: {block_id}")
        parts = [block_rows[block_id]]
        consumed.add(block_id)
        for fragment_id in merge_config.get(block_id, []) or []:
            fragment_id = str(fragment_id)
            if fragment_id in consumed:
                raise RuntimeError(f"translation fragment consumed twice: {fragment_id}")
            if fragment_id not in block_rows:
                raise RuntimeError(f"missing translation fragment: {fragment_id}")
            parts.append(block_rows[fragment_id])
            consumed.add(fragment_id)
        source_block = next(item for item in source.get("blocks", []) if str(item["block_id"]) == block_id)
        blocks[block_id] = _inject_missing_page_markers(
            "".join(parts), str(source_block.get("source_text", "")), source_block.get("page_anchors", [])
        )
    extras = sorted(set(block_rows) - consumed)
    if extras:
        raise RuntimeError(f"unconsumed translated block rows: {extras}")

    expected_notes = {int(item["number"]) for item in source.get("footnotes", [])}
    if set(footnote_rows) != expected_notes:
        raise RuntimeError(
            f"footnote workfile mismatch; missing={sorted(expected_notes-set(footnote_rows))}, "
            f"extras={sorted(set(footnote_rows)-expected_notes)}"
        )
    expected_images = {str(item["image_id"]) for item in source.get("images", [])}
    if set(caption_rows) != expected_images:
        raise RuntimeError(
            f"caption workfile mismatch; missing={sorted(expected_images-set(caption_rows))}, "
            f"extras={sorted(set(caption_rows)-expected_images)}"
        )

    metadata_path = data_dir / f"{stem}-translation-metadata.json"
    metadata = read_json(metadata_path) if metadata_path.exists() else {}
    terms_path = data_dir / f"{stem}-terms.json"
    terms = read_json(terms_path) if terms_path.exists() else []
    mapping = {
        "chapter": metadata.get("chapter", metadata),
        "blocks": blocks,
        "footnotes": {str(key): footnote_rows[key] for key in sorted(footnote_rows)},
        "image_captions": {key: caption_rows[key] for key in sorted(caption_rows)},
        "terms": terms,
    }
    output = data_dir / f"{stem}-translation-map.json"
    write_json(output, mapping)
    return output
