import json
import tempfile
import unittest
from pathlib import Path

import yaml

from ebook_translation_toolkit.models import StructuredChapter
from ebook_translation_toolkit.render_markdown import render_markdown


FIXTURE = Path(__file__).parent / "fixtures" / "cybernetic_brain_minimal.json"


class MarkdownRenderTests(unittest.TestCase):
    def test_markdown_uses_same_blocks_inline_anchors_and_footnotes(self):
        chapter = StructuredChapter.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))
        with tempfile.TemporaryDirectory() as directory:
            markdown = render_markdown(chapter, Path(directory) / "chapter.md")
        self.assertEqual(markdown.count("<!-- BLOCK_ID:"), 10)
        self.assertEqual(markdown.count("WITHIN_PARAGRAPH:"), 10)
        self.assertEqual(markdown.count("\n[^"), 7)
        self.assertIn("../../assets/chapter-01/figure-001.jpg", markdown)
        metadata = yaml.safe_load(markdown.split("---", 2)[1])
        self.assertEqual(metadata["translation_status"], "complete")

    def test_page_anchor_does_not_create_blank_paragraph(self):
        chapter = StructuredChapter.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))
        with tempfile.TemporaryDirectory() as directory:
            markdown = render_markdown(chapter, Path(directory) / "chapter.md")
        self.assertNotIn("\n\n<!-- PDF_PAGE:", markdown)


if __name__ == "__main__":
    unittest.main()
