from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path

from .epub_models import EpubBook, EpubChapter, EpubFootnote, EpubImage


_MIME_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}

_FIGURE_PATTERN = re.compile(r"\[\s*图\s*(\d+(?:\.\d+)?)\s*\]")
_FN_PATTERN = re.compile(r"\[\s*FN\s*:\s*([^\]]+)\s*\]")
_MD_FN_REF_PATTERN = re.compile(r"\[\^(\d+)\]")
_PAGE_PATTERN = re.compile(r"\[\[\s*PAGE\s*:\s*([^|\]]+)(?:\|([^\]]+))?\s*\]\]")


def _media_type_for(path: Path) -> str:
    return _MIME_BY_SUFFIX.get(path.suffix.lower(), "application/octet-stream")


def _block_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n{2,}", text)
    return [p.strip() for p in parts if p.strip()]


def _normalize_footnote_markers(text: str) -> tuple[str, list[str]]:
    seen: dict[str, int] = {}
    order: list[str] = []

    def replace_fn(match: re.Match[str]) -> str:
        marker = match.group(1).strip()
        # Honour an explicit numeric marker when possible so that
        # references like ``[[FN:6]]`` round-trip to ``@@FN:6@@``
        # instead of being renumbered positionally.  Non-numeric markers
        # fall back to per-block positional numbering, which is what
        # legacy text without explicit numbers expects.
        try:
            explicit = int(marker)
            seen.setdefault(marker, explicit)
            order.append(marker)
            return f"@@FN:{explicit}@@"
        except ValueError:
            seen.setdefault(marker, len(seen) + 1)
            order.append(marker)
            return f"@@FN:{seen[marker]}@@"

    cleaned = _FN_PATTERN.sub(replace_fn, text)

    # Also recognise standard Markdown footnote references (``[^N]``)
    # used by the legacy Chapter 1 markdown.  They translate to the
    # same ``@@FN:<n>@@`` marker so downstream rendering is identical.
    def replace_md_ref(match: re.Match[str]) -> str:
        marker = match.group(1).strip()
        order.append(marker)
        return f"@@FN:{marker}@@"

    cleaned = _MD_FN_REF_PATTERN.sub(replace_md_ref, cleaned)
    # Strip the legacy ``[^N]:`` definition lines that have already been
    # turned into structured ``EpubFootnote`` records — they should not
    # appear in the body of the rendered XHTML.
    cleaned = re.sub(r"^\s*\[\^\d+\]:\s.*$", "", cleaned, flags=re.M)
    return cleaned, order


def _normalize_image_markers(text: str) -> tuple[str, list[str]]:
    order: list[str] = []

    def replace_img(match: re.Match[str]) -> str:
        marker = f"fig-{match.group(1).strip()}"
        order.append(marker)
        return f"@@IMG:{marker}@@"

    cleaned = _FIGURE_PATTERN.sub(replace_img, text)
    return cleaned, order


def _normalize_page_markers(text: str) -> tuple[str, list[tuple[str, str]]]:
    seen: dict[tuple[str, str], int] = {}
    order: list[tuple[str, str]] = []

    def replace_page(match: re.Match[str]) -> str:
        pdf_page = match.group(1).strip()
        printed = (match.group(2) or pdf_page).strip()
        key = (pdf_page, printed)
        seen.setdefault(key, len(seen) + 1)
        order.append((pdf_page, printed))
        return f"@@PAGE:{seen[key]}@@"

    cleaned = _PAGE_PATTERN.sub(replace_page, text)
    return cleaned, order


def _strip_leading_block_artifacts(text: str) -> str:
    text = re.sub(r"^\s*@@PAGE:\d+@@", "", text)
    text = re.sub(r"^\s*@@FN:\d+@@", "", text)
    text = re.sub(r"^\s*@@IMG:[^@]+@@", "", text)
    return text.lstrip()


