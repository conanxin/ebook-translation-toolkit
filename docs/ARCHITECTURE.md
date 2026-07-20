# Architecture

The toolkit is split into a small number of layers; each layer talks
only to the layer directly below it.

```mermaid
flowchart TB
  subgraph L1[CLI / Driver Layer]
    C[cli.py]
    W[scripts/ebook-translate.{sh,ps1}]
  end
  subgraph L2[Project init / helpers]
    U[utils.py]
    PC[project_check.py]
  end
  subgraph L3[Pipeline stages]
    EX[pdf_extract.py]
    CD[chapter_detect.py]
    NR[paragraph_normalize.py]
    TP[translation_packets.py]
    AT[apply_translation.py]
    CT[compile_translation.py]
    IMD[image_anchors.py]
    PA[page_anchors.py]
    FN[footnotes.py / endnotes.py]
    BT[bilingual_terms.py]
    TL[terminology_lock.py]
  end
  subgraph L4[Renderers]
    HR[html_render.py]
    MR[markdown_render.py]
    OS[obsidian_sync.py]
    EP[render_epub.py<br/>render_epub_book.py<br/>legacy_chapter_adapter.py<br/>epub_models / notes / navigation / package / validator]
  end
  subgraph L5[Shared models]
    M[models.py<br/>structured-chapter-schema.json]
    S[schemas/]
  end
  C --> L3
  W --> C
  L3 --> M
  L3 --> S
  L4 --> M
```

## Module map

- `cli.py` — argparse dispatcher. Every subcommand documented in [WORKFLOW.md](WORKFLOW.md).
- `pdf_extract.py` — PyMuPDF text-layer detection. OCR fallback.
- `chapter_detect.py` — heuristic chapter-boundary detection from headers + layout.
- `paragraph_normalize.py` — cross-page paragraph repair; emits `<span epub:type="pagebreak">` anchors.
- `translation_packets.py` / `apply_translation.py` — packet construction and translation write-back.
- `compile_translation.py` — combines chapters into a single book artefact.
- `image_anchors.py` — paragraph-level image anchoring using PDF image bbox.
- `page_anchors.py` — page anchor registry.
- `footnotes.py` / `endnotes.py` — footnote detection and ordering.
- `bilingual_terms.py` — proper-noun bilingual rules.
- `terminology_lock.py` — preferred_zh / deprecated_zh / context_required checks; YAML-driven.
- `html_render.py` — single-file HTML with inline popovers and no visual italics.
- `markdown_render.py` — portable Markdown with standard footnotes.
- `obsidian_sync.py` — name-safe notes, image copies, cross-references.
- EPUB stack:
  - `epub_models.py` — `EpubBook`, `EpubChapter`, `EpubFootnote`, `EpubImage`.
  - `epub_notes.py` — normalization, footnote IDs, image IDs, page IDs.
  - `epub_navigation.py` — `nav.xhtml` + `toc.ncx`.
  - `epub_package.py` — `write_epub` (mimetype-first ZIP, deterministic).
  - `epub_validator.py` — internal validator (no EPUBCheck dependency).
  - `render_epub.py` — XHTML rendering for a single chapter.
  - `render_epub_book.py` — orchestrates a full book build.
  - `legacy_chapter_adapter.py` — parses legacy Markdown `[^N]` footnotes for chapter 1.

## Single source of truth

Every renderer reads `chapter-XX-zh.json`. The renderer never writes
back to the structured JSON. The renderer never reads from the
translator's raw output.

## Determinism

Three persisted state files in `.ebook-translation/`:

- `epub-identifier.txt` — UUIDv4 generated once, reused forever.
- `epub-modified.txt` — first-run timestamp, never regenerated unless reset.
- `terminology-lock.yaml` — commit-friendly.

ZIP entry timestamps are forced to `0x80000000` (1980-01-01) so the
archive is byte-identical across consecutive builds.
