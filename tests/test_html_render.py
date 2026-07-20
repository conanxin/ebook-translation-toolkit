import json
import re
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from ebook_translation_toolkit.models import Block, Footnote, FootnoteRef, PageAnchor, StructuredChapter
from ebook_translation_toolkit.render_html import render_html


FIXTURE = Path(__file__).parent / "fixtures" / "cybernetic_brain_minimal.json"


class HtmlRenderTests(unittest.TestCase):
    def setUp(self):
        self.chapter = StructuredChapter.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))

    def test_offline_inline_footnotes_and_no_italics(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "chapter.html"
            html = render_html(self.chapter, output)
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(len(soup.select("button.footnote-trigger")), 7)
        self.assertEqual(len(soup.select("template[id^='footnote-template-']")), 7)
        self.assertIsNotNone(soup.select_one("aside[role='note']"))
        self.assertFalse(soup.select("ol.footnotes, .notes-page, section.footnotes"))
        self.assertIsNone(soup.find("em"))
        self.assertIsNone(soup.find("i"))
        self.assertIsNone(re.search(r"font-style\s*:\s*italic", html, re.I))
        self.assertNotRegex(html, r"(?:https?:)?//")
        self.assertIn("Escape", html)
        self.assertIn("aria-expanded", html)
        self.assertIn('.footnote-trigger[aria-expanded="true"] { position:relative; z-index:110; }', html)
        self.assertIn("width:auto !important", html)

    def test_ten_cross_page_blocks_are_single_dom_paragraphs(self):
        with tempfile.TemporaryDirectory() as directory:
            html = render_html(self.chapter, Path(directory) / "chapter.html")
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(len(soup.select("p[data-block-id]")), 10)
        self.assertEqual(len(soup.select("span.page-anchor[data-within-paragraph]")), 10)
        for anchor in soup.select("span.page-anchor"):
            self.assertIsNotNone(anchor.find_parent("p"))

    def test_images_follow_their_complete_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            soup = BeautifulSoup(render_html(self.chapter, Path(directory) / "chapter.html"), "html.parser")
        for image_id, block_id in (("figure-001", "p-001"), ("figure-002", "p-005")):
            block = soup.select_one(f'[data-block-id="{block_id}"]')
            figure = soup.select_one(f'figure[data-image-id="{image_id}"]')
            self.assertIsNotNone(figure)
            self.assertLess(str(soup).index(str(block)), str(soup).index(str(figure)))

    def test_translated_inline_markers_render_without_leaking(self):
        chapter = StructuredChapter(
            {"title": "Book", "author": "Author"},
            {"number": 2, "title_en": "Two", "title_zh": "第二章"},
            [Block("p-001", source_text="Source.1", translated_text="译文[[PAGE:3|2]]继续。[[FN:1]]", source_pdf_page_start=2, source_pdf_page_end=3, page_anchors=[PageAnchor(3, "2", 7, "p-001")], footnote_refs=[FootnoteRef(1, 7)])],
            footnotes=[Footnote(1, "Source note", "中文注释", "p-001")],
        )
        with tempfile.TemporaryDirectory() as directory:
            html = render_html(chapter, Path(directory) / "chapter.html")
        self.assertNotIn("[[PAGE:", html)
        self.assertNotIn("[[FN:", html)
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(soup.select_one(".page-anchor")["data-pdf-page"], "3")
        self.assertEqual(soup.select_one(".footnote-trigger")["data-footnote"], "1")


if __name__ == "__main__":
    unittest.main()
