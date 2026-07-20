from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import Block, Term
from .utils import atomic_write_text


CATEGORIES = {
    "PERSON", "BOOK", "ARTICLE", "ORGANIZATION", "CONFERENCE", "THEORY",
    "TECHNICAL_TERM", "PLACE", "DEVICE", "PROJECT",
}


def load_terminology(path: Path) -> list[Term]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream, delimiter="\t")
        terms = []
        for row in rows:
            if not row.get("english") or not row.get("chinese"):
                continue
            terms.append(Term(row["english"], row["chinese"], row.get("category") or "TECHNICAL_TERM", notes=row.get("notes") or ""))
        return terms


def expected_first_form(term: Term) -> str:
    if term.category in {"BOOK", "ARTICLE"}:
        chinese = term.chinese if term.chinese.startswith("《") else f"《{term.chinese}》"
        return f"{chinese}（{term.english}）"
    return f"{term.chinese}（{term.english}）"


def check_terms(blocks: list[Block], terms: list[Term]) -> dict[str, list[str]]:
    text = "\n".join(block.translated_text for block in blocks)
    by_id = {block.block_id: block.translated_text for block in blocks}
    missing: list[str] = []
    duplicates: list[str] = []
    inconsistent: list[str] = []
    for term in terms:
        if term.category not in CATEGORIES:
            inconsistent.append(f"{term.english}: unsupported category {term.category}")
        target = by_id.get(term.first_block_id, text) if term.first_block_id else text
        chinese = term.chinese if term.category not in {"BOOK", "ARTICLE"} or term.chinese.startswith("《") else f"《{term.chinese}》"
        prefix = f"{chinese}（{term.english}"
        first_chinese = target.find(chinese)
        first_prefix = target.find(prefix)
        if first_chinese >= 0 and (first_prefix < 0 or first_chinese != first_prefix):
            missing.append(term.english)
        if text.count(f"（{term.english}") > 1:
            duplicates.append(term.english)
        if re.search(rf"{re.escape(term.english)}（{re.escape(term.english)}）", text):
            inconsistent.append(f"{term.english}: duplicated Latin spelling")
    return {"missing": missing, "duplicates": duplicates, "inconsistent": inconsistent}


def write_report(path: Path, result: dict[str, list[str]]) -> None:
    lines = ["# Bilingual terminology report", ""]
    for key in ("missing", "duplicates", "inconsistent"):
        lines.append(f"## {key.title()}")
        lines.extend(f"- {item}" for item in result[key])
        if not result[key]:
            lines.append("- None")
        lines.append("")
    atomic_write_text(path, "\n".join(lines))
