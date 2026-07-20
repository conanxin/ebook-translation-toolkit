import unittest

from ebook_translation_toolkit.image_anchors import anchor_images, find_caption_groups
from ebook_translation_toolkit.models import Block, ImageAsset


class ImageAnchorTests(unittest.TestCase):
    def test_caption_group_collects_wrapped_caption_blocks(self):
        blocks = [
            Block("b-001", type="attribution", source_text="Figure 4.1. A machine.", source_pdf_page_start=10, source_pdf_page_end=10),
            Block("b-002", type="blockquote", source_text="Source: Archive.", source_pdf_page_start=10, source_pdf_page_end=10),
            Block("p-001", source_text="Body.", source_pdf_page_start=10, source_pdf_page_end=10),
        ]
        groups = find_caption_groups(blocks, 4)
        self.assertEqual(groups[0]["number"], 1)
        self.assertEqual(groups[0]["block_ids"], ["b-001", "b-002"])
        self.assertEqual(groups[0]["caption"], "Figure 4.1. A machine. Source: Archive.")

    def test_caption_group_accepts_leading_panel_labels(self):
        blocks = [
            Block(
                "b-001",
                type="attribution",
                source_text="A B Figure 6.11. Control systems: A, body; B, firm.",
                source_pdf_page_start=256,
                source_pdf_page_end=256,
            )
        ]
        groups = find_caption_groups(blocks, 6)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["number"], 11)
        self.assertEqual(groups[0]["block_ids"], ["b-001"])


    def test_image_is_anchored_after_complete_block(self):
        blocks = [Block("p-001", source_pdf_page_start=12, source_pdf_page_end=13), Block("p-002", source_pdf_page_start=14, source_pdf_page_end=14)]
        image = ImageAsset("figure-001", "assets/figure.jpg", 13)
        anchor_images(blocks, [image])
        self.assertEqual(image.after_block_id, "p-001")
        self.assertEqual(blocks[0].image_after, ["figure-001"])

    def test_top_image_inside_cross_page_paragraph_follows_complete_paragraph(self):
        blocks = [
            Block("h-001", type="heading", source_text="Title", source_pdf_page_start=1, source_pdf_page_end=1),
            Block("p-001", source_text="Paragraph spanning the figure page.", source_pdf_page_start=1, source_pdf_page_end=2),
        ]
        image = ImageAsset("figure-001", "assets/figure.png", 2, bbox=[10, 60, 200, 180])
        anchor_images(blocks, [image])
        self.assertEqual(image.after_block_id, "p-001")

    def test_override_is_honored(self):
        blocks = [Block("p-001"), Block("p-002")]
        image = ImageAsset("figure-002", "assets/figure.jpg", 1)
        anchor_images(blocks, [image], {"anchors": {"figure-002": "p-002"}})
        self.assertEqual(image.after_block_id, "p-002")

    def test_duplicate_image_is_rejected(self):
        with self.assertRaises(ValueError):
            anchor_images([Block("p-001")], [ImageAsset("f", "a", 1), ImageAsset("f", "b", 2)])


if __name__ == "__main__":
    unittest.main()
