from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TerminologyLockResult:
    status: str
    config: str
    checked_chapters: list[int] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    surface_checks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "config": self.config,
            "checked_chapters": self.checked_chapters,
            "errors": self.errors,
            "warnings": self.warnings,
            "surface_checks": self.surface_checks,
        }


def _issue(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def load_terminology_lock(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid terminology lock YAML: {exc}") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("terminology lock must be a mapping with version: 1")
    terms = data.get("locked_terms")
    if not isinstance(terms, list):
        raise ValueError("locked_terms must be a list")
    return data


def _chapter_files(root: Path) -> list[tuple[int, Path]]:
    files: list[tuple[int, Path]] = []
    for path in sorted((root / "intermediate" / "chapters").glob("chapter-*-zh.json")):
        match = re.fullmatch(r"chapter-(\d+)-zh\.json", path.name)
        if match:
            files.append((int(match.group(1)), path))
    return files


def _visible_html(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text)


def _visible_markdown(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^---\s*$.*?^---\s*$", " ", text, count=1, flags=re.M | re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"!\[[^]]*]\([^)]*\)", " ", text)
    return text


def _term_in_context(source: str, term: dict[str, Any]) -> bool:
    required = [str(item) for item in term.get("context_required", [])]
    if not required:
        return True
    lower = source.casefold()
    return any(item.casefold() in lower for item in required)


def _english_present(source: str, term: dict[str, Any]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(str(name))}(?!\w)", source, re.I) for name in term.get("english", []))


def _chapter_obsidian_path(root: Path, chapter: int, destination: Path | None) -> Path | None:
    if destination is None or not destination.exists():
        return None
    candidates = sorted(destination.glob(f"第{'一二三四五六七八九十'[chapter-1]}章-*.md")) if 1 <= chapter <= 10 else []
    return candidates[0] if len(candidates) == 1 else None


def check_terminology_lock(project_root: Path, *, obsidian_dir: Path | None = None) -> tuple[int, dict[str, Any]]:
    root = project_root.resolve()
    config_path = root / ".ebook-translation" / "terminology-lock.yaml"
    result = TerminologyLockResult(status="FAIL", config=str(config_path))
    try:
        data = load_terminology_lock(config_path)
    except ValueError as exc:
        result.errors.append(_issue("INVALID_YAML", str(exc), path=str(config_path)))
        return 2, result.to_dict()

    terms = data["locked_terms"]
    ids = [term.get("id") for term in terms if isinstance(term, dict)]
    duplicate_ids = sorted({item for item in ids if item and ids.count(item) > 1})
    for term_id in duplicate_ids:
        result.errors.append(_issue("DUPLICATE_ID", f"duplicate terminology term id: {term_id}", term_id=term_id))

    for term in terms:
        if not isinstance(term, dict):
            result.errors.append(_issue("INVALID_TERM", "locked term entry must be a mapping"))
            continue
        term_id = str(term.get("id", ""))
        preferred = str(term.get("preferred_zh", ""))
        deprecated = [str(item) for item in term.get("deprecated_zh", [])]
        if not term_id or not preferred or not isinstance(term.get("english"), list):
            result.errors.append(_issue("INVALID_TERM", "locked term requires id, english list, and preferred_zh", term_id=term_id))
        if preferred in deprecated:
            result.errors.append(_issue("PREFERRED_IS_DEPRECATED", "preferred_zh must not also be deprecated", term_id=term_id, preferred_zh=preferred))

    chapter_records: dict[int, dict[str, Any]] = {}
    for chapter, path in _chapter_files(root):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            result.errors.append(_issue("INVALID_CHAPTER_JSON", str(exc), chapter=chapter, path=str(path)))
            continue
        records = list(payload.get("blocks", [])) + list(payload.get("footnotes", []))
        chapter_records[chapter] = {"path": path, "records": records}
        result.checked_chapters.append(chapter)

    for term in terms:
        if not isinstance(term, dict) or not term.get("id"):
            continue
        term_id = str(term["id"])
        preferred = str(term.get("preferred_zh", ""))
        deprecated = [str(item) for item in term.get("deprecated_zh", [])]
        category = str(term.get("category", ""))
        relevant: list[tuple[int, dict[str, Any], str, str]] = []
        for chapter, payload in chapter_records.items():
            for record in payload["records"]:
                source = str(record.get("source_text", ""))
                target = str(record.get("translated_text", ""))
                if _english_present(source, term) and _term_in_context(source, term):
                    relevant.append((chapter, record, source, target))
                    for variant in deprecated:
                        if variant and variant in target:
                            result.errors.append(_issue("DEPRECATED_VARIANT", f"deprecated variant remains: {variant}", term_id=term_id, chapter=chapter, block_id=record.get("block_id"), variant=variant))
                    if preferred and preferred not in target and category == "PHILOSOPHICAL_TERM" and term.get("require_preferred_in_every_context", True):
                        result.errors.append(_issue("CONTEXT_PREFERRED_MISSING", f"preferred philosophical term missing in required context: {preferred}", term_id=term_id, chapter=chapter, block_id=record.get("block_id")))
        if category == "PERSON":
            variants = [preferred, *deprecated]
            observed = sorted({variant for _, _, _, target in relevant for variant in variants if variant and variant in target})
            if len(observed) > 1:
                result.errors.append(_issue("MULTIPLE_PERSON_VARIANTS", "multiple Chinese variants found for one PERSON", term_id=term_id, variants=observed))
            if term.get("require_english_on_first_occurrence") and relevant:
                first_by_chapter: dict[int, tuple[dict[str, Any], str]] = {}
                for chapter, record, _, target in relevant:
                    first_by_chapter.setdefault(chapter, (record, target))
                for chapter, (record, target) in first_by_chapter.items():
                    if preferred in target and not any(f"（{name}" in target or f"({name}" in target for name in term.get("english", [])):
                        result.errors.append(_issue("FIRST_OCCURRENCE_ENGLISH_MISSING", "first chapter occurrence lacks English parenthetical", term_id=term_id, chapter=chapter, block_id=record.get("block_id")))

    destination = obsidian_dir.resolve() if obsidian_dir else None
    for chapter in result.checked_chapters:
        json_path = chapter_records[chapter]["path"]
        json_text = "\n".join(str(record.get("translated_text", "")) for record in chapter_records[chapter]["records"])
        surfaces: list[tuple[str, Path | None, str]] = [
            ("json", json_path, json_text),
            ("html", root / "output" / "html" / f"chapter-{chapter:02d}-zh.html", ""),
            ("markdown", root / "output" / "markdown" / f"chapter-{chapter:02d}-zh.md", ""),
            ("obsidian", _chapter_obsidian_path(root, chapter, destination), ""),
        ]
        loaded: dict[str, str] = {}
        for name, path, text in surfaces:
            if path is None or not path.exists():
                if name != "obsidian" or destination is not None:
                    result.warnings.append(_issue("SURFACE_MISSING", f"surface missing: {name}", chapter=chapter, surface=name, path=str(path) if path else None))
                continue
            loaded[name] = text or (_visible_html(path) if name == "html" else _visible_markdown(path))
        for term in terms:
            if not isinstance(term, dict):
                continue
            variants = [str(term.get("preferred_zh", "")), *[str(item) for item in term.get("deprecated_zh", [])]]
            counts = {name: {variant: text.count(variant) for variant in variants if variant} for name, text in loaded.items()}
            if "json" in counts:
                expected = counts["json"]
                for name, observed in counts.items():
                    if name != "json" and any(observed.get(variant, 0) != expected.get(variant, 0) for variant in deprecated if variant):
                        result.errors.append(_issue("SURFACE_INCONSISTENT", "deprecated term counts differ across output surfaces", term_id=term.get("id"), chapter=chapter, surface=name, expected=expected, observed=observed))
                result.surface_checks.append({"term_id": term.get("id"), "chapter": chapter, "counts": counts})

    result.status = "FAIL" if result.errors else ("WARN" if result.warnings else "PASS")
    return (2 if result.errors else (1 if result.warnings else 0)), result.to_dict()
