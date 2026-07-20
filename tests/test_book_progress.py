import json
import tempfile
import unittest
from pathlib import Path

from ebook_translation_toolkit.book_progress import detect_book_plan, render_book_indices, update_chapter


class BookProgressTests(unittest.TestCase):
    def test_plan_preserves_part_boundaries_and_resume_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "intermediate").mkdir(parents=True)
            structure = {"title":"Book","author":"Author","pdf_total_pages":60,"toc":[
                {"level":1,"title":"1. One","pdf_page":2},
                {"level":1,"title":"2. Two","pdf_page":10},
                {"level":1,"title":"PART 1","pdf_page":20},
                {"level":2,"title":"3. Three","pdf_page":22},
                {"level":1,"title":"Notes","pdf_page":40}
            ]}
            (root / "intermediate/ebook-structure.json").write_text(json.dumps(structure), encoding="utf-8")
            pages = [json.dumps({"page_index":i,"printed_page_number":str(i)}) for i in range(1,61)]
            (root / "intermediate/ebook-pages.jsonl").write_text("\n".join(pages), encoding="utf-8")
            plan = detect_book_plan(root)
            self.assertEqual([(c["pdf_start"], c["pdf_end"]) for c in plan["chapters"]], [(2,9),(10,19),(22,39)])
            update_chapter(root, 2, "EXTRACTED", source_words=123)
            resumed = detect_book_plan(root)
            self.assertEqual(resumed["chapters"][1]["status"], "EXTRACTED")
            self.assertEqual(resumed["chapters"][1]["source_words"], 123)
            rendered = render_book_indices(root)
            self.assertTrue(Path(rendered["html"]).exists())
            self.assertIn("width:100%", Path(rendered["html"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
