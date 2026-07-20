import json
import tempfile
import unittest
from pathlib import Path

from ebook_translation_toolkit.endnotes import bind_endnote_references, extract_chapter_endnotes
from ebook_translation_toolkit.models import Block, Footnote, StructuredChapter


class EndnoteTests(unittest.TestCase):
    def test_extracts_cross_page_notes_and_binds(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pages.jsonl"
            rows = [
                {"page_index": 1, "text": "Notes to Chapter 2\n1. First hy-\n phenated note.\n2. Second note starts"},
                {"page_index": 2, "text": "2 :: NOTES TO PAGES\n and ends.\nNotes to Chapter 3\n1. Other"},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            notes = extract_chapter_endnotes(path, 2)
            self.assertEqual([note.number for note in notes], [1, 2])
            self.assertIn("hyphenated", notes[0].source_text)
            chapter = StructuredChapter({}, {}, [Block("p-001", source_text="One.1"), Block("p-002", source_text="Two.2")])
            bind_endnote_references(chapter, notes)
            self.assertEqual([ref.number for block in chapter.blocks for ref in block.footnote_refs], [1, 2])

    def test_last_chapter_stops_at_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pages.jsonl"
            rows = [{"page_index": 1, "text": "Notes to Chapter 8\n1. Last note.\n References\n1. Not a note"}]
            path.write_text(json.dumps(rows[0]), encoding="utf-8")
            notes = extract_chapter_endnotes(path, 8)
            self.assertEqual(len(notes), 1)
            self.assertEqual(notes[0].source_text, "Last note.")

    def test_numbered_reference_inside_note_is_not_a_new_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pages.jsonl"
            row = {
                "page_index": 1,
                "text": (
                    "Notes to Chapter 3\n"
                    "1. First note refers to chapter 7. In that chapter the topic returns.\n"
                    "2. Second note.\n"
                    "Notes to Chapter 4\n1. Other"
                ),
            }
            path.write_text(json.dumps(row), encoding="utf-8")
            notes = extract_chapter_endnotes(path, 3)
            self.assertEqual([note.number for note in notes], [1, 2])
            self.assertIn("chapter 7. In", notes[0].source_text)

    def test_adjacent_archival_number_does_not_hide_next_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pages.jsonl"
            notes = " ".join(f"{number}. Note {number}." for number in range(1, 8))
            row = {
                "page_index": 1,
                "text": (
                    "Notes to Chapter 4\n"
                    f"{notes} 8. Archive B.N. 1. 9. Ninth note.\n"
                    "Notes to Chapter 5\n1. Other"
                ),
            }
            path.write_text(json.dumps(row), encoding="utf-8")
            extracted = extract_chapter_endnotes(path, 4)
            self.assertEqual([note.number for note in extracted], list(range(1, 10)))
            self.assertIn("B.N. 1.", extracted[7].source_text)
            self.assertEqual(extracted[8].source_text, "Ninth note.")

    def test_figure_decimal_is_not_bound_as_endnote_reference(self):
        chapter = StructuredChapter(
            {},
            {},
            [
                Block("p-001", source_text="He was born in 1903.5 It continued."),
                Block("p-002", source_text="Figure 4.5 shows the result."),
            ],
        )
        notes = [type("Note", (), {"number": 5, "block_id": ""})()]
        bind_endnote_references(chapter, notes)
        self.assertEqual(chapter.blocks[0].source_text, "He was born in 1903. It continued.")
        self.assertEqual(chapter.blocks[0].footnote_refs[0].number, 5)
        self.assertEqual(chapter.blocks[1].source_text, "Figure 4.5 shows the result.")

    def test_license_decimal_is_not_bound_as_endnote_reference(self):
        chapter = StructuredChapter(
            book={},
            chapter={},
            blocks=[
                Block(
                    block_id="p-001",
                    type="paragraph",
                    source_text="The argument ends here.5",
                    reading_order=1,
                ),
                Block(
                    block_id="q-001",
                    type="blockquote",
                    source_text="Commons Share Alike 2.5 Generic License.)",
                    reading_order=2,
                ),
            ],
            footnotes=[],
            images=[],
            terms=[],
            page_anchors=[],
        )
        notes = [Footnote(number=5, source_text="A note.")]

        bind_endnote_references(chapter, notes)

        self.assertEqual(chapter.blocks[0].source_text, "The argument ends here.")
        self.assertEqual(chapter.blocks[0].footnote_refs[0].number, 5)
        self.assertEqual(chapter.blocks[1].source_text, "Commons Share Alike 2.5 Generic License.)")

    def test_reference_after_colon_is_bound(self):
        chapter = StructuredChapter({}, {}, [Block("p-001", source_text="The quotation begins:45")])
        notes = [type("Note", (), {"number": 45, "block_id": ""})()]
        bind_endnote_references(chapter, notes)
        self.assertEqual(chapter.blocks[0].source_text, "The quotation begins:")
        self.assertEqual(chapter.blocks[0].footnote_refs[0].number, 45)


if __name__ == "__main__":
    unittest.main()