def build_chapter_text_blocks(chapter: EpubChapter) -> list[dict[str, object]]:
    """Convert a structured chapter into ordered XHTML-shaped segments.

    The output of this helper is consumed by `epub_package.py` which renders
    the actual XHTML.  Each segment is one of:

    - {"type": "paragraph", "text": str, "block_id": str}
    - {"type": "epigraph", "lines": list[str]}
    - {"type": "subsection", "title_zh": str, "title_en": str}
    - {"type": "image", "marker": str}
    - {"type": "footnote_ref", "marker": str}
    - {"type": "pagebreak", "printed_page": str, "pdf_page": str}

    Cross-page markers attached to source blocks are preserved as
    inline pagebreaks and are never emitted as standalone paragraphs.
    """

    segments: list[dict[str, object]] = []
    seen_figures: set[str] = set()

    for block in chapter.blocks:
        text = (block.get("translated_text") or "").strip()
        if not text:
            continue
        block_id = block.get("block_id", "")
        block_type = block.get("type") or "paragraph"

        # Normalize inline artifacts into markers, preserving ordering
        cleaned, fn_order = _normalize_footnote_markers(text)
        cleaned, img_order = _normalize_image_markers(cleaned)
        cleaned, page_order = _normalize_page_markers(cleaned)

        if block_type == "epigraph":
            lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
            segments.append({"type": "epigraph", "lines": lines, "block_id": block_id})
        else:
            paragraphs = _block_paragraphs(cleaned)
            for paragraph in paragraphs:
                paragraph, _page_inline = _normalize_page_markers(paragraph)
                paragraph = _strip_leading_block_artifacts(paragraph)
                if not paragraph:
                    continue
                segments.append({"type": "paragraph", "text": paragraph, "block_id": block_id})

        for pdf, printed in page_order:
            segments.append(
                {"type": "pagebreak", "printed_page": printed, "pdf_page": pdf, "block_id": block_id}
            )
        for marker in img_order:
            segments.append({"type": "image_ref", "marker": marker, "block_id": block_id})
        for marker in fn_order:
            segments.append({"type": "footnote_ref", "marker": marker, "block_id": block_id})
        seen_figures.update(img_order)

    return segments


def build_footnote_id(chapter_number: int, number: int) -> str:
    return f"ch{chapter_number:02d}-fn-{number:03d}"


def build_footnote_ref_id(chapter_number: int, number: int) -> str:
    return f"ch{chapter_number:02d}-fnref-{number:03d}"


def build_page_anchor_id(chapter_number: int, pdf_page: str, printed_page: str) -> str:
    safe_printed = re.sub(r"[^0-9A-Za-z]+", "-", printed_page).strip("-") or pdf_page
    return f"ch{chapter_number:02d}-page-{safe_printed}"


def build_image_id(chapter_number: int, figure_id: str) -> str:
    return f"ch{chapter_number:02d}-img-{figure_id}"


def compute_deterministic_zip_timestamp(epoch: int = 0x80000000) -> int:
    """Return a fixed ZIP DOS timestamp.

    Using 1980-01-01 ensures deterministic ordering and reproducibility.
    """
    return epoch


def deterministic_path(relative: str) -> str:
    """Normalize relative path inside the EPUB container.

    EPUB forbids absolute paths and parent directory traversal.  This helper
    raises if either condition is detected so the build fails fast.
    """

    normalized = relative.replace("\\", "/").lstrip("/")
    if normalized.startswith("../") or "/../" in normalized or normalized == ".." or normalized.startswith(".."):
        raise ValueError(f"unsafe EPUB path: {relative}")
    return normalized


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def detect_zip_anomalies(zip_path: Path) -> list[str]:
    anomalies: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        first = zf.namelist()[0]
        if first != "mimetype":
            anomalies.append(f"first entry must be 'mimetype', got '{first}'")
        info = zf.getinfo("mimetype")
        if info.compress_type != zipfile.ZIP_STORED:
            anomalies.append("mimetype must be uncompressed (ZIP_STORED)")
        if info.file_size != len("application/epub+zip"):
            anomalies.append("mimetype content must be exactly 'application/epub+zip'")
        for name in zf.namelist():
            if name.startswith("/") or "://" in name:
                anomalies.append(f"absolute or URL path entry: {name}")
            if name.startswith("../") or "/../" in name or name == "..":
                anomalies.append(f"parent-traversal path entry: {name}")
        bad = zf.testzip()
        if bad is not None:
            anomalies.append(f"corrupt entry: {bad}")
    return anomalies


def collect_body_images(book: EpubBook) -> list[EpubImage]:
    return book.images


def chapter_image_lookup(book: EpubBook) -> dict[int, dict[str, EpubImage]]:
    out: dict[int, dict[str, EpubImage]] = {}
    for image in book.images:
        out.setdefault(image.chapter, {})[image.figure_id] = image
    return out