from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class PageAnchor:
    pdf_page: int
    printed_page: str = ""
    offset: int = 0
    within_block: str = ""


@dataclass(slots=True)
class FootnoteRef:
    number: int
    offset: int


@dataclass(slots=True)
class Block:
    block_id: str
    type: str = "paragraph"
    source_text: str = ""
    translated_text: str = ""
    source_pdf_page_start: int = 0
    source_pdf_page_end: int = 0
    printed_page_start: str = ""
    printed_page_end: str = ""
    page_anchors: list[PageAnchor] = field(default_factory=list)
    image_after: list[str] = field(default_factory=list)
    footnote_refs: list[FootnoteRef] = field(default_factory=list)
    styles: list[str] = field(default_factory=list)
    reading_order: int = 0

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Block":
        value = dict(value)
        value["page_anchors"] = [PageAnchor(**item) for item in value.get("page_anchors", [])]
        value["footnote_refs"] = [FootnoteRef(**item) for item in value.get("footnote_refs", [])]
        return cls(**value)


@dataclass(slots=True)
class ImageAsset:
    image_id: str
    path: str
    pdf_page: int
    bbox: list[float] = field(default_factory=list)
    caption_source: str = ""
    caption_zh: str = ""
    sha256: str = ""
    after_block_id: str = ""


@dataclass(slots=True)
class Footnote:
    number: int
    source_text: str = ""
    translated_text: str = ""
    block_id: str = ""


@dataclass(slots=True)
class Term:
    english: str
    chinese: str
    category: str = "TECHNICAL_TERM"
    first_block_id: str = ""
    notes: str = ""


@dataclass(slots=True)
class StructuredChapter:
    book: dict[str, Any]
    chapter: dict[str, Any]
    blocks: list[Block]
    images: list[ImageAsset] = field(default_factory=list)
    footnotes: list[Footnote] = field(default_factory=list)
    terms: list[Term] = field(default_factory=list)
    page_anchors: list[PageAnchor] = field(default_factory=list)
    schema_version: str = "0.1.0"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "StructuredChapter":
        return cls(
            book=value.get("book", {}),
            chapter=value.get("chapter", {}),
            blocks=[Block.from_dict(item) for item in value.get("blocks", [])],
            images=[ImageAsset(**item) for item in value.get("images", [])],
            footnotes=[Footnote(**item) for item in value.get("footnotes", [])],
            terms=[Term(**item) for item in value.get("terms", [])],
            page_anchors=[PageAnchor(**item) for item in value.get("page_anchors", [])],
            schema_version=value.get("schema_version", "0.1.0"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def validate(self) -> list[str]:
        errors: list[str] = []
        ids = [block.block_id for block in self.blocks]
        if len(ids) != len(set(ids)):
            errors.append("duplicate block_id")
        paragraphs = [block.block_id for block in self.blocks if block.type == "paragraph"]
        if any(not item.startswith("p-") for item in paragraphs):
            errors.append("paragraph block_id must start with p-")
        image_ids = {image.image_id for image in self.images}
        for block in self.blocks:
            if block.source_pdf_page_end < block.source_pdf_page_start:
                errors.append(f"invalid page range: {block.block_id}")
            if set(block.image_after) - image_ids:
                errors.append(f"unknown image reference: {block.block_id}")
            for anchor in block.page_anchors:
                if anchor.within_block and anchor.within_block != block.block_id:
                    errors.append(f"page anchor misbound: {block.block_id}")
        return errors
