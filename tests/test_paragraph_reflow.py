import unittest

from ebook_translation_toolkit.models import Block, FootnoteRef
from ebook_translation_toolkit.paragraph_reflow import group_layout_lines, normalize_page_records, normalize_semantic_blocks, should_merge


class ParagraphReflowTests(unittest.TestCase):
    def test_wrapped_indented_quote_is_one_group_with_internal_paragraph_break(self):
        def line(text, x, y):
            return {"text": text, "bbox": [x, y, 300, y + 9], "font_size": 9.2, "type": "paragraph"}

        lines = [
            line("Body continuation.", 63, 60),
            line("Quote first line", 75, 90),
            line("quote wrapped line", 75, 101),
            line("Quote second paragraph", 87, 112),
            line("second paragraph wrapped", 75, 123),
            line("Author resumes.", 63, 150),
        ]
        groups = group_layout_lines(lines, 63)
        self.assertEqual([[item["text"] for item in group] for group in groups], [
            ["Body continuation."],
            ["Quote first line", "quote wrapped line"],
            ["Quote second paragraph", "second paragraph wrapped"],
            ["Author resumes."],
        ])

    def test_dedent_from_quote_to_body_starts_new_group(self):
        def line(text, x, y):
            return {"text": text, "bbox": [x, y, 300, y + 9], "font_size": 9.2, "type": "paragraph"}

        groups = group_layout_lines([
            line("Quoted first line", 81, 90),
            line("quoted ending.", 81, 100),
            line("Author resumes without a large gap.", 69, 110),
        ], 69)
        self.assertEqual(len(groups), 2)

    def test_normal_first_line_indent_wraps_to_body_margin(self):
        def line(text, x, y):
            return {"text": text, "bbox": [x, y, 300, y + 9], "font_size": 9.2, "type": "paragraph"}

        groups = group_layout_lines([
            line("Indented first line", 75, 100),
            line("wrapped at the body margin.", 63, 110),
        ], 63)
        self.assertEqual(len(groups), 1)

    def test_cross_page_blockquote_continuation_merges(self):
        pages = [
            {"page_index": 1, "printed_page_number": "1", "blocks": [{"block_id": "q1", "text": "A quotation continues", "reading_order": 1, "block_type": "blockquote"}]},
            {"page_index": 2, "printed_page_number": "2", "blocks": [{"block_id": "q2", "text": "on the next page.", "reading_order": 1, "block_type": "blockquote"}]},
        ]
        blocks = normalize_page_records(pages, 1, 2)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].source_pdf_page_end, 2)

    def test_caption_fragment_does_not_swallow_next_page_quote(self):
        pages = [
            {"page_index": 1, "printed_page_number": "1", "blocks": [
                {"block_id": "q", "text": "Quoted words and", "reading_order": 1, "block_type": "blockquote"},
                {"block_id": "c1", "text": "Figure 4.1. Time moves down", "reading_order": 2, "block_type": "attribution"},
                {"block_id": "c2", "text": "ward through the image", "reading_order": 3, "block_type": "blockquote"},
            ]},
            {"page_index": 2, "printed_page_number": "2", "blocks": [
                {"block_id": "q2", "text": "that is the conclusion.", "reading_order": 1, "block_type": "blockquote"},
            ]},
        ]
        blocks = normalize_page_records(pages, 1, 2)
        caption = next(block for block in blocks if block.source_text.startswith("ward"))
        self.assertEqual(caption.source_pdf_page_end, 1)

    def test_unfinished_cross_page_sentence_merges(self):
        self.assertTrue(should_merge({"page": 1, "text": "This sentence is not"}, {"page": 2, "text": "finished yet."}))

    def test_finished_paragraph_does_not_merge(self):
        self.assertFalse(should_merge({"page": 1, "text": "This is complete."}, {"page": 2, "text": "Another paragraph begins."}))

    def test_finished_paragraph_before_capitalized_in_does_not_merge(self):
        self.assertFalse(should_merge({"page": 1, "text": "This is complete."}, {"page": 2, "text": "In 1956 a new paragraph begins."}))

    def test_uppercase_word_with_continuation_prefix_does_not_merge(self):
        self.assertFalse(should_merge({"page": 1, "text": "This is complete."}, {"page": 2, "text": "Ashby begins another paragraph."}))

    def test_normalization_is_idempotent(self):
        pages = [
            {"page_index": 1, "printed_page_number": "1", "blocks": [{"block_id": "r1", "text": "A continuing", "reading_order": 1, "block_type": "paragraph"}]},
            {"page_index": 2, "printed_page_number": "2", "blocks": [{"block_id": "r2", "text": "sentence ends.", "reading_order": 1, "block_type": "paragraph"}]},
        ]
        first = normalize_page_records(pages, 1, 2)
        second = normalize_page_records(pages, 1, 2)
        self.assertEqual([item.source_text for item in first], [item.source_text for item in second])
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].block_id, "p-001")
        self.assertEqual(first[0].page_anchors[0].within_block, "p-001")

    def test_footer_is_not_body(self):
        pages = [{"page_index": 1, "printed_page_number": "1", "blocks": [
            {"block_id": "p", "text": "Body.", "reading_order": 1, "block_type": "paragraph"},
            {"block_id": "f", "text": "1", "reading_order": 2, "block_type": "footer"},
        ]}]
        self.assertEqual(len(normalize_page_records(pages, 1, 1)), 1)

    def test_soft_hyphen_line_break_repairs_word(self):
        pages = [{"page_index": 1, "printed_page_number": "1", "blocks": [
            {"block_id": "p", "text": "work\u00ad\ning", "reading_order": 1, "block_type": "paragraph"},
        ]}]
        self.assertEqual(normalize_page_records(pages, 1, 1)[0].source_text, "working")

    def test_legacy_embedded_font_punctuation_is_repaired(self):
        pages = [{"page_index": 1, "printed_page_number": "1", "blocks": [
            {"block_id": "p", "text": "Ashby＊s ※machine§, 1903每1972〞later", "reading_order": 1, "block_type": "paragraph"},
        ]}]
        self.assertEqual(
            normalize_page_records(pages, 1, 1)[0].source_text,
            "Ashby’s “machine”, 1903–1972—later",
        )

    def test_layout_quote_paragraphs_with_distinct_ids_stay_separate(self):
        pages = [{"page_index": 1, "printed_page_number": "1", "blocks": [
            {"block_id": "p0001-layout-001", "text": "First quote paragraph.", "reading_order": 1, "block_type": "blockquote", "bbox": [75, 100, 300, 120]},
            {"block_id": "p0001-layout-002", "text": "Second quote paragraph.", "reading_order": 2, "block_type": "blockquote", "bbox": [87, 121, 300, 141]},
        ]}]
        blocks = normalize_page_records(pages, 1, 1)
        self.assertEqual([block.source_text for block in blocks], ["First quote paragraph.", "Second quote paragraph."])

    def test_courier_bold_section_label_is_retyped_as_heading(self):
        blocks = [Block(block_id="b-001", type="attribution", source_text="The Synthetic Brain")]
        repaired = normalize_semantic_blocks(blocks)
        self.assertEqual(repaired[0].type, "heading")

    def test_wrapped_bibliographic_attribution_is_merged(self):
        blocks = [
            Block(block_id="b-001", type="attribution", source_text="Norbert Wiener,"),
            Block(block_id="b-002", type="blockquote", source_text="The Human Use of Human Beings, 2nd ed."),
        ]
        repaired = normalize_semantic_blocks(blocks)
        self.assertEqual(len(repaired), 1)
        self.assertEqual(repaired[0].type, "attribution")
        self.assertIn("2nd ed.", repaired[0].source_text)

    def test_lowercase_chapter_subtitle_continuation_is_merged(self):
        blocks = [
            Block(block_id="b-001", type="heading", source_text="4"),
            Block(block_id="b-002", type="heading", source_text="ROSS ASHBY psychiatry, synthetic brains,"),
            Block(block_id="b-003", type="blockquote", source_text="and cybernetics"),
        ]
        repaired = normalize_semantic_blocks(blocks)
        self.assertEqual(len(repaired), 2)
        self.assertEqual(repaired[1].source_text, "ROSS ASHBY psychiatry, synthetic brains, and cybernetics")

    def test_semantic_cross_page_merge_preserves_anchor_and_footnote(self):
        blocks = [
            Block(block_id="p-001", source_text="A sentence continues", source_pdf_page_start=10,
                  source_pdf_page_end=10, printed_page_start="1", printed_page_end="1"),
            Block(block_id="p-002", source_text="on the next page.", source_pdf_page_start=11,
                  source_pdf_page_end=11, printed_page_start="2", printed_page_end="2",
                  footnote_refs=[FootnoteRef(1, 17)]),
        ]
        repaired = normalize_semantic_blocks(blocks)
        self.assertEqual(len(repaired), 1)
        self.assertEqual([anchor.pdf_page for anchor in repaired[0].page_anchors], [11])
        self.assertEqual(repaired[0].page_anchors[0].within_block, "p-001")
        self.assertEqual(repaired[0].footnote_refs[0].number, 1)
        self.assertGreater(repaired[0].footnote_refs[0].offset, 17)

    def test_override_splits_heading_from_cross_page_paragraph_and_retypes(self):
        pages = [
            {"page_index": 10, "printed_page_number": "1", "blocks": [
                {"block_id": "raw-1", "text": "archway The paragraph starts here and", "reading_order": 1,
                 "block_type": "paragraph", "bbox": [60, 100, 400, 140]},
            ]},
            {"page_index": 11, "printed_page_number": "2", "blocks": [
                {"block_id": "raw-2", "text": "continues on the next page.", "reading_order": 1,
                 "block_type": "paragraph", "bbox": [60, 100, 400, 140]},
            ]},
        ]
        overrides = {"split": [{"block": "p-001", "after": "archway", "left_type": "heading", "right_type": "paragraph"}]}

        blocks = normalize_page_records(pages, 10, 11, overrides)

        self.assertEqual([block.type for block in blocks], ["heading", "paragraph"])
        self.assertEqual(blocks[0].source_pdf_page_end, 10)
        self.assertEqual(blocks[1].source_pdf_page_start, 10)
        self.assertEqual(blocks[1].source_pdf_page_end, 11)
        self.assertEqual(blocks[1].page_anchors[0].pdf_page, 11)

    def test_override_retypes_standalone_block(self):
        pages = [{"page_index": 10, "printed_page_number": "1", "blocks": [
            {"block_id": "raw-1", "text": "on therapy", "reading_order": 1,
             "block_type": "blockquote", "bbox": [90, 100, 300, 120]},
        ]}]

        blocks = normalize_page_records(pages, 10, 10, {"retype": [{"block": "b-001", "type": "heading"}]})

        self.assertEqual(blocks[0].type, "heading")

    def test_override_repairs_a_source_word_without_changing_structure(self):
        pages = [{"page_index": 10, "printed_page_number": "1", "blocks": [
            {"block_id": "raw-1", "text": "The AntiUniversity opened.", "reading_order": 1,
             "block_type": "paragraph", "bbox": [60, 100, 300, 120]},
        ]}]

        blocks = normalize_page_records(
            pages,
            10,
            10,
            {"replace": [{"block": "p-001", "old": "AntiUniversity", "new": "Anti-University"}]},
        )

        self.assertEqual(blocks[0].source_text, "The Anti-University opened.")


if __name__ == "__main__":
    unittest.main()
