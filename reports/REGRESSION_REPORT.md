# Regression Report

STATUS: PASS

## Current regression project

- Book: *The Cybernetic Brain: Sketches of Another Future*
- Chapter: “The Adaptive Brain / 适应性大脑”
- Project: `D:\home\conanxin\workspace\ebook-first-chapter-cn\the-cybernetic-brain`
- Fixture policy: short synthetic/derived fragments and metadata only; the PDF and full chapter text were not copied into the toolkit.

## Results

- Paragraph merging: PASS. Ten validated cross-page logical blocks each remain one stable paragraph with one internal page anchor.
- Page anchors: PASS. The current HTML still contains the exact internal PDF page sequence 13, 15, 17, 18, 19, 21, 22, 25, 26, 27; toolkit anchors do not create a new `<p>` or Markdown blank paragraph.
- Figure 1.1 placement: PASS. It follows a complete paragraph.
- Figure 1.2 placement: PASS. It remains after a complete paragraph and was not moved.
- Footnote interaction: PASS. Definitions and triggers are 1–7, every trigger has an inline binding, and the reusable component closes on second click, outside click and Escape.
- Duplicate footnote section: PASS. No `.notes-page`, `ol.footnotes` or appended footnote section.
- Visual italics: PASS. No `<em>`, `<i>` or effective `font-style: italic` in generated or current validated HTML.
- Bilingual names and terms: PASS. The 28 validated English search forms are present; the minimal structure-first fixture also passes first-occurrence checks.
- HTML/Markdown consistency: PASS. Toolkit fixture block_id order is identical in both renderers.
- Markdown/Obsidian consistency: PASS. Current project Markdown equals the Vault version after the expected portable image-path normalization.
- Image hashes: PASS. Figure 1.1 and Figure 1.2 match the frozen project and Vault SHA-256 values.
- Frozen outputs: PASS. Current HTML, project Markdown, Vault Markdown and both project images match the pre-change baseline hashes.
- Browser regression: PASS at 1366×768, 1920×1080 and 390×844; images loaded after lazy-load activation, no horizontal overflow, 7/7 note cards stayed inside the viewport, continuous pages had zero minimum page height, and no external requests occurred.
- Browser evidence: `reports/browser-validation.json`.

## Regression count

- Python tests: 28
- Failures: 0
- Skips: 0
- Browser viewport suites: 3
- Regressions found: 0
