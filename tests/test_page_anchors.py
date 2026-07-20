import unittest

from ebook_translation_toolkit.models import Block, PageAnchor
from ebook_translation_toolkit.page_anchors import build_page_anchors, html_anchor, markdown_anchor


class PageAnchorTests(unittest.TestCase):
    def test_anchor_is_inline_and_bound(self):
        block = Block("p-012", source_pdf_page_start=12, source_pdf_page_end=13, page_anchors=[PageAnchor(13, "2", 12)])
        anchors = build_page_anchors([block])
        self.assertEqual(anchors[0].within_block, "p-012")
        self.assertNotIn("<p", html_anchor(anchors[0]))
        self.assertIn('data-within-paragraph="p-012"', html_anchor(anchors[0]))

    def test_markdown_anchor_has_no_blank_lines(self):
        marker = markdown_anchor(PageAnchor(13, "2", 5, "p-012"))
        self.assertNotIn("\n", marker)
        self.assertIn("WITHIN_PARAGRAPH: p-012", marker)


if __name__ == "__main__":
    unittest.main()
