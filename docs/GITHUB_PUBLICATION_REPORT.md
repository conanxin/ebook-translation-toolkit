# GitHub Publication Report — `ebook-translation-toolkit`

_Generated as part of the v0.2.0 publication and the v1.0.0 private example publication._

This document records the GitHub-side state of the **`ebook-translation-toolkit`** project and a summary pointer to its private reference example. **No proprietary derivative material lives in this repository.**

## Public toolkit repository

| Field | Value |
|---|---|
| GitHub repository | `conanxin/ebook-translation-toolkit` |
| Repository URL | <https://github.com/conanxin/ebook-translation-toolkit> |
| Visibility | **PUBLIC** |
| Default branch | `main` |
| `main` HEAD commit | `2974f38d2da03a4f95229a9d97b0399107e50bf0` |
| Latest tag | `v0.2.0` |
| `v0.2.0` tag commit | `2974f38d2da03a4f95229a9d97b0399107e50bf0` |
| Release URL | <https://github.com/conanxin/ebook-translation-toolkit/releases/tag/v0.2.0> |
| Test workflow | `.github/workflows/test.yml` (runs on push & pull_request) |
| Package workflow | `.github/workflows/package.yml` (builds wheel + sdist) |
| Pages | enabled — <https://conanxin.github.io/ebook-translation-toolkit/> (source: `main`, `/docs`) |

### v0.2.0 Release assets

| Asset | Size (bytes) | SHA-256 (GitHub-recorded) |
|---|---:|---|
| `ebook_translation_toolkit-0.2.0-py3-none-any.whl` | 80,853 | `403bee89d876ae9f8ddd23596a0313cfce79286232a716b9c005e3c11e15a3b8` |
| `ebook_translation_toolkit-0.2.0.tar.gz` | 84,679 | `303e56825c97306c139f1856850fc03abcd5944e57e4f0a4cac312461bd70402` |

### Test result (v0.2.0)

| Metric | Count |
|---|---:|
| Collected | 106 |
| Passed | 102 |
| Skipped (environment-only) | 4 |
| Failures | 0 |
| Errors | 0 |

## Private reference example (summary)

A separate **PRIVATE** example repository demonstrates the full pipeline end-to-end with one real translated book.

| Field | Value |
|---|---|
| Repository | `conanxin/the-cybernetic-brain-zh-example` |
| Visibility | **PRIVATE** |
| Default branch | `main` |
| Example version | v1.0.0 |
| Deliverables | HTML + Markdown + EPUB 3 (reflowable) |
| Chapters | 8 / 8 |
| Body images | 85 / 85 |
| Footnotes | 412 / 412 |
| Noteref / backlink | 412 / 412 each |
| Source EPUB SHA-256 | `158049c890f713dac8197b6285382492a172196b707fbd7f61204d0293a49fe6` |
| Shipped EPUB SHA-256 | `8c757f7cc7e6730b3fbe3767b07215cc0b7b429a307d0b5f9714466e543e3709` |
| Toolkit referenced | `ebook-translation-toolkit` v0.2.0 |

## Content boundaries (enforced and verified)

The public `ebook-translation-toolkit` repository **does NOT** contain:

- The full translated book.
- The final book EPUB.
- The original English PDF.
- The reference example's HTML, Markdown, or EPUB assets.
- Any chapter XHTML, body image, footnote or noteref/bookmark of the reference book.

The reference book assets (HTML / Markdown / EPUB 3) live **only** in the **PRIVATE**
`conanxin/the-cybernetic-brain-zh-example` repository and its private Release.

The original English PDF is **NOT** uploaded to any GitHub repository.

## Source-side protection (read-only verification)

| Artifact | Status |
|---|---|
| Original translation project (`<ORIGINAL_PROJECT>`) — HTML, Markdown, images, structured translations | unchanged |
| Obsidian book directory (`<OBSIDIAN_VAULT>`) — 8 chapter MD files + assets | unchanged |
| Source EPUB SHA-256 at `<ORIGINAL_PROJECT>/output/epub/the-cybernetic-brain-zh.epub` | `158049c890f713dac8197b6285382492a172196b707fbd7f61204d0293a49fe6` — verified post-publish |

## Pages (public documentation site)

GitHub Pages is enabled on the `main` branch served from `/docs`. The site is
static — `index.html` plus 13 Markdown files wired through direct
relative-path linking. No external dependency, no build framework.

| Field | Value |
|---|---|
| Site URL | <https://conanxin.github.io/ebook-translation-toolkit/> |
| Branch / path | `main` / `/docs` |
| HTTPS enforced | true |

## How to install / use

```bash
pip install ebook-translation-toolkit==0.2.0
ebook-translate --help
render-epub --help
validate-epub --help
```

See `docs/QUICK_START.md`, `docs/WORKFLOW.md`, and `docs/EPUB_PIPELINE.md`
for the full pipeline reference.

## Pointer to the case study

The richer, end-to-end case study narrative lives in:

- `docs/CASE_STUDY_THE_CYBERNETIC_BRAIN.md` — inside this public repo (full
  metrics, environment tables, terminology-locking rules, validation outcomes)
- `examples/the-cybernetic-brain/metrics.json` and `manifest-check.json` —
  generated check artifacts pointing to the full case
- The actual book assets live in the private companion repository (see summary
  table above); this public repository has no copy of the book assets.

---

_Generated as part of the 0.2.0 publication cycle. Cross-references stay in
sync with the private companion repository's publishing report._
