import json
import tempfile
import unittest
from pathlib import Path

from ebook_translation_toolkit.cli import _render
from ebook_translation_toolkit.models import Block, Footnote, ImageAsset, StructuredChapter
from ebook_translation_toolkit.pre_render_gate import evaluate_pre_render_gate, run_pre_render_gate
from ebook_translation_toolkit.utils import chapter_json_path, write_json


def chapters() -> tuple[StructuredChapter, StructuredChapter]:
    source = StructuredChapter(
        book={"title": "Book", "author": "Author"},
        chapter={"number": 2, "title_en": "Chapter", "title_zh": "章节"},
        blocks=[Block("p-001", source_text="A complete source paragraph.", source_pdf_page_start=1)],
        images=[ImageAsset("figure-001", "assets/chapter-02/figure-001.png", 1, caption_source="A caption")],
        footnotes=[Footnote(1, source_text="A complete source note.", block_id="p-001")],
    )
    translated = StructuredChapter.from_dict(source.to_dict())
    translated.blocks[0].translated_text = "完整译文。"
    translated.footnotes[0].translated_text = "完整注释。"
    translated.images[0].caption_zh = "完整图注。"
    return source, translated


class PreRenderGateTests(unittest.TestCase):
    def test_missing_block_rejects_render(self):
        source, translated = chapters()
        translated.blocks.clear()
        result = evaluate_pre_render_gate(source, translated)
        self.assertEqual(result["pre_render_decision"], "FAIL")
        self.assertEqual(result["missing_blocks"], ["p-001"])

    def test_empty_translation_rejects_render(self):
        source, translated = chapters()
        translated.blocks[0].translated_text = ""
        result = evaluate_pre_render_gate(source, translated)
        self.assertEqual(result["empty_translations"], ["p-001"])
        self.assertEqual(result["pre_render_decision"], "FAIL")

    def test_untranslated_footnote_rejects_render(self):
        source, translated = chapters()
        translated.footnotes[0].translated_text = ""
        result = evaluate_pre_render_gate(source, translated)
        self.assertEqual(result["empty_footnotes"], [1])
        self.assertEqual(result["pre_render_decision"], "FAIL")

    def test_untranslated_caption_rejects_render(self):
        source, translated = chapters()
        translated.images[0].caption_zh = ""
        result = evaluate_pre_render_gate(source, translated)
        self.assertEqual(result["empty_image_captions"], ["figure-001"])
        self.assertEqual(result["pre_render_decision"], "FAIL")

    def test_rejected_tmp_cache_is_never_read(self):
        source, translated = chapters()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(chapter_json_path(root, 2, "source"), source.to_dict())
            write_json(chapter_json_path(root, 2, "zh"), translated.to_dict())
            rejected = root / ".tmp" / "chapter-02-zh.rejected.json"
            rejected.parent.mkdir(parents=True)
            rejected.write_text(json.dumps({"blocks": []}), encoding="utf-8")
            result = run_pre_render_gate(root, 2)
        self.assertEqual(result["pre_render_decision"], "PASS")
        self.assertTrue(result["ignored_rejected_cache"])

    def test_render_requires_passing_pre_render_gate(self):
        source, translated = chapters()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(chapter_json_path(root, 2, "source"), source.to_dict())
            translated.blocks[0].translated_text = ""
            write_json(chapter_json_path(root, 2, "zh"), translated.to_dict())
            with self.assertRaisesRegex(RuntimeError, "PRE_RENDER_GATE FAIL"):
                _render(root, 2)
            translated.blocks[0].translated_text = "完整译文。"
            write_json(chapter_json_path(root, 2, "zh"), translated.to_dict())
            _render(root, 2)
            self.assertTrue((root / "output" / "html" / "chapter-02-zh.html").exists())
            self.assertTrue((root / "output" / "markdown" / "chapter-02-zh.md").exists())


if __name__ == "__main__":
    unittest.main()
