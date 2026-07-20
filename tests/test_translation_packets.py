import unittest

from ebook_translation_toolkit.models import Block, FootnoteRef, PageAnchor
from ebook_translation_toolkit.translation_packets import marked_source_text


class TranslationPacketTests(unittest.TestCase):
    def test_marked_text_carries_internal_page_and_footnote_tokens(self):
        block = Block(
            block_id="p-001",
            source_text="Alpha beta gamma.",
            page_anchors=[PageAnchor(13, "2", 6, "p-001")],
            footnote_refs=[FootnoteRef(4, 10)],
        )
        self.assertEqual(
            marked_source_text(block),
            "Alpha [[PAGE:13|2]]beta[[FN:4]] gamma.",
        )


if __name__ == "__main__":
    unittest.main()
