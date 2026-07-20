import tempfile
import unittest
from pathlib import Path

from ebook_translation_toolkit.apply_translation import apply_translation_map
from ebook_translation_toolkit.models import Block, Footnote, ImageAsset, StructuredChapter
from ebook_translation_toolkit.utils import chapter_json_path, write_json


class ApplyTranslationTests(unittest.TestCase):
    def test_applies_image_caption_from_same_translation_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = StructuredChapter(
                book={"title": "Book"},
                chapter={"number": 3, "title_en": "Chapter"},
                blocks=[Block("p-001", source_text="Text")],
                images=[ImageAsset("figure-001", "assets/chapter-03/figure-001.png", 10)],
                footnotes=[Footnote(1, source_text="Note", block_id="p-001")],
            )
            write_json(chapter_json_path(root, 3, "source"), source.to_dict())
            mapping = root / "mapping.json"
            write_json(mapping, {
                "blocks": {"p-001": "译文"},
                "footnotes": {"1": "注释"},
                "image_captions": {"figure-001": "图注"},
            })
            translated = apply_translation_map(root, 3, mapping)
            self.assertEqual(translated.images[0].caption_zh, "图注")


if __name__ == "__main__":
    unittest.main()
