---
name: ebook-translation-zh
description: Translate English or other-language PDF ebooks into complete Simplified Chinese chapters while preserving logical paragraphs, images, footnotes, bilingual proper nouns, original reading structure, offline HTML, Markdown, and Obsidian output. Use for ebook translation, PDF chapter translation, book layout reconstruction, footnote popovers, PDF-to-Markdown, PDF-to-HTML, or Obsidian book translation projects. Do not use for short ordinary document summaries or translation requests that do not involve book structure.
---

# Ebook Translation ZH

Use one structure-first pipeline for every book. Do not recreate extraction, rendering, or synchronization logic per project.

## Required startup

1. Run `scripts/locate_toolkit.py` and use the first valid toolkit it returns.
2. Read the project `.ebook-translation/project.yaml` before acting.
3. Read [WORKFLOW.md](references/WORKFLOW.md) and the task-relevant standards. For paragraph, image, footnote, rendering, or acceptance work, read the matching reference completely.
4. Inspect the project terminology TSV and translation glossary before translating.

## Required data flow

Build `chapter-XX-source.json` before translation. Preserve one stable block per logical source paragraph; PDF page boundaries are internal anchors. Prepare context-rich translation packets, translate every block without summary or omission, and write `chapter-XX-zh.json` as the sole translated source of truth.

Render HTML and Markdown only from that translation JSON. Generate offline HTML with inline footnote popovers and no visual italics, portable Markdown with standard footnotes, guarded Obsidian output, and both machine- and human-readable QA reports.

Use `scripts/run_toolkit.py` or the toolkit wrappers. `all` may prepare packets but must never call an unauthorized external translation API; Codex performs the translation and writes the translated JSON.

## Change discipline

Book-specific exceptions belong in project overrides and terminology. A reusable rule change must update the central toolkit implementation, `standards/`, this Skill's corresponding `references/`, and regression tests together. Do not fork a new pipeline for an individual book.

## EPUB 3 packaging

When a project enables `render.epub.enabled` in `.ebook-translation/project.yaml`,
the toolkit additionally renders an EPUB 3 package from the same translation
JSON.  Triggers (use any):

- The user asks for an `.epub` or "EPUB version".
- `output/epub/<slug>-zh.epub` is missing but the structured translations and
  approved Markdown exist.
- A new terminology-lock or footnote change must propagate to the EPUB.

Workflow:

1. Run `ebook-translate render-epub --project-root <ROOT>` (or
   `pwsh scripts/ebook-translate.ps1 render-epub -ProjectRoot <ROOT>`).
2. Run `ebook-translate validate-epub --epub <EPUB>` immediately after.
3. For a long-running project, persist UUID and `dcterms:modified` to
   `.ebook-translation/epub-identifier.txt` and `.ebook-translation/epub-modified.txt`
   so consecutive builds are byte-identical.

Never edit files inside `output/epub/` directly.  The renderer is the only
authority; in-place edits make subsequent renders diverge.

See [EPUB_RENDERING_STANDARD.md](../../standards/EPUB_RENDERING_STANDARD.md).
