from __future__ import annotations

import json
import re
from pathlib import Path

from .models import Footnote, FootnoteRef, StructuredChapter
from .utils import chapter_json_path, read_json, write_json
from .source_markdown import render_source_markdown


def extract_chapter_endnotes(pages_jsonl: Path, chapter_number: int) -> list[Footnote]:
    pages = [json.loads(line) for line in pages_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    start_marker = f"Notes to Chapter {chapter_number}"
    next_marker = f"Notes to Chapter {chapter_number + 1}"
    collecting = False
    pieces: list[str] = []
    for page in pages:
        text = str(page.get("text", ""))
        if not collecting and start_marker in text:
            collecting = True
            text = text.split(start_marker, 1)[1]
        if not collecting:
            continue
        stop_markers = [marker for marker in (next_marker, "\n References", "\nReferences", "\n Index", "\nIndex") if marker in text]
        if stop_markers:
            position = min(text.index(marker) for marker in stop_markers)
            pieces.append(text[:position])
            break
        pieces.append(text)
    if not pieces:
        return []
    text = "\n".join(pieces)
    text = re.sub(r"(?m)^\s*\d+\s*::\s*NOTES TO PAGES[^\n]*$", "", text)
    text = re.sub(r"(?m)^\s*NOTES TO PAGES[^\n]*::\s*\d+\s*$", "", text)
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    text = re.sub(r"\s*\n\s*", " ", text).strip()
    text = text.replace("HansJörg", "Hans-Jörg").replace("neverending", "never-ending").replace("postKatrina", "post-Katrina")
    # Keep the leading boundary zero-width.  Consuming it loses a real note
    # number when the preceding note ends with a numbered archival reference,
    # for example "B.N. 1. 9. The next note ...".
    raw_matches = list(re.finditer(r"(?<!\S)(\d{1,2})\.\s+", text))
    # Notes often contain ordinary numbered references such as "chapter 7. In ...".
    # Accept only the monotonically increasing note sequence so those citations do
    # not become duplicate endnote boundaries.  Skipped matches remain part of the
    # surrounding note body because slicing uses the next accepted match.
    matches = []
    expected = 1
    for match in raw_matches:
        if int(match.group(1)) == expected:
            matches.append(match)
            expected += 1
    notes: list[Footnote] = []
    for index, match in enumerate(matches):
        number = int(match.group(1))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = re.sub(r"\s+", " ", text[match.end():end]).strip()
        notes.append(Footnote(number=number, source_text=body))
    return notes


def bind_endnote_references(chapter: StructuredChapter, notes: list[Footnote]) -> None:
    for block in chapter.blocks:
        block.footnote_refs = []
    for note in notes:
        candidates = []
        # A printed endnote marker follows punctuation, but figure labels such as
        # "figure 4.5" do as well after extraction.  Reject that semantic context
        # instead of all digit-dot prefixes: a real marker can legitimately follow
        # a year, as in "born in 1903.1 After ...".
        pattern = re.compile(rf"(?<=[.!?:…\u2019\u201d)]){note.number}(?=\s|$)")
        for block in chapter.blocks:
            for match in pattern.finditer(block.source_text):
                prefix = block.source_text[:match.start()]
                suffix = block.source_text[match.end():]
                if re.search(r"(?:figure|fig\.)\s+\d+\.$", prefix, re.IGNORECASE):
                    continue
                # Version and licence decimals can look exactly like an endnote
                # after extraction (for example, "Share Alike 2.5 Generic
                # License").  Reject the decimal only when its surrounding
                # lexical context identifies a version/licence expression.  Do
                # not reject every digit-dot-number sequence: a genuine marker
                # can immediately follow a year, such as "born in 1903.1".
                if re.search(r"(?:version|license|licence|share\s+alike)\s+\d+\.$", prefix, re.IGNORECASE) and re.match(
                    r"\s+(?:generic\s+)?(?:license|licence|release|edition|version)\b", suffix, re.IGNORECASE
                ):
                    continue
                candidates.append((block, match))
        if len(candidates) != 1:
            raise RuntimeError(f"expected one reference for note {note.number}, found {len(candidates)}")
        block, match = candidates[0]
        block.source_text = block.source_text[:match.start()] + block.source_text[match.end():]
        block.footnote_refs.append(FootnoteRef(number=note.number, offset=match.start()))
        note.block_id = block.block_id


def attach_project_endnotes(project_root: Path, chapter_number: int) -> StructuredChapter:
    source_path = chapter_json_path(project_root, chapter_number, "source")
    chapter = StructuredChapter.from_dict(read_json(source_path))
    notes = extract_chapter_endnotes(project_root / "intermediate" / "ebook-pages.jsonl", chapter_number)
    bind_endnote_references(chapter, notes)
    chapter.footnotes = notes
    write_json(source_path, chapter.to_dict())
    render_source_markdown(chapter, source_path.with_suffix(".md"))
    return chapter
