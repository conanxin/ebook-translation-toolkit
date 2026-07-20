import json
import unittest
from pathlib import Path

from ebook_translation_toolkit.bilingual_terms import check_terms, expected_first_form
from ebook_translation_toolkit.models import StructuredChapter, Term


FIXTURE = Path(__file__).parent / "fixtures" / "cybernetic_brain_minimal.json"


class BilingualTermTests(unittest.TestCase):
    def test_28_terms_pass(self):
        chapter = StructuredChapter.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))
        self.assertEqual(len(chapter.terms), 28)
        result = check_terms(chapter.blocks, chapter.terms)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["inconsistent"], [])

    def test_book_form(self):
        self.assertEqual(expected_first_form(Term("Design for a Brain", "大脑设计", "BOOK")), "《大脑设计》（Design for a Brain）")


if __name__ == "__main__":
    unittest.main()
