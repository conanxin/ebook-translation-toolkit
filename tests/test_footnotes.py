import unittest

from ebook_translation_toolkit.footnotes import html_trigger, validate_footnotes
from ebook_translation_toolkit.models import Footnote, FootnoteRef


class FootnoteTests(unittest.TestCase):
    def test_seven_notes_are_consecutive_and_bound(self):
        notes = [Footnote(number) for number in range(1, 8)]
        refs = [FootnoteRef(number, number * 10) for number in range(1, 8)]
        self.assertEqual(validate_footnotes(notes, refs), [])

    def test_gap_is_rejected(self):
        self.assertTrue(validate_footnotes([Footnote(1), Footnote(3)], [FootnoteRef(1, 0), FootnoteRef(3, 1)]))

    def test_trigger_is_accessible_button(self):
        trigger = html_trigger(2)
        self.assertIn("<button", trigger)
        self.assertIn('aria-expanded="false"', trigger)
        self.assertIn('aria-controls="footnote-popover"', trigger)
        self.assertNotIn("href=", trigger)


if __name__ == "__main__":
    unittest.main()
