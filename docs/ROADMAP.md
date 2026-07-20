# Roadmap

What comes after v0.2.0. Items are listed in priority order. None are
committed; this is for planning only.

## v0.3 — Multi-language target

- Make `dc:language` driven by project config instead of hard-coded
  `zh-CN`.
- Translate the user-level Skill into English so non-Chinese projects
  can adopt it without manual translation.
- Add Japanese / Korean as first-class targets.

## v0.4 — Reader / cover preview

- Optional `epub-meta` integration when Calibre is installed.
- Optional `epubcheck` integration when the Java jar is bundled.
- Auto-screenshot of the unpacked EPUB's titlepage / first chapter /
  footnote round-trip in CI, persisted as `browser-screenshot.png`.

## v0.5 — Multi-book projects

- A second `book_progress.json` schema that tracks books in a series
  rather than chapters in one book.
- Optional `series.yaml` for VOL 1 / VOL 2 / VOL 3 translation
  pipelines.

## Long-term

- Push the structured chapter schema to JSON Schema 2020-12 with full
  `$ref` coverage.
- Add an `ebook-translate serve` HTTP service that exposes the
  renderer for browser-based QA without an extra build step.
- Move the user-level Skill from Codex-style `SKILL.md` to Hermes
  `instructions.md` while keeping a Codex-compatible mirror.
