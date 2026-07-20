import json
import tempfile
import unittest
from pathlib import Path

from ebook_translation_toolkit.chapter_detect import detect_chapter
from ebook_translation_toolkit.paragraph_reflow import chapter_overrides
from ebook_translation_toolkit.utils import chapter_json_path


class MultiChapterTests(unittest.TestCase):
    def test_chapter_scoped_paragraph_overrides_do_not_leak(self):
        raw = {
            "merge": [["global-a", "global-b"]],
            "chapters": {
                "5": {"split": [{"block": "p-010", "after": "heading"}], "retype": [{"block": "b-003", "type": "heading"}]},
                "6": {"split": [{"block": "p-020", "after": "other"}]},
            },
        }

        chapter_five = chapter_overrides(raw, 5)
        chapter_six = chapter_overrides(raw, 6)

        self.assertEqual(chapter_five["split"][0]["block"], "p-010")
        self.assertEqual(chapter_six["split"][0]["block"], "p-020")
        self.assertEqual(chapter_five["merge"], [["global-a", "global-b"]])
        self.assertEqual(chapter_six["retype"], [])

    def test_later_chapter_ignores_chapter_one_override_and_stops_at_part(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".ebook-translation").mkdir(parents=True)
            (root / "intermediate").mkdir()
            (root / ".ebook-translation/project.yaml").write_text(
                "chapter:\n  number: 1\n  pdf_start: 12\n  pdf_end: 27\n", encoding="utf-8"
            )
            structure = {
                "pdf_total_pages": 120,
                "toc": [
                    {"level": 1, "title": "1. First", "pdf_page": 12},
                    {"level": 1, "title": "2. Second", "pdf_page": 28},
                    {"level": 1, "title": "PART 1", "pdf_page": 46},
                    {"level": 2, "title": "3. Third", "pdf_page": 48}
                ],
                "chapters": [{"level": 1, "title": "1. First", "pdf_page": 12}]
            }
            (root / "intermediate/ebook-structure.json").write_text(json.dumps(structure), encoding="utf-8")
            pages = [json.dumps({"page_index": page, "printed_page_number": str(page - 11)}) for page in range(1, 121)]
            (root / "intermediate/ebook-pages.jsonl").write_text("\n".join(pages), encoding="utf-8")
            result = detect_chapter(root, 2)
            self.assertEqual((result["pdf_start"], result["pdf_end"]), (28, 45))

    def test_later_chapter_uses_chapters_directory(self):
        root = Path("D:/book")
        self.assertEqual(chapter_json_path(root, 2, "source"), root / "intermediate/chapters/chapter-02-source.json")


if __name__ == "__main__":
    unittest.main()
