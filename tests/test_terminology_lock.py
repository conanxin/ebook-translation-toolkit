from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ebook_translation_toolkit.terminology_lock import check_terminology_lock


class TerminologyLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".ebook-translation").mkdir(parents=True)
        (self.root / "intermediate" / "chapters").mkdir(parents=True)
        (self.root / "output" / "html").mkdir(parents=True)
        (self.root / "output" / "markdown").mkdir(parents=True)
        self.obsidian = self.root / "vault"
        self.obsidian.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_lock(self, terms: str) -> None:
        text = "version: 1\nlocked_terms:\n" + terms
        (self.root / ".ebook-translation" / "terminology-lock.yaml").write_text(text, encoding="utf-8")

    def write_chapter(self, source: str, target: str, *, chapter: int = 2, html_target: str | None = None, markdown_target: str | None = None, obsidian_target: str | None = None) -> None:
        payload = {"blocks": [{"block_id": "p-001", "source_text": source, "translated_text": target}], "footnotes": []}
        (self.root / "intermediate" / "chapters" / f"chapter-{chapter:02d}-zh.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        visible_html = html_target if html_target is not None else target
        visible_md = markdown_target if markdown_target is not None else target
        visible_ob = obsidian_target if obsidian_target is not None else target
        (self.root / "output" / "html" / f"chapter-{chapter:02d}-zh.html").write_text(f"<html><body><p>{visible_html}</p></body></html>", encoding="utf-8")
        (self.root / "output" / "markdown" / f"chapter-{chapter:02d}-zh.md").write_text(visible_md, encoding="utf-8")
        numeral = "一二三四五六七八九十"[chapter - 1]
        (self.obsidian / f"第{numeral}章-测试.md").write_text(visible_ob, encoding="utf-8")

    @staticmethod
    def person_term() -> str:
        return """  - id: person-example\n    english: [Example Person]\n    preferred_zh: 甲名\n    deprecated_zh: [乙名]\n    category: PERSON\n    require_english_on_first_occurrence: true\n"""

    @staticmethod
    def philosophy_term() -> str:
        return """  - id: philosophy-example\n    english: [enframing, Gestell]\n    preferred_zh: 框定\n    deprecated_zh: [座架]\n    category: PHILOSOPHICAL_TERM\n    context_required: [Heidegger, philosophy of technology, technology]\n    exclude_ordinary_context: true\n"""

    def test_person_multiple_variants_detected(self) -> None:
        self.write_lock(self.person_term())
        self.write_chapter("Example Person appears twice.", "甲名（Example Person）与乙名")
        code, result = check_terminology_lock(self.root, obsidian_dir=self.obsidian)
        self.assertEqual(code, 2)
        self.assertIn("MULTIPLE_PERSON_VARIANTS", {item["code"] for item in result["errors"]})

    def test_deprecated_variant_detected(self) -> None:
        self.write_lock(self.person_term())
        self.write_chapter("Example Person appears.", "乙名（Example Person）")
        _, result = check_terminology_lock(self.root, obsidian_dir=self.obsidian)
        self.assertIn("DEPRECATED_VARIANT", {item["code"] for item in result["errors"]})

    def test_first_occurrence_requires_english_parenthetical(self) -> None:
        self.write_lock(self.person_term())
        self.write_chapter("Example Person appears.", "甲名出现了")
        _, result = check_terminology_lock(self.root, obsidian_dir=self.obsidian)
        self.assertIn("FIRST_OCCURRENCE_ENGLISH_MISSING", {item["code"] for item in result["errors"]})

    def test_context_required_hit_requires_preferred(self) -> None:
        self.write_lock(self.philosophy_term())
        self.write_chapter("Heidegger describes enframing in technology.", "海德格尔讨论座架。")
        _, result = check_terminology_lock(self.root, obsidian_dir=self.obsidian)
        self.assertIn("CONTEXT_PREFERRED_MISSING", {item["code"] for item in result["errors"]})

    def test_context_required_miss_does_not_report(self) -> None:
        self.write_lock(self.philosophy_term())
        self.write_chapter("The editor used enframing as an ordinary label.", "编辑使用普通标签。")
        code, result = check_terminology_lock(self.root, obsidian_dir=self.obsidian)
        self.assertEqual(code, 0)
        self.assertEqual(result["errors"], [])

    def test_ordinary_reveal_is_not_heidegger_term(self) -> None:
        self.write_lock("""  - id: philosophy-revealing\n    english: [revealing]\n    preferred_zh: 显露\n    deprecated_zh: [揭示]\n    category: PHILOSOPHICAL_TERM\n    context_required: [Heidegger, unconcealment, philosophy of technology]\n    exclude_ordinary_context: true\n""")
        self.write_chapter("The result is revealing a measurement error.", "结果揭示了测量错误。")
        code, result = check_terminology_lock(self.root, obsidian_dir=self.obsidian)
        self.assertEqual(code, 0)
        self.assertEqual(result["errors"], [])

    def test_ordinary_framing_is_not_gestell(self) -> None:
        self.write_lock(self.philosophy_term())
        self.write_chapter("The framing of the photograph is narrow.", "照片构图很窄。")
        code, result = check_terminology_lock(self.root, obsidian_dir=self.obsidian)
        self.assertEqual(code, 0)
        self.assertEqual(result["errors"], [])

    def test_json_html_markdown_obsidian_consistency(self) -> None:
        self.write_lock(self.person_term())
        self.write_chapter("Example Person appears.", "甲名（Example Person）", html_target="乙名（Example Person）")
        _, result = check_terminology_lock(self.root, obsidian_dir=self.obsidian)
        self.assertIn("SURFACE_INCONSISTENT", {item["code"] for item in result["errors"]})

    def test_invalid_yaml_detected(self) -> None:
        (self.root / ".ebook-translation" / "terminology-lock.yaml").write_text("version: [\n", encoding="utf-8")
        code, result = check_terminology_lock(self.root)
        self.assertEqual(code, 2)
        self.assertEqual(result["errors"][0]["code"], "INVALID_YAML")

    def test_duplicate_term_id_detected(self) -> None:
        term = self.person_term()
        self.write_lock(term + term.replace("preferred_zh: 甲名", "preferred_zh: 丙名"))
        self.write_chapter("Example Person appears.", "甲名（Example Person）")
        _, result = check_terminology_lock(self.root, obsidian_dir=self.obsidian)
        self.assertIn("DUPLICATE_ID", {item["code"] for item in result["errors"]})

    def test_preferred_cannot_be_deprecated(self) -> None:
        self.write_lock("""  - id: invalid-overlap\n    english: [Example]\n    preferred_zh: 同名\n    deprecated_zh: [同名]\n    category: TECHNICAL_TERM\n""")
        self.write_chapter("Example.", "同名")
        _, result = check_terminology_lock(self.root, obsidian_dir=self.obsidian)
        self.assertIn("PREFERRED_IS_DEPRECATED", {item["code"] for item in result["errors"]})


if __name__ == "__main__":
    unittest.main()
