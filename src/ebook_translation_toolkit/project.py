from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from . import __version__
from .utils import atomic_write_text, read_yaml, write_yaml


TOOLKIT_ROOT = Path(__file__).resolve().parents[2]


def default_config(
    pdf: Path,
    project_root: Path,
    obsidian_vault: Path | None,
    book_slug: str,
    chapter: int,
    language: str,
) -> dict[str, Any]:
    return {
        "toolkit_version": __version__,
        "skill": "ebook-translation-zh",
        "book": {"title": "", "author": "", "slug": book_slug},
        "source": {"pdf": "source/original.pdf", "input_pdf": str(pdf)},
        "language": {"source": "en", "target": language},
        "chapter": {"number": chapter, "title_en": "", "title_zh": "", "pdf_start": None, "pdf_end": None},
        "obsidian": {
            "vault": str(obsidian_vault) if obsidian_vault else "",
            "destination": f"_Agent/Outputs/Book-Translations/{book_slug}",
        },
        "render": {
            "html": {
                "inline_footnotes": True,
                "append_footnote_section": False,
                "italic_visual_style": False,
                "reading_modes": ["paged", "continuous"],
            },
            "markdown": {"standard_footnotes": True},
        },
        "terms": {"bilingual_first_occurrence": True},
        "images": {"insert_only_after_complete_block": True},
        "paragraphs": {"merge_across_pdf_pages": True, "page_markers_inside_blocks": True},
    }


def _copy_template(relative: str, destination: Path) -> None:
    source = TOOLKIT_ROOT / "templates" / relative
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        shutil.copy2(source, destination)


def initialize_project(
    pdf: Path,
    project_root: Path,
    obsidian_vault: Path | None,
    book_slug: str,
    chapter: int = 1,
    language: str = "zh-CN",
) -> dict[str, Any]:
    project_root = project_root.resolve()
    for relative in (
        ".ebook-translation",
        "source",
        "intermediate",
        "assets",
        "output/html",
        "output/markdown",
        "reports",
        "scripts",
    ):
        (project_root / relative).mkdir(parents=True, exist_ok=True)

    source_pdf = project_root / "source" / "original.pdf"
    if pdf.exists() and not source_pdf.exists():
        shutil.copy2(pdf, source_pdf)

    config_path = project_root / ".ebook-translation" / "project.yaml"
    if config_path.exists():
        config = read_yaml(config_path)
    else:
        config = default_config(pdf, project_root, obsidian_vault, book_slug, chapter, language)
        write_yaml(config_path, config)

    _copy_template("project/AGENTS.md", project_root / "AGENTS.md")
    _copy_template("project/README.md", project_root / "README.md")
    for name, content in {
        "paragraph-overrides.yaml": "merge: []\nsplit: []\n",
        "image-overrides.yaml": "anchors: {}\n",
        "terminology.tsv": "category\tenglish\tchinese\tnotes\n",
    }.items():
        path = project_root / ".ebook-translation" / name
        if not path.exists():
            atomic_write_text(path, content)

    ps = project_root / "scripts" / "ebook-translate.ps1"
    sh = project_root / "scripts" / "ebook-translate.sh"
    if not ps.exists():
        atomic_write_text(ps, "$toolkit = $env:EBOOK_TRANSLATION_TOOLKIT_HOME\nif (-not $toolkit) { $toolkit = 'D:\\home\\conanxin\\workspace\\ebook-translation-toolkit' }\n& \"$toolkit\\scripts\\ebook-translate.ps1\" @args\nexit $LASTEXITCODE\n")
    if not sh.exists():
        atomic_write_text(sh, "#!/usr/bin/env bash\nset -euo pipefail\ntoolkit=\"${EBOOK_TRANSLATION_TOOLKIT_HOME:-/mnt/d/home/conanxin/workspace/ebook-translation-toolkit}\"\nexec \"$toolkit/scripts/ebook-translate.sh\" \"$@\"\n")
    return config
