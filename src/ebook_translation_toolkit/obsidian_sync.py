from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from .utils import ensure_within, sha256_file


CHAPTER_PREFIXES = {1: "第一章", 2: "第二章", 3: "第三章", 4: "第四章", 5: "第五章", 6: "第六章", 7: "第七章", 8: "第八章"}


def chapter_output_name(chapter_number: int, title_zh: str) -> str:
    """Build the canonical Unicode note name inside Python.

    Windows PowerShell 5 may corrupt non-ASCII native-process arguments. A
    derived name avoids sending Chinese text across that boundary.
    """
    prefix = CHAPTER_PREFIXES.get(chapter_number, f"第{chapter_number}章")
    return f"{prefix}-{title_zh}.md"


def vault_markdown(markdown: str) -> str:
    return re.sub(
        r"\]\(\.\./\.\./assets/((?:chapter-\d+/)?[^/)]+)\)",
        r"](assets/\1)",
        markdown,
    )


def sync_obsidian(
    markdown_path: Path,
    project_root: Path,
    vault: Path,
    destination: Path,
    *,
    copy_assets: bool = False,
    dry_run: bool = False,
    output_name: str | None = None,
) -> dict[str, Any]:
    vault = vault.resolve()
    target_dir = ensure_within(vault, vault / destination)
    if ".obsidian" in {part.lower() for part in target_dir.parts}:
        raise ValueError("refusing to write inside .obsidian")
    output_name = output_name or markdown_path.name
    target_markdown = target_dir / output_name
    content = vault_markdown(markdown_path.read_text(encoding="utf-8-sig"))
    actions = [str(target_markdown)]
    asset_pairs: list[tuple[Path, Path]] = []
    if copy_assets:
        for match in re.finditer(r"!\[[^]]*]\(\.\./\.\./assets/((?:chapter-\d+/)?[^/)]+)\)", markdown_path.read_text(encoding="utf-8-sig")):
            relative = Path(match.group(1))
            source = project_root / "assets" / relative
            if not source.is_file():
                raise FileNotFoundError(f"unable to resolve asset: {relative}")
            target = target_dir / "assets" / relative
            asset_pairs.append((source, target))
            actions.append(str(target))
    if dry_run:
        return {"dry_run": True, "actions": actions, "verified": False}
    target_dir.mkdir(parents=True, exist_ok=True)
    target_markdown.write_text(content, encoding="utf-8", newline="\n")
    for source, target in asset_pairs:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    verified = target_markdown.read_text(encoding="utf-8") == content
    asset_hashes = []
    for source, target in asset_pairs:
        same = sha256_file(source) == sha256_file(target)
        verified = verified and same
        asset_hashes.append({"source": str(source), "target": str(target), "same": same})
    return {"dry_run": False, "actions": actions, "verified": verified, "asset_hashes": asset_hashes}
