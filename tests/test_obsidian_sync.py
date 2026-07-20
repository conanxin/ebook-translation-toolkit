import tempfile
import unittest
from pathlib import Path

from ebook_translation_toolkit.obsidian_sync import chapter_output_name, sync_obsidian


class ObsidianSyncTests(unittest.TestCase):
    def test_canonical_chinese_output_name_is_derived_in_python(self):
        self.assertEqual(
            chapter_output_name(5, "格雷戈里·贝特森与 R. D. 莱恩：对称、精神病学与六十年代"),
            "第五章-格雷戈里·贝特森与 R. D. 莱恩：对称、精神病学与六十年代.md",
        )

    def test_sync_is_scoped_and_hash_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            vault = Path(directory) / "vault"
            markdown = root / "output" / "markdown" / "chapter-01-zh.md"
            asset = root / "assets" / "chapter-01" / "figure.jpg"
            markdown.parent.mkdir(parents=True)
            asset.parent.mkdir(parents=True)
            markdown.write_text("正文\n\n![](../../assets/chapter-01/figure.jpg)\n", encoding="utf-8")
            asset.write_bytes(b"image-bytes")
            result = sync_obsidian(markdown, root, vault, Path("Books/book"), copy_assets=True)
            self.assertTrue(result["verified"])
            target = vault / "Books" / "book"
            self.assertIn("![](assets/chapter-01/figure.jpg)", (target / markdown.name).read_text(encoding="utf-8"))
            self.assertEqual((target / "assets" / "chapter-01" / "figure.jpg").read_bytes(), b"image-bytes")

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            vault = Path(directory) / "vault"
            markdown = root / "output" / "markdown" / "chapter.md"
            markdown.parent.mkdir(parents=True)
            markdown.write_text("text", encoding="utf-8")
            result = sync_obsidian(markdown, root, vault, Path("safe"), dry_run=True)
            self.assertTrue(result["dry_run"])
            self.assertFalse(vault.exists())

    def test_obsidian_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            vault = Path(directory) / "vault"
            markdown = root / "output" / "markdown" / "chapter.md"
            markdown.parent.mkdir(parents=True)
            markdown.write_text("text", encoding="utf-8")
            with self.assertRaises(ValueError):
                sync_obsidian(markdown, root, vault, Path(".obsidian/unsafe"))


if __name__ == "__main__":
    unittest.main()
