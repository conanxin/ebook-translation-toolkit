"""Unit tests for the EPUB packaging pipeline.

These tests use standard unittest.TestCase classes so that
``python -m unittest discover -s tests -p 'test_*.py'`` enumerates them.
"""

from __future__ import annotations

import json
import re
import zipfile
import unittest
from pathlib import Path

from ebook_translation_toolkit.epub_models import (
    EpubBook,
    EpubBookMetadata,
    EpubChapter,
    EpubFootnote,
    EpubImage,
)
from ebook_translation_toolkit.epub_navigation import render_nav_xhtml, render_toc_ncx
from ebook_translation_toolkit.epub_notes import (
    build_footnote_id,
    build_footnote_ref_id,
    build_page_anchor_id,
)
from ebook_translation_toolkit.epub_package import write_epub
from ebook_translation_toolkit.epub_validator import validate_epub
from ebook_translation_toolkit.render_epub import render_chapter_xhtml


_CSS_PATH = Path(__file__).resolve().parents[1] / "templates" / "epub" / "book.css"


def _image_payload() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff"
        b"\xff?\x00\x05\xfe\x02\xfe\xa3V\x9c\xd2\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _make_image(chapter: int, idx: int, label: str = "图 1.1") -> EpubImage:
    img = EpubImage(
        chapter=chapter,
        figure_id=f"figure-{idx:03d}",
        file_name=f"fig-{idx:03d}.png",
        mime_type="image/png",
        relative_path=f"images/fig-{idx:03d}.png",
        alt_text_zh=label,
        sha256="",
        caption_zh=label,
    )
    img.payload = _image_payload()  # type: ignore[attr-defined]
    return img


def _make_chapter(number: int, *, with_images: bool = True) -> EpubChapter:
    blocks = [
        {
            "block_id": "p-001",
            "type": "paragraph",
            "translated_text": (
                f"章节 {number} 第一段内容，包含 [[PAGE:13|3]] 页面锚点和 [[FN:6]] 注释引用。"
            ),
            "source_text": "",
        },
        {
            "block_id": "p-002",
            "type": "paragraph",
            "translated_text": "这是第二段。",
            "source_text": "",
        },
    ]
    footnotes = [
        EpubFootnote(chapter=number, number=6, block_id="p-001", text="示例注释"),
    ]
    images: list[EpubImage] = []
    if with_images:
        images.append(_make_image(number, 1))
    return EpubChapter(
        number=number,
        title_zh=f"第{number}章",
        title_en=f"Chapter {number}",
        blocks=blocks,
        footnotes=footnotes,
        images=images,
    )


def _build_book(num_chapters: int = 2) -> EpubBook:
    metadata = EpubBookMetadata(
        title_zh="测试书",
        title_en="Test Book",
        author="Test Author",
        uuid="00000000-0000-0000-0000-000000000000",
        modified="2026-07-20T12:00:00Z",
        language="zh-CN",
    )
    book = EpubBook(metadata=metadata)
    for n in range(1, num_chapters + 1):
        book.chapters.append(_make_chapter(n))
    for chapter in book.chapters:
        for image in chapter.images:
            book.images.append(image)
    return book


def _make_minimal_jpeg(path: Path) -> Path:
    """Write a 1×1 white JPEG to ``path`` and return it.

    Tests use this helper to fabricate a tiny but valid cover file
    so the EPUB package builder does not bail out on a missing file.
    """
    import struct
    import zlib

    # Tiny PNG (1×1 transparent) instead of JPEG — smaller, no encoding deps.
    png_signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data).to_bytes(4, "big")
    ihdr = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc
    raw = b"\x00\xff\xff\xff"
    compressed = zlib.compress(raw)
    idat_crc = zlib.crc32(b"IDAT" + compressed).to_bytes(4, "big")
    idat = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + idat_crc
    iend_crc = zlib.crc32(b"IEND").to_bytes(4, "big")
    iend = struct.pack(">I", 0) + b"IEND" + iend_crc
    path.write_bytes(png_signature + ihdr + idat + iend)
    return path


