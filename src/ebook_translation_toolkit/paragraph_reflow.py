from __future__ import annotations

import json
from dataclasses import asdict
import re
from pathlib import Path
from typing import Any

from .models import Block, FootnoteRef, PageAnchor, StructuredChapter
from .utils import chapter_json_path, load_project_config, read_json, read_yaml, write_json


TERMINAL = re.compile(r"[.!?。！？][\"'’”）)]*\d*$")
CONTINUATION = re.compile(
    r"^(?:(?:and|but|or|nor|so|yet|because|which|that|who|with|of|to|for|in|on|as|than)\b|[,;:—–-])",
)


def _clean(text: str) -> str:
    text = re.sub(r"(?<=\w)(?:-|\u00ad)\s*\n\s*(?=\w)", "", text)
    text = text.replace("\u00ad", "")
    # A few legacy embedded-font glyphs in scholarly PDFs map to CJK symbols
    # instead of their intended English punctuation during native extraction.
    text = text.translate(str.maketrans({"＊": "’", "※": "“", "§": "”", "每": "–", "〞": "—", "\u00a0": " "}))
    return re.sub(r"\s*\n\s*", " ", text).strip()


def should_merge(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    if previous.get("page") == current.get("page"):
        return False
    left = _clean(previous.get("text", ""))
    right = _clean(current.get("text", ""))
    if not left or not right:
        return False
    if left.endswith("-") and right[:1].islower():
        return True
    if not TERMINAL.search(left):
        return True
    if right[:1].islower() or CONTINUATION.search(right):
        return True
    return False


def _override_pairs(overrides: dict[str, Any]) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for group in overrides.get("merge", []) or []:
        for first, second in zip(group, group[1:]):
            result.add((str(first), str(second)))
    return result


def group_layout_lines(lines: list[dict[str, Any]], base_x: float) -> list[list[dict[str, Any]]]:
    """Group native PDF lines without splitting every line of an indented quote.

    A normal paragraph begins with one indented line and wraps back to the body
    margin. A display quotation keeps the same inset on every wrapped line and
    may use a deeper inset for a new paragraph. Only a transition from the body
    margin or a genuine increase in indentation starts a new paragraph.
    """
    groups: list[list[dict[str, Any]]] = []
    for line in lines:
        start_new = not groups
        if groups:
            prior = groups[-1][-1]
            gap = line["bbox"][1] - prior["bbox"][3]
            start_new = line["type"] != groups[-1][0]["type"]
            if line["type"] == "heading":
                start_new = True
            elif line["type"] == "paragraph" and line["bbox"][0] >= base_x + 8:
                prior_x = float(prior["bbox"][0])
                current_x = float(line["bbox"][0])
                prior_at_body_margin = prior_x < base_x + 8
                deeper_indent = current_x >= prior_x + 8
                start_new = prior_at_body_margin or deeper_indent
            elif line["type"] == "paragraph" and prior["type"] == "paragraph":
                prior_x = float(prior["bbox"][0])
                current_x = float(line["bbox"][0])
                dedented_to_body = len(groups[-1]) > 1 and prior_x >= base_x + 8 and current_x < base_x + 8
                start_new = dedented_to_body or gap > max(10.0, line["font_size"] * 1.6)
            elif gap > max(10.0, line["font_size"] * 1.6):
                start_new = True
            if groups[-1][0]["type"] == "attribution" and line["type"] == "blockquote" and line["text"].startswith("(") and gap < 10:
                start_new = False
                line["type"] = "attribution"
        if start_new:
            groups.append([line])
        else:
            groups[-1].append(line)
    return groups


def normalize_semantic_blocks(blocks: list[Block]) -> list[Block]:
    """Repair small typographic fragments after the geometric reflow pass.

    Courier-bold section headings are frequently exposed as attributions, and
    long bibliographic attributions can wrap into a following Courier line.
    Chapter subtitles can likewise wrap into one lower-case continuation line.
    These repairs preserve the leading block id and rebase any internal page
    anchors, so repeated normalization remains deterministic.
    """
    def merge_pair(left: Block, right: Block, block_type: str) -> None:
        separator = ""
        if not left.source_text.endswith(("-", "\u00ad")):
            separator = " "
        left_len = len(left.source_text) + len(separator)
        left.source_text = _clean(left.source_text + separator + right.source_text)
        left.type = block_type
        prior_end_page = left.source_pdf_page_end
        if right.source_pdf_page_start > prior_end_page:
            for page in range(prior_end_page + 1, right.source_pdf_page_start + 1):
                printed = right.printed_page_start if page == right.source_pdf_page_start else ""
                if not any(anchor.pdf_page == page for anchor in left.page_anchors):
                    left.page_anchors.append(PageAnchor(page, printed, left_len, left.block_id))
        if right.source_pdf_page_end > left.source_pdf_page_end:
            left.source_pdf_page_end = right.source_pdf_page_end
            left.printed_page_end = right.printed_page_end
        left.page_anchors.extend(
            PageAnchor(anchor.pdf_page, anchor.printed_page, anchor.offset + left_len, left.block_id)
            for anchor in right.page_anchors
            if not any(existing.pdf_page == anchor.pdf_page for existing in left.page_anchors)
        )
        left.footnote_refs.extend(
            FootnoteRef(ref.number, ref.offset + left_len) for ref in right.footnote_refs
        )
        left.image_after.extend(item for item in right.image_after if item not in left.image_after)
        left.styles = sorted(set(left.styles + right.styles))

    # Join wrapped citations before deciding whether a Courier-bold line is a
    # section heading. This prevents the first half of a citation from being
    # mistaken for a heading merely because its year occurs on the next line.
    citation_repaired: list[Block] = []
    merged_citation_ids: set[str] = set()
    index = 0
    while index < len(blocks):
        current = blocks[index]
        following = blocks[index + 1] if index + 1 < len(blocks) else None
        if (
            following
            and current.type == "attribution"
            and following.type == "blockquote"
            and current.source_pdf_page_end == following.source_pdf_page_start
            and len(following.source_text) <= 140
            and (
                current.source_text.rstrip().endswith(",")
                or re.search(r"\b(?:19|20)\d{2}[a-z]?\b|\b(?:p{1,2}|vol|ed)\.", following.source_text, re.I)
            )
        ):
            merge_pair(current, following, "attribution")
            merged_citation_ids.add(current.block_id)
            citation_repaired.append(current)
            index += 2
            continue
        citation_repaired.append(current)
        index += 1

    for block_index, block in enumerate(citation_repaired):
        text = block.source_text.strip()
        previous_type = citation_repaired[block_index - 1].type if block_index else ""
        if (
            block.type == "attribution"
            and len(text) <= 100
            and not re.search(r"\b(?:19|20)\d{2}[a-z]?\b|\b(?:p{1,2}|vol|ed)\.\s*\d", text, re.I)
            and not re.match(r"^(?:figure|fig\.)\s", text, re.I)
            and previous_type != "blockquote"
            and block.block_id not in merged_citation_ids
        ):
            block.type = "heading"

    repaired: list[Block] = []
    index = 0
    while index < len(citation_repaired):
        current = citation_repaired[index]
        following = citation_repaired[index + 1] if index + 1 < len(citation_repaired) else None
        if (
            following
            and current.type == "heading"
            and following.type == "blockquote"
            and current.source_pdf_page_start == following.source_pdf_page_start
            and following.source_text[:1].islower()
            and not any(item.type == "paragraph" for item in repaired)
        ):
            merge_pair(current, following, "heading")
            repaired.append(current)
            index += 2
            continue
        repaired.append(current)
        index += 1

    cross_page_repaired: list[Block] = []
    for block in repaired:
        if cross_page_repaired:
            previous = cross_page_repaired[-1]
            caption_context = (
                len(cross_page_repaired) >= 2
                and cross_page_repaired[-2].source_pdf_page_end == previous.source_pdf_page_end
                and re.match(r"^Figure\s+\d+\.\d+\.", cross_page_repaired[-2].source_text, re.I)
            )
            if (
                previous.type == block.type
                and block.type in {"paragraph", "blockquote"}
                and previous.source_pdf_page_end < block.source_pdf_page_start
                and not caption_context
                and should_merge(
                    {"page": previous.source_pdf_page_end, "text": previous.source_text},
                    {"page": block.source_pdf_page_start, "text": block.source_text},
                )
            ):
                merge_pair(previous, block, previous.type)
                continue
        cross_page_repaired.append(block)

    for order, block in enumerate(cross_page_repaired, 1):
        block.reading_order = order
    return cross_page_repaired


def extract_pdf_layout_pages(pdf_path: Path, page_metadata: list[dict[str, Any]], start_page: int, end_page: int) -> list[dict[str, Any]]:
    """Reconstruct logical per-page blocks from line indentation and typography.

    The page JSON remains the source for printed page labels.  Native PDF line
    geometry is used because many publishers encode several indented logical
    paragraphs as one coarse text block.
    """
    import fitz

    printed = {int(item["page_index"]): item.get("printed_page_number", "") for item in page_metadata}
    document = fitz.open(pdf_path)
    result: list[dict[str, Any]] = []
    for page_number in range(start_page, end_page + 1):
        page = document[page_number - 1]
        lines: list[dict[str, Any]] = []
        for raw_block in page.get_text("dict").get("blocks", []):
            if raw_block.get("type") != 0:
                continue
            for raw_line in raw_block.get("lines", []):
                spans = raw_line.get("spans", [])
                text = "".join(span.get("text", "") for span in spans).strip()
                if not text:
                    continue
                bbox = list(raw_line.get("bbox", [0, 0, 0, 0]))
                if bbox[1] < 50 or bbox[1] > page.rect.height - 28:
                    continue
                first = spans[0]
                font_name = str(first.get("font", ""))
                font_size = float(first.get("size", 0) or 0)
                is_bold = "Bold" in font_name or bool(first.get("flags", 0) & 16)
                if font_size >= 14:
                    block_type = "heading"
                elif font_name.startswith("Courier-Bold"):
                    block_type = "attribution"
                elif font_name.startswith("Courier"):
                    block_type = "blockquote"
                else:
                    block_type = "paragraph"
                lines.append({"text": text, "bbox": bbox, "font_name": font_name, "font_size": font_size, "bold": is_bold, "type": block_type})
        body_x = [line["bbox"][0] for line in lines if line["type"] == "paragraph" and line["font_size"] < 13]
        base_x = min(body_x) if body_x else 0.0
        groups = group_layout_lines(lines, base_x)
        blocks = []
        for index, group in enumerate(groups, 1):
            text = "\n".join(item["text"] for item in group)
            block_type = group[0]["type"]
            if block_type == "paragraph" and min(float(item["bbox"][0]) for item in group) >= base_x + 8:
                block_type = "blockquote"
            blocks.append({
                "block_id": f"p{page_number:04d}-layout-{index:03d}",
                "bbox": [group[0]["bbox"][0], group[0]["bbox"][1], group[-1]["bbox"][2], group[-1]["bbox"][3]],
                "text": text,
                "reading_order": index - 1,
                "font_name": group[0]["font_name"],
                "font_size": group[0]["font_size"],
                "bold": group[0]["bold"],
                "italic": False,
                "block_type": block_type,
            })
        result.append({"page_index": page_number, "printed_page_number": printed.get(page_number, ""), "blocks": blocks})
    document.close()
    return result


def normalize_page_records(
    pages: list[dict[str, Any]],
    start_page: int,
    end_page: int,
    overrides: dict[str, Any] | None = None,
) -> list[Block]:
    overrides = overrides or {}
    force_merge = _override_pairs(overrides)
    raw: list[dict[str, Any]] = []
    for page in pages:
        number = int(page["page_index"])
        if not start_page <= number <= end_page:
            continue
        for block in sorted(page.get("blocks", []), key=lambda item: item.get("reading_order", 0)):
            if block.get("block_type") in {"header", "footer"}:
                continue
            text = _clean(block.get("text", ""))
            if not text:
                continue
            font_name = str(block.get("font_name", ""))
            source_type = block.get("block_type", "paragraph")
            if source_type == "body":
                if font_name.startswith("Courier-Bold"):
                    source_type = "attribution"
                elif font_name.startswith("Courier"):
                    source_type = "blockquote"
                else:
                    source_type = "paragraph"
            raw.append({
                "raw_id": block.get("block_id", f"raw-{number}-{len(raw)+1}"),
                "text": text,
                "page": number,
                "printed": page.get("printed_page_number", ""),
                "type": source_type,
                "font_name": font_name,
                "font_size": float(block.get("font_size", 0) or 0),
                "bbox": block.get("bbox", []),
                "styles": [name for name in ("bold", "italic") if block.get(name)],
            })

    # Some PDFs expose each line of a display quotation as a separate block.
    # Coalesce only typographically continuous Courier lines; ordinary body
    # blocks on the same page remain distinct logical paragraphs.
    line_groups: list[list[dict[str, Any]]] = []
    for item in raw:
        if line_groups:
            previous = line_groups[-1][-1]
            same_page = previous["page"] == item["page"]
            prior_box, box = previous.get("bbox", []), item.get("bbox", [])
            vertical_gap = (float(box[1]) - float(prior_box[3])) if len(prior_box) == len(box) == 4 else 999
            layout_blocks = "-layout-" in previous["raw_id"] or "-layout-" in item["raw_id"]
            quote_line = previous["type"] == item["type"] == "blockquote" and vertical_gap < 10 and not layout_blocks
            citation_wrap = previous["type"] == "attribution" and item["type"] == "blockquote" and item["text"].startswith("(") and vertical_gap < 10
            if same_page and (quote_line or citation_wrap):
                line_groups[-1].append(item)
                if citation_wrap:
                    line_groups[-1][0]["type"] = "attribution"
                continue
        line_groups.append([item])
    raw = []
    for group in line_groups:
        first = dict(group[0])
        first["text"] = " ".join(item["text"] for item in group)
        first["raw_id"] = "+".join(item["raw_id"] for item in group)
        first_box = group[0].get("bbox") or [0, 0, 0, 0]
        last_box = group[-1].get("bbox") or [0, 0, 0, 0]
        first["bbox"] = [first_box[0], first_box[1], last_box[2], last_box[3]]
        raw.append(first)

    groups: list[list[dict[str, Any]]] = []
    for item in raw:
        if groups:
            previous = groups[-1][-1]
            forced = (previous["raw_id"], item["raw_id"]) in force_merge
            mergeable_type = previous["type"] == item["type"] and item["type"] in {"paragraph", "blockquote"}
            caption_context = (
                len(groups) >= 2
                and groups[-2][-1]["page"] == previous["page"]
                and re.match(r"^Figure\s+\d+\.\d+\.", groups[-2][-1]["text"], re.I)
            )
            if forced or (mergeable_type and not caption_context and should_merge(previous, item)):
                groups[-1].append(item)
                continue
        groups.append([item])

    blocks: list[Block] = []
    paragraph_number = 0
    other_number = 0
    for order, group in enumerate(groups, 1):
        block_type = "paragraph" if all(item["type"] == "paragraph" for item in group) else group[0]["type"]
        if block_type == "paragraph":
            paragraph_number += 1
            block_id = f"p-{paragraph_number:03d}"
        else:
            other_number += 1
            block_id = f"b-{other_number:03d}"
        text_parts: list[str] = []
        anchors: list[PageAnchor] = []
        prior_page = group[0]["page"]
        for item in group:
            if item["page"] != prior_page:
                anchors.append(PageAnchor(item["page"], str(item["printed"]), len(" ".join(text_parts)) + 1, block_id))
                prior_page = item["page"]
            text_parts.append(item["text"])
        block = Block(
            block_id=block_id,
            type=block_type,
            source_text=" ".join(text_parts),
            source_pdf_page_start=group[0]["page"],
            source_pdf_page_end=group[-1]["page"],
            printed_page_start=str(group[0]["printed"]),
            printed_page_end=str(group[-1]["printed"]),
            page_anchors=anchors,
            styles=sorted({style for item in group for style in item["styles"]}),
            reading_order=order,
        )
        blocks.append(block)

    for instruction in overrides.get("split", []) or []:
        block_id = instruction.get("block")
        marker = instruction.get("after", "")
        for index, block in enumerate(list(blocks)):
            if block.block_id == block_id and marker in block.source_text:
                cut = block.source_text.index(marker) + len(marker)
                data = asdict(block)
                left_anchors = [anchor for anchor in block.page_anchors if anchor.offset <= cut]
                right_anchors = [PageAnchor(anchor.pdf_page, anchor.printed_page, anchor.offset - cut, block.block_id + "b") for anchor in block.page_anchors if anchor.offset > cut]
                split_page = block.source_pdf_page_start
                split_printed = block.printed_page_start
                for anchor in block.page_anchors:
                    if anchor.offset <= cut:
                        split_page = anchor.pdf_page
                        split_printed = anchor.printed_page
                left = Block.from_dict(
                    {
                        **data,
                        "block_id": instruction.get("left_id", block.block_id),
                        "type": instruction.get("left_type", block.type),
                        "source_text": block.source_text[:cut].strip(),
                        "source_pdf_page_end": split_page,
                        "printed_page_end": split_printed,
                        "page_anchors": [asdict(anchor) for anchor in left_anchors],
                    }
                )
                right_id = instruction.get("right_id", block.block_id + "b")
                for anchor in right_anchors:
                    anchor.within_block = right_id
                right = Block.from_dict(
                    {
                        **data,
                        "block_id": right_id,
                        "type": instruction.get("right_type", block.type),
                        "source_text": block.source_text[cut:].strip(),
                        "source_pdf_page_start": split_page,
                        "printed_page_start": split_printed,
                        "page_anchors": [asdict(anchor) for anchor in right_anchors],
                    }
                )
                blocks[index:index + 1] = [left, right]
                break

    for instruction in overrides.get("retype", []) or []:
        block_id = instruction.get("block")
        target_type = instruction.get("type")
        if not block_id or not target_type:
            continue
        for block in blocks:
            if block.block_id == block_id:
                block.type = str(target_type)
                break
    blocks = normalize_semantic_blocks(blocks)
    for instruction in overrides.get("replace", []) or []:
        block_id = instruction.get("block")
        old = str(instruction.get("old", ""))
        new = str(instruction.get("new", ""))
        if not block_id or not old:
            continue
        for block in blocks:
            if block.block_id == block_id and old in block.source_text:
                block.source_text = block.source_text.replace(old, new)
                break
    return blocks


def chapter_overrides(raw_overrides: dict, chapter_number: int) -> dict:
    """Combine legacy global overrides with chapter-scoped instructions."""
    result: dict[str, list] = {}
    scoped = (raw_overrides.get("chapters", {}) or {}).get(str(chapter_number), {}) or {}
    for key in ("merge", "split", "retype", "replace"):
        result[key] = list(raw_overrides.get(key, []) or []) + list(scoped.get(key, []) or [])
    return result


def normalize_project(project_root: Path, chapter_number: int) -> StructuredChapter:
    config = load_project_config(project_root)
    structure = read_json(project_root / "intermediate" / "ebook-structure.json")
    boundary = next((item for item in structure.get("chapters", []) if item.get("chapter_number") == chapter_number), None)
    if boundary is None:
        from .chapter_detect import detect_chapter
        boundary = detect_chapter(project_root, chapter_number)
    pages = [json.loads(line) for line in (project_root / "intermediate" / "ebook-pages.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    overrides = chapter_overrides(read_yaml(project_root / ".ebook-translation" / "paragraph-overrides.yaml"), chapter_number)
    pdf_path = project_root / "source" / "original.pdf"
    layout_pages = extract_pdf_layout_pages(pdf_path, pages, int(boundary["pdf_start"]), int(boundary["pdf_end"])) if pdf_path.exists() else pages
    blocks = normalize_page_records(layout_pages, int(boundary["pdf_start"]), int(boundary["pdf_end"]), overrides)
    title_en = re.sub(r"^\s*\d+\s*[.:]\s*", "", str(boundary.get("title", ""))).strip()
    progress_path = project_root / "reports" / "BOOK_TRANSLATION_PROGRESS.json"
    progress_item = None
    if progress_path.exists():
        progress = read_json(progress_path)
        progress_item = next((item for item in progress.get("chapters", []) if int(item.get("number", 0)) == chapter_number), None)
    chapter_meta = {
        "number": chapter_number,
        "title_en": title_en,
        "title_zh": (progress_item or {}).get("title_zh", ""),
        "pdf_start": boundary["pdf_start"],
        "pdf_end": boundary["pdf_end"],
        "printed_start": boundary.get("printed_start", ""),
        "printed_end": boundary.get("printed_end", ""),
    }
    chapter = StructuredChapter(
        book=config.get("book", {}),
        chapter=chapter_meta,
        blocks=blocks,
        page_anchors=[anchor for block in blocks for anchor in block.page_anchors],
    )
    stem = f"chapter-{chapter_number:02d}"
    write_json(chapter_json_path(project_root, chapter_number, "source"), chapter.to_dict())
    return chapter
