from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

import yaml


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any, *, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    return value or {}


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def project_config_path(root: Path) -> Path:
    preferred = root / ".ebook-translation" / "project.yaml"
    return preferred if preferred.exists() else root / "project.yaml"


def load_project_config(root: Path) -> dict[str, Any]:
    path = project_config_path(root)
    if not path.exists():
        raise FileNotFoundError(f"project.yaml not found under {root}")
    return read_yaml(path)


def chapter_stem(chapter: int) -> str:
    return f"chapter-{chapter:02d}"


def chapter_data_dir(root: Path, chapter: int) -> Path:
    """Keep the validated chapter-01 layout, use the multi-chapter directory thereafter."""
    if chapter == 1 and not (root / "intermediate" / "chapters" / "chapter-01-source.json").exists():
        return root / "intermediate"
    return root / "intermediate" / "chapters"


def chapter_json_path(root: Path, chapter: int, suffix: str) -> Path:
    return chapter_data_dir(root, chapter) / f"{chapter_stem(chapter)}-{suffix}.json"


def is_relative_safe(path: str) -> bool:
    p = Path(path)
    return not p.is_absolute() and ".." not in p.parts


def ensure_within(base: Path, candidate: Path) -> Path:
    base_resolved = base.resolve()
    candidate_resolved = candidate.resolve()
    if candidate_resolved != base_resolved and base_resolved not in candidate_resolved.parents:
        raise ValueError(f"path escapes allowed root: {candidate}")
    return candidate_resolved


def markdown_visible_text(text: str) -> str:
    text = re.sub(r"^---\s.*?^---\s*", "", text, flags=re.M | re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"!\[[^]]*]\([^)]*\)", "", text)
    text = re.sub(r"\[\^\d+]", "", text)
    text = re.sub(r"^\[\^\d+]:.*$", "", text, flags=re.M)
    text = re.sub(r"[*_`#>]", "", text)
    return re.sub(r"\s+", "", text)


def consecutive(values: Iterable[int], start: int = 1) -> bool:
    actual = list(values)
    return actual == list(range(start, start + len(actual)))
