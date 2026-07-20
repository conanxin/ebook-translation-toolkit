#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


def candidates() -> list[Path]:
    values: list[Path] = []
    if os.environ.get("EBOOK_TRANSLATION_TOOLKIT_HOME"):
        values.append(Path(os.environ["EBOOK_TRANSLATION_TOOLKIT_HOME"]))
    values.extend([
        Path(r"D:\home\conanxin\workspace\ebook-translation-toolkit"),
        Path("/mnt/d/home/conanxin/workspace/ebook-translation-toolkit"),
    ])
    current = Path.cwd().resolve()
    for parent in (current, *current.parents):
        values.append(parent / "ebook-translation-toolkit")
        values.append(parent.parent / "ebook-translation-toolkit")
    seen: set[str] = set()
    return [path for path in values if not (str(path) in seen or seen.add(str(path)))]


def locate() -> Path:
    for path in candidates():
        if (path / "VERSION").is_file() and (path / "src" / "ebook_translation_toolkit").is_dir():
            return path.resolve()
    raise FileNotFoundError("ebook-translation-toolkit was not found; set EBOOK_TRANSLATION_TOOLKIT_HOME")


if __name__ == "__main__":
    try:
        print(locate())
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        raise SystemExit(2)
