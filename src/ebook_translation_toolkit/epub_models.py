from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EpubBookMetadata:
    title_zh: str
    title_en: str
    author: str
    language: str = "zh-CN"
    uuid: str = ""
    modified: str = ""
    source_pdf: str = ""
    cover_path: str = ""


@dataclass
class EpubChapter:
    number: int
    title_zh: str
    title_en: str
    blocks: list[dict[str, Any]] = field(default_factory=list)
    footnotes: list[dict[str, Any]] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)
    page_anchors: list[dict[str, Any]] = field(default_factory=list)
    subsections: list[dict[str, Any]] = field(default_factory=list)
    source_path: str = ""


@dataclass
class EpubImage:
    chapter: int
    figure_id: str
    file_name: str
    mime_type: str
    relative_path: str
    alt_text_zh: str
    sha256: str
    caption_zh: str = ""


@dataclass
class EpubFootnote:
    chapter: int
    number: int
    block_id: str
    text: str


@dataclass
class EpubBook:
    metadata: EpubBookMetadata
    chapters: list[EpubChapter] = field(default_factory=list)
    images: list[EpubImage] = field(default_factory=list)
    footnotes: list[EpubFootnote] = field(default_factory=list)
    page_anchors: list[dict[str, Any]] = field(default_factory=list)

    def body_image_count(self) -> int:
        return len(self.images)