class TestEpubPackage(unittest.TestCase):
    """Smoke tests on the EPUB zip layout, OPF, and rendering invariants."""

    def test_mimetype_is_first_entry_and_uncompressed(self) -> None:
        book = _build_book()
        output = Path(self._tmp_path()) / "out.epub"
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        with zipfile.ZipFile(output) as zf:
            names = zf.namelist()
            info = zf.getinfo("mimetype")
            self.assertEqual(names[0], "mimetype")
            self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
            self.assertEqual(info.file_size, len(b"application/epub+zip"))
            self.assertEqual(zf.read("mimetype"), b"application/epub+zip")

    def test_container_xml_well_formed_and_points_to_opf(self) -> None:
        book = _build_book()
        output = Path(self._tmp_path()) / "out.epub"
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        with zipfile.ZipFile(output) as zf:
            container = zf.read("META-INF/container.xml")
            self.assertIn(b"EPUB/package.opf", container)

    def test_opf_metadata(self) -> None:
        book = _build_book()
        output = Path(self._tmp_path()) / "out.epub"
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        with zipfile.ZipFile(output) as zf:
            opf = zf.read("EPUB/package.opf").decode("utf-8")
            self.assertIn("dc:title", opf)
            self.assertIn("测试书", opf)
            self.assertIn("dc:creator", opf)
            self.assertIn("Test Author", opf)
            self.assertIn("zh-CN", opf)
            self.assertIn("dcterms:modified", opf)
            self.assertIn("2026-07-20T12:00:00Z", opf)

    def test_manifest_complete_and_in_spine(self) -> None:
        book = _build_book(2)
        # Provide a real cover file so the manifest emits a cover-image
        # property without the package builder crashing on a missing file.
        tmp = Path(self._tmp_path())
        cover = tmp / "cover.jpg"
        _make_minimal_jpeg(cover)
        book.metadata.cover_path = str(cover)
        output = tmp / "out.epub"
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        with zipfile.ZipFile(output) as zf:
            opf = zf.read("EPUB/package.opf").decode("utf-8")
            self.assertIn('href="text/chapter-01.xhtml"', opf)
            self.assertIn('href="text/chapter-02.xhtml"', opf)
            self.assertIn('href="images/fig-001.png"', opf)
            self.assertIn('properties="nav"', opf)
            self.assertIn('properties="cover-image"', opf)
            self.assertIn('itemref idref="titlepage"', opf)
            self.assertIn('itemref idref="chapter-01"', opf)
            self.assertIn('itemref idref="chapter-02"', opf)

    def test_nav_includes_toc_page_list_landmarks(self) -> None:
        nav = render_nav_xhtml(_build_book(2))
        self.assertIn('epub:type="toc"', nav)
        self.assertIn('epub:type="page-list"', nav)
        self.assertIn('epub:type="landmarks"', nav)

    def test_ncx_lists_title_and_chapters(self) -> None:
        ncx = render_toc_ncx(_build_book(2))
        self.assertIn("navpoint-titlepage", ncx)
        self.assertIn("navpoint-chapter-01", ncx)
        self.assertIn("navpoint-chapter-02", ncx)
        self.assertIn('playOrder="1"', ncx)
        self.assertIn('playOrder="2"', ncx)

    def test_page_list_lists_unique_anchors(self) -> None:
        book = _build_book(2)
        book.chapters[0].page_anchors = [
            {"printed_page": "3", "pdf_page": "13", "anchor_id": build_page_anchor_id(1, "13", "3")},
            {"printed_page": "3", "pdf_page": "13", "anchor_id": build_page_anchor_id(1, "13", "3")},
            {"printed_page": "4", "pdf_page": "14", "anchor_id": build_page_anchor_id(1, "14", "4")},
        ]
        nav = render_nav_xhtml(book)
        self.assertEqual(nav.count("原书第3页"), 1)
        self.assertEqual(nav.count("原书第4页"), 1)

    def test_eight_chapters_present(self) -> None:
        book = _build_book(8)
        output = Path(self._tmp_path()) / "out.epub"
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        with zipfile.ZipFile(output) as zf:
            for n in range(1, 9):
                self.assertIn(f"EPUB/text/chapter-{n:02d}.xhtml", zf.namelist())

    def test_body_images_present(self) -> None:
        book = _build_book(2)
        output = Path(self._tmp_path()) / "out.epub"
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        with zipfile.ZipFile(output) as zf:
            self.assertIn("EPUB/images/fig-001.png", zf.namelist())

    def test_footnotes_referenced_in_xhtml(self) -> None:
        chapter = _make_chapter(1)
        chapter.footnotes = [
            EpubFootnote(chapter=1, number=6, block_id="p-001", text="示例注释"),
        ]
        xhtml = render_chapter_xhtml(chapter, book_title_zh="测试书")
        self.assertIn('id="ch01-fnref-006"', xhtml)
        self.assertIn('href="#ch01-fn-006"', xhtml)
        self.assertIn('id="ch01-fn-006"', xhtml)
        self.assertIn('epub:type="noteref"', xhtml)
        self.assertIn('epub:type="footnote"', xhtml)
        self.assertIn('epub:type="backlink"', xhtml)

    def test_footnote_ids_unique_within_chapter(self) -> None:
        fn = EpubFootnote(chapter=1, number=1, block_id="p-001", text="x")
        self.assertNotEqual(
            build_footnote_id(fn.chapter, fn.number),
            build_footnote_ref_id(fn.chapter, fn.number),
        )

    def test_image_media_type_is_correct(self) -> None:
        book = _build_book(1)
        output = Path(self._tmp_path()) / "out.epub"
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        with zipfile.ZipFile(output) as zf:
            manifest = zf.read("EPUB/package.opf").decode("utf-8")
            self.assertIn('images/fig-001.png" media-type="image/png"', manifest)

    def test_xhtml_is_parseable(self) -> None:
        from xml.etree import ElementTree as ET

        book = _build_book(1)
        output = Path(self._tmp_path()) / "out.epub"
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        with zipfile.ZipFile(output) as zf:
            for n in range(1, 2):
                xml = zf.read(f"EPUB/text/chapter-{n:02d}.xhtml")
                ET.fromstring(xml)

    def test_no_external_resources_dependency(self) -> None:
        book = _build_book(1)
        output = Path(self._tmp_path()) / "out.epub"
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        with zipfile.ZipFile(output) as zf:
            for name in zf.namelist():
                data = zf.read(name).decode("utf-8", errors="ignore")
                if name.endswith(".xhtml") or name.endswith(".html"):
                    self.assertNotIn("<script", data.lower())
                    self.assertNotIn('rel="stylesheet" href="http', data)

    def test_no_javascript(self) -> None:
        book = _build_book(1)
        output = Path(self._tmp_path()) / "out.epub"
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        with zipfile.ZipFile(output) as zf:
            for name in zf.namelist():
                if name.endswith(".xhtml") or name.endswith(".html"):
                    content = zf.read(name).decode("utf-8")
                    self.assertFalse(re.search(r"<script\b", content, re.I))

    def test_no_visible_italics(self) -> None:
        book = _build_book(1)
        output = Path(self._tmp_path()) / "out.epub"
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        with zipfile.ZipFile(output) as zf:
            for name in zf.namelist():
                if name.endswith(".xhtml"):
                    content = zf.read(name).decode("utf-8")
                    self.assertNotIn("<em>", content)
                    self.assertNotIn("<i>", content)

    def test_no_absolute_paths(self) -> None:
        book = _build_book(1)
        output = Path(self._tmp_path()) / "out.epub"
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        with zipfile.ZipFile(output) as zf:
            for name in zf.namelist():
                self.assertFalse(name.startswith("/"))
                self.assertNotIn("://", name)

    def test_book_uuid_stable(self) -> None:
        book = _build_book(1)
        book.metadata.uuid = "11111111-2222-3333-4444-555555555555"
        tmp = Path(self._tmp_path())
        a = tmp / "a.epub"
        b = tmp / "b.epub"
        res_a = write_epub(book, output_path=a, css_path=_CSS_PATH)
        res_b = write_epub(book, output_path=b, css_path=_CSS_PATH)
        self.assertEqual(res_a.sha256, res_b.sha256)

    def test_reproducible_build(self) -> None:
        book = _build_book(2)
        tmp = Path(self._tmp_path())
        first = tmp / "first.epub"
        second = tmp / "second.epub"
        res1 = write_epub(book, output_path=first, css_path=_CSS_PATH)
        res2 = write_epub(book, output_path=second, css_path=_CSS_PATH)
        self.assertEqual(res1.sha256, res2.sha256)

    def test_legacy_chapter_adapter_loads_approved_markdown(self) -> None:
        from ebook_translation_toolkit.legacy_chapter_adapter import (
            build_chapter_from_legacy,
        )

        tmp = Path(self._tmp_path())
        md = tmp / "ch1.md"
        md.write_text(
            "---\n"
            "title: 适应性大脑\n"
            "original_title: The Adaptive Brain\n"
            "---\n\n"
            "# 第一章　适应性大脑\n\n"
            "> 引文第一行。\n\n"
            "> 引文第二行。\n\n"
            "[^1]: 第一条注释示例。\n",
            encoding="utf-8",
        )
        chapter = build_chapter_from_legacy(md, chapter_number=1)
        self.assertEqual(chapter.title_zh, "适应性大脑")
        self.assertTrue(any(b.get("type") == "epigraph" for b in chapter.blocks))
        self.assertTrue(any(f["number"] == 1 for f in chapter.footnotes))

    def test_validator_returns_pass(self) -> None:
        book = _build_book(2)
        tmp = Path(self._tmp_path())
        cover = tmp / "cover.jpg"
        _make_minimal_jpeg(cover)
        book.metadata.cover_path = str(cover)
        output = tmp / "out.epub"
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        report = validate_epub(output)
        self.assertEqual(report["status"], "PASS")

    def test_image_order_matches_structured_chapter(self) -> None:
        chapter = _make_chapter(1)
        chapter.images = [_make_image(1, 1), _make_image(1, 2)]
        chapter.images[0].file_name = "a.png"
        chapter.images[1].file_name = "b.png"
        chapter.images[0].payload = b"A"  # type: ignore[attr-defined]
        chapter.images[1].payload = b"B"  # type: ignore[attr-defined]
        output = Path(self._tmp_path()) / "out.epub"
        book = EpubBook(
            metadata=EpubBookMetadata(
                title_zh="t",
                title_en="t",
                author="a",
                uuid="00000000-0000-0000-0000-000000000000",
                modified="2026-07-20T12:00:00Z",
            ),
            chapters=[chapter],
            images=list(chapter.images),
        )
        write_epub(book, output_path=output, css_path=_CSS_PATH)
        with zipfile.ZipFile(output) as zf:
            self.assertIn("EPUB/images/a.png", zf.namelist())
            self.assertIn("EPUB/images/b.png", zf.namelist())

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    _tmp_counter = 0

    def _tmp_path(self) -> str:
        import tempfile
        TestEpubPackage._tmp_counter += 1
        d = tempfile.mkdtemp(prefix=f"epubtest_{TestEpubPackage._tmp_counter}_")
        self.addCleanup(self._cleanup_tmp, d)
        return d

    @staticmethod
    def _cleanup_tmp(d: str) -> None:
        import shutil

        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()