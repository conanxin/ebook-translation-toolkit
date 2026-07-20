from __future__ import annotations

from pathlib import Path

from .models import StructuredChapter, Term
from .utils import chapter_json_path, read_json, write_json


def apply_translation_map(project_root: Path, chapter_number: int, mapping_path: Path) -> StructuredChapter:
    chapter = StructuredChapter.from_dict(read_json(chapter_json_path(project_root, chapter_number, "source")))
    mapping = read_json(mapping_path)
    block_map = mapping.get("blocks", {})
    missing = [block.block_id for block in chapter.blocks if block.block_id not in block_map]
    extras = sorted(set(block_map) - {block.block_id for block in chapter.blocks})
    if missing or extras:
        raise RuntimeError(f"translation map mismatch; missing={missing}, extras={extras}")
    for block in chapter.blocks:
        block.translated_text = str(block_map[block.block_id]).strip()
        if not block.translated_text:
            raise RuntimeError(f"empty translation: {block.block_id}")
    note_map = {int(key): value for key, value in mapping.get("footnotes", {}).items()}
    if set(note_map) != {note.number for note in chapter.footnotes}:
        raise RuntimeError("translated footnotes do not match source footnotes")
    for note in chapter.footnotes:
        note.translated_text = str(note_map[note.number]).strip()
    if chapter.images:
        caption_map = mapping.get("image_captions", {})
        expected_images = {image.image_id for image in chapter.images}
        if set(caption_map) != expected_images:
            raise RuntimeError("translated image captions do not match source images")
        for image in chapter.images:
            image.caption_zh = str(caption_map[image.image_id]).strip()
            if not image.caption_zh:
                raise RuntimeError(f"empty image caption: {image.image_id}")
    chapter.chapter.update(mapping.get("chapter", {}))
    if mapping.get("terms"):
        chapter.terms = [Term(**item) for item in mapping["terms"]]
    output = chapter_json_path(project_root, chapter_number, "zh")
    write_json(output, chapter.to_dict())
    return chapter
