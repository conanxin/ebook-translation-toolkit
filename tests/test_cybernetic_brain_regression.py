import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from ebook_translation_toolkit.models import StructuredChapter
from ebook_translation_toolkit.render_html import render_html
from ebook_translation_toolkit.render_markdown import render_markdown
from ebook_translation_toolkit.utils import sha256_file


FIXTURES = Path(__file__).parent / "fixtures"
# These paths intentionally reference machine-local destinations for the
# reference book project.  They are only used by @unittest.skipUnless
# guards; they are intentionally parameterized via environment variables
# in a CI / fork environment and otherwise fall through to skip.
CURRENT = Path(
    os.environ.get(
        "EBOOK_REFERENCE_PROJECT",
        r"D:\home\conanxin\workspace\ebook-first-chapter-cn\the-cybernetic-brain",
    )
)
VAULT = Path(
    os.environ.get(
        "EBOOK_REFERENCE_VAULT",
        r"D:\OBSIDIAN_NOV\conanxin\_Agent\Outputs\Book-Translations\the-cybernetic-brain",
    )
)


class CyberneticBrainRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = StructuredChapter.from_dict(json.loads((FIXTURES / "cybernetic_brain_minimal.json").read_text(encoding="utf-8")))
        cls.baseline = json.loads((FIXTURES / "current_project_baseline.json").read_text(encoding="utf-8"))

    def test_ten_cross_page_merge_rules(self):
        merged = [block for block in self.fixture.blocks if block.source_pdf_page_end > block.source_pdf_page_start]
        self.assertEqual(len(merged), 10)
        self.assertTrue(all(len(block.page_anchors) == 1 for block in merged))

    def test_fixture_render_has_identical_block_order(self):
        with tempfile.TemporaryDirectory() as directory:
            html = render_html(self.fixture, Path(directory) / "chapter.html")
            markdown = render_markdown(self.fixture, Path(directory) / "chapter.md")
        html_ids = re.findall(r'data-block-id="([^"]+)"', html)
        markdown_ids = re.findall(r"<!-- BLOCK_ID: ([^ ]+) -->", markdown)
        self.assertEqual(html_ids, markdown_ids)

    @unittest.skipUnless(CURRENT.exists(), "current project is not available")
    def test_current_outputs_are_frozen(self):
        self.assertEqual(sha256_file(CURRENT / "output/html/chapter-01-zh.html"), self.baseline["html_sha256"])
        self.assertEqual(sha256_file(CURRENT / "output/markdown/chapter-01-zh.md"), self.baseline["markdown_sha256"])
        self.assertEqual(sha256_file(VAULT / "第一章-适应性大脑.md"), self.baseline["obsidian_markdown_sha256"])

    @unittest.skipUnless(CURRENT.exists(), "current project is not available")
    def test_current_footnotes_images_and_italic_rules(self):
        html = (CURRENT / "output/html/chapter-01-zh.html").read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual([int(item["data-footnote"]) for item in soup.select("button.footnote-trigger")], list(range(1, 8)))
        self.assertEqual(len(soup.select("template[id^='footnote-template-']")), 7)
        self.assertFalse(soup.select("ol.footnotes, .notes-page, section.footnotes"))
        self.assertIsNone(soup.find("em"))
        self.assertIsNone(soup.find("i"))
        self.assertNotRegex(html, r"font-style\s*:\s*italic")
        for name in ("figure-001.jpg", "figure-002.jpg"):
            image = soup.select_one(f'img[src$="{name}"]')
            self.assertIsNotNone(image)
            previous = image.parent.find_previous("p")
            self.assertIsNotNone(previous)
            self.assertRegex(previous.get_text(strip=True), r"[。！？）》）]$")

    @unittest.skipUnless(CURRENT.exists(), "current project is not available")
    def test_current_internal_anchors_terms_and_asset_hashes(self):
        html = (CURRENT / "output/html/chapter-01-zh.html").read_text(encoding="utf-8")
        anchors = [int(value) for value in re.findall(r'class="pdf-page-marker" data-pdf-page="(\d+)"', html)]
        self.assertEqual(anchors, self.baseline["internal_page_anchors"])
        combined = (CURRENT / "output/markdown/chapter-01-zh.md").read_text(encoding="utf-8") + (CURRENT / "intermediate/translation-glossary.md").read_text(encoding="utf-8")
        for term in self.baseline["bilingual_terms"]:
            self.assertIn(term, combined)
        for name, digest in self.baseline["images"].items():
            self.assertEqual(sha256_file(CURRENT / "assets/chapter-01" / name), digest)
            self.assertEqual(sha256_file(VAULT / "assets" / name), digest)

    @unittest.skipUnless(CURRENT.exists(), "current project is not available")
    def test_project_and_obsidian_markdown_are_equivalent(self):
        project = (CURRENT / "output/markdown/chapter-01-zh.md").read_text(encoding="utf-8").replace("../../assets/chapter-01/", "assets/")
        obsidian = (VAULT / "第一章-适应性大脑.md").read_text(encoding="utf-8")
        self.assertEqual(project, obsidian)


if __name__ == "__main__":
    unittest.main()
