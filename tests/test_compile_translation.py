import json
import tempfile
import unittest
from pathlib import Path

from ebook_translation_toolkit.compile_translation import compile_translation_workfiles
from ebook_translation_toolkit.models import Block, Footnote, ImageAsset, PageAnchor, StructuredChapter
from ebook_translation_toolkit.utils import chapter_data_dir, chapter_json_path, read_json, write_json


class CompileTranslationTests(unittest.TestCase):
    def test_compiles_and_consumes_declared_fragment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ebook-translation").mkdir()
            (root / ".ebook-translation" / "translation-overrides.yaml").write_text(
                "merge:\n  p-001: [p-001b]\n", encoding="utf-8"
            )
            source = StructuredChapter(
                book={"title": "Book"}, chapter={"number": 4},
                blocks=[Block("p-001", source_text="A B")],
                images=[ImageAsset("figure-001", "assets/chapter-04/figure-001.png", 1)],
                footnotes=[Footnote(1, source_text="N", block_id="p-001")],
            )
            write_json(chapter_json_path(root, 4, "source"), source.to_dict())
            data = chapter_data_dir(root, 4)
            data.mkdir(parents=True, exist_ok=True)
            (data / "chapter-04-blocks-zh.jsonl").write_text(
                '\n'.join([
                    json.dumps({"block_id": "p-001", "translated_text": "甲"}, ensure_ascii=False),
                    json.dumps({"block_id": "p-001b", "translated_text": "乙"}, ensure_ascii=False),
                ]), encoding="utf-8"
            )
            (data / "chapter-04-footnotes-zh.jsonl").write_text(
                json.dumps({"number": 1, "translated_text": "注"}, ensure_ascii=False), encoding="utf-8"
            )
            (data / "chapter-04-image-captions-zh.jsonl").write_text(
                json.dumps({"image_id": "figure-001", "caption_zh": "图"}, ensure_ascii=False), encoding="utf-8"
            )
            output = compile_translation_workfiles(root, 4)
            self.assertEqual(read_json(output)["blocks"], {"p-001": "甲乙"})

    def test_rejects_unconsumed_fragment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ebook-translation").mkdir()
            source = StructuredChapter(book={}, chapter={"number": 4}, blocks=[Block("p-001", source_text="A")])
            write_json(chapter_json_path(root, 4, "source"), source.to_dict())
            data = chapter_data_dir(root, 4)
            data.mkdir(parents=True, exist_ok=True)
            (data / "chapter-04-blocks-zh.jsonl").write_text(
                '{"block_id":"p-001","translated_text":"甲"}\n{"block_id":"old","translated_text":"乙"}', encoding="utf-8"
            )
            (data / "chapter-04-footnotes-zh.jsonl").write_text("", encoding="utf-8")
            (data / "chapter-04-image-captions-zh.jsonl").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unconsumed"):
                compile_translation_workfiles(root, 4)

    def test_injects_page_marker_created_by_semantic_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ebook-translation").mkdir()
            source = StructuredChapter(
                book={}, chapter={"number": 4},
                blocks=[Block("p-001", source_text="First half second half.",
                              source_pdf_page_start=10, source_pdf_page_end=11,
                              page_anchors=[PageAnchor(11, "2", 11, "p-001")])],
            )
            write_json(chapter_json_path(root, 4, "source"), source.to_dict())
            data = chapter_data_dir(root, 4)
            data.mkdir(parents=True, exist_ok=True)
            (data / "chapter-04-blocks-zh.jsonl").write_text(
                '{"block_id":"p-001","translated_text":"前半句。后半句。"}', encoding="utf-8"
            )
            (data / "chapter-04-footnotes-zh.jsonl").write_text("", encoding="utf-8")
            (data / "chapter-04-image-captions-zh.jsonl").write_text("", encoding="utf-8")
            output = compile_translation_workfiles(root, 4)
            self.assertIn("[[PAGE:11|2]]", read_json(output)["blocks"]["p-001"])

    def test_chapter_scoped_merge_does_not_leak_to_same_block_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ebook-translation").mkdir()
            (root / ".ebook-translation" / "translation-overrides.yaml").write_text(
                "chapters:\n  4:\n    merge:\n      p-001: [p-001b]\n", encoding="utf-8"
            )
            source = StructuredChapter(book={}, chapter={"number": 5}, blocks=[Block("p-001", source_text="A")])
            write_json(chapter_json_path(root, 5, "source"), source.to_dict())
            data = chapter_data_dir(root, 5)
            data.mkdir(parents=True, exist_ok=True)
            (data / "chapter-05-blocks-zh.jsonl").write_text(
                '{"block_id":"p-001","translated_text":"甲"}', encoding="utf-8"
            )
            (data / "chapter-05-footnotes-zh.jsonl").write_text("", encoding="utf-8")
            (data / "chapter-05-image-captions-zh.jsonl").write_text("", encoding="utf-8")
            output = compile_translation_workfiles(root, 5)
            self.assertEqual(read_json(output)["blocks"], {"p-001": "甲"})


if __name__ == "__main__":
    unittest.main()
