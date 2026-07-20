# Changelog

## 0.2.0 - 2026-07-20

- Added generic EPUB 3 builder, validator, and project-level rendering pipeline.
- Added reflowable EPUB CSS with offline-safe defaults, dark-mode support, no embedded fonts.
- Added nav.xhtml (toc + page-list + landmarks) and EPUB 2-compatible toc.ncx.
- Added project-side chapter-01 legacy Markdown adapter that preserves approved translation.
- Added `check-terminology-lock`, `render-epub`, `validate-epub` subcommands.
- Added persistent EPUB UUID in `.ebook-translation/epub-identifier.txt` for deterministic builds.
- Added EPUB RENDERING STANDARD and supporting fixtures, regression tests, and asset catalog.

### 0.2.0 publication - 2026-07-21

- Made the toolkit publicly available on GitHub as `conanxin/ebook-translation-toolkit`.
- Added LICENSE (MIT) at the repo root.
- Added `.github/workflows/test.yml` (Python 3.12, unit tests, CLI smoke) and `.github/workflows/package.yml` (wheel + sdist + GitHub Release on `v*` tag).
- Added `docs/` with `INDEX`, `WORKFLOW`, `ARCHITECTURE`, `DATA_MODEL`, `TRANSLATION_PIPELINE`, `HTML_AND_OBSIDIAN`, `EPUB_PIPELINE`, `QUALITY_GATES`, `TROUBLESHOOTING`, `CASE_STUDY_THE_CYBERNETIC_BRAIN`, `DEVELOPMENT_HISTORY`, `ROADMAP`.
- Added `examples/the-cybernetic-brain/` with scrubbed project config, terminology lock sample, metrics, manifest, expected structure, screenshots placeholder, and short case study.
- Added `docs/index.html` for GitHub Pages.
- Replaced machine paths in public docs with `<PROJECT_ROOT>` / `<TOOLKIT_ROOT>` / `<OBSIDIAN_VAULT>` placeholders.
- Test suite fixed: `test_epub_package.py` rewritten as `TestEpubPackage(unittest.TestCase)` so `python -m unittest discover` enumerates all 22 tests.

## Unreleased

- Added resumable whole-book planning, progress state transitions, per-chapter directories, and offline book indices.
- Added native-PDF indentation-aware paragraph reconstruction so coarse PDF blocks no longer merge distinct logical paragraphs.
- Added chapter-endnote extraction and one-to-one inline reference binding across notes pages.
- Added translated page/footnote marker validation, translation-map application, scoped output naming, and multi-viewport browser acceptance rules.

## 0.1.0 - 2026-07-19

- Established the canonical structure-first PDF ebook translation pipeline.
- Added native-text-aware extraction, chapter detection, cross-page paragraph reflow, internal page anchors, complete-block image anchoring, context-rich translation packets, bilingual terminology checks, offline HTML, portable Markdown, guarded Obsidian sync, and machine-readable QA.
- Added the inline accessible footnote popover proven in *The Cybernetic Brain* Chapter 1.
- Added Windows and WSL user Skill installation, synchronization, wrappers, and regression fixtures.