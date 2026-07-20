# Development History

A faithful, 28-stage record of how this toolkit came to be. None of
the stages below are invented; each corresponds to a real piece of work
in the project log.

## Stages

1. **English PDF ingestion** — accept a single PDF; document the
   constraints (≤ 2 GB, encrypted PDF rejected, text layer optional).
2. **PDF text-layer detection** — per-page check via PyMuPDF; if
   density of glyphs is below threshold, dispatch to OCR.
3. **Structured text and page-block extraction** — `ebook-pages.jsonl`
   per page; one JSON record per page with optional OCR fallback text.
4. **Chapter boundary detection** — heuristic over headings + TOC +
   layout. 8/8 for the case-study book.
5. **PDF-page / logical-paragraph separation** — emit per-block
   `page_anchor` while keeping one block per logical paragraph.
6. **Cross-page paragraph repair** — strip the artificial newline
   inserted at PDF page boundaries when paragraph indentation matches
   the next paragraph's continuation.
7. **Image extraction + paragraph anchoring** — render-image-aware
   bbox extraction; bind image to nearest preceding paragraph; record
   `figure_id` and `image_id`.
8. **Translation-packet generation** — bundle a `source.json` slice
   with glossary slices and term-locks; emit one packet per chapter.
9. **Per-chapter translation** — external agent translates one
   `block_id` at a time; returns `translation-map.json`.
10. **Per-paragraph Chinese / English review** — second pass over each
    block; ensures proper-noun treatment and footnote rendering.
11. **Bilingual proper-noun rules** — table-driven rule set; emit
    "Chinese (English)" on first occurrence per chapter.
12. **Whole-book glossary** — accumulates from per-chapter packets;
    canonical place for term additions.
13. **Terminology lock** — project-level YAML; preferred_zh /
    deprecated_zh / context_required; gates re-runs of `qa`.
14. **Offline HTML rendering** — single file per chapter, inline
    popovers, no JS, no visible italics.
15. **Pagination vs continuous rendering** — supported via the
    `epub:type="pagebreak"` semantic and the page-list navigation.
16. **HTML in-place footnote interaction** — CSS-only toggle; the
    `<a epub:type="noteref">` and `<aside epub:type="footnote">` pair
    handle open / close / Escape.
17. **Markdown rendering** — standard `[^N]` footnotes; portable
    across all major Markdown readers.
18. **Obsidian sync** — name-safe note filenames; relative image
    paths; bidirectional cross-reference via `[[wikilinks]]`.
19. **Whole-book indices and progress restoration** — `book_progress.json`
    restores per-chapter state on a fresh checkout.
20. **EPUB 3 reflowable output** — `<aside epub:type="footnote">`
    inline; page anchors; chapter wrapping.
21. **EPUB navigation, NCX, page-list** — three-layer nav
    (`nav.xhtml` + `toc.ncx` + `page-list`) so old and new readers
    both work.
22. **EPUB standard footnotes** — `<aside epub:type="footnote">` with
    `<a epub:type="backlink">`; round-trip tested.
23. **Chapter 1 legacy adapter** — parses Markdown with standard
    `[^N]` footnotes when no `chapter-XX-zh.json` exists.
24. **EPUB deterministic build** — persist UUID and
    `dcterms:modified`; force DOS `0x80000000` ZIP timestamps.
25. **Internal EPUB validator** — no EPUBCheck dependency; covers
    every structural check EPUBCheck runs.
26. **Browser XHTML probe** — Playwright headless Chromium; verifies
    live rendering, horizontal overflow, footnote round-trip.
27. **Automatic tests and regression guards** — 106 tests; new
    behaviour is always paired with a regression test.
28. **GitHub publication and re-use** — public toolkit + private
    case-study repo; reproducible from a clean checkout.

## Real problems hit along the way

For each: what the bug was, where it lived, what fixed it.

- **PDF page boundaries split paragraphs.** Cross-page repair missed
  paragraph-indentation continuation. *Fix:* per-book column-detection
  flag, plus a guarded re-indent.
- **Images dropped into the wrong paragraph.** The image-bbox
  heuristic was greedy. *Fix:* bbox closer to the *preceding*
  paragraph, not the next.
- **A long English paragraph got split into multiple Chinese
  blocks.** Translator agent over-zealously split. *Fix:* the
  translation packet enforces one-paragraph-one-block at the protocol
  level; agents that violate it are reverted by the apply step.
- **HTML footnote could only be seen at end of chapter.** The
  renderer used back-of-book layout. *Fix:* `<aside epub:type="footnote">`
  inline, immediately after the referencing block.
- **HTML rendered an italic styled source.** Source Markdown contained
  `*foo*`. *Fix:* normalisation strips stray asterisks before
  rendering; QA gate `check-html-render` enforces no `<em>` / `<i>`.
- **Person names missing English in first occurrence.** Translator
  forgot. *Fix:* `check-bilingual-terms` gate; bilingual rules table.
- **Cross-chapter person-name drift (Stuart Kauffman, 斯图亚特 vs
  斯图尔特).** Inconsistent translator output. *Fix:* terminology
  lock YAML; `check-terminology-lock` gate; deprecated_zh marked.
- **Heidegger term drift (Gestell / enframing / revealing rendered as
  框定 + 显露 vs 座架 + 揭示).** Philosophy-context vs ordinary
  context conflated. *Fix:* `context_required` term lock with
  Heidegger-explicit gating.
- **Chapter 1 had no `chapter-01-zh.json`.** It was hand-curated
  Markdown from the pilot. *Fix:* legacy Markdown adapter.
- **Chapter 1 Markdown footnotes not recognised by the renderer.**
  Adapter emitted blocks; renderer expected `[[FN:N]]`. *Fix:*
  `_MD_FN_REF_PATTERN` + number-only `fn_number_lookup` fallback.
- **Renderer dict / dataclass mixed-mode crash.** Legacy chapter had
  images stored as dicts; structured chapters had dataclasses.
  *Fix:* `_*_id`/`_*_file_name`/`_*_caption` helpers handle both
  shapes.
- **Explicit footnote numbers positionally renumbered.** `[[FN:6]]`
  became `@@FN:1@@`. *Fix:* `_normalize_footnote_markers` honours an
  explicit numeric marker before falling back to positional.
- **`unittest discover` skipped `test_epub_package.py`.** Tests were
  module-level functions. *Fix:* rewrite as `TestEpubPackage(unittest.TestCase)`;
  add `tests/__init__.py`.
- **`dcterms:modified` made the EPUB hash change on every build.**
  Rebuilding twice produced different SHA-256. *Fix:* persist
  `epub-modified.txt`; deterministic ZIP timestamps.
- **External-content vs rendering-dependency URL distinction.** The
  validator reported 8 `EXTERNAL_LINK` warnings. *Fix:* classify as
  `CONTENT_EXTERNAL_LINKS` (footnote citation URLs are content, not
  rendering); internal validator reports them but does not block.

None of the problems above required rewriting the toolkit's data
model; they all lived in the renderers or in the QA gates.

## Why this history matters

This is what got cemented into `standards/` so the next book is built
faster.
