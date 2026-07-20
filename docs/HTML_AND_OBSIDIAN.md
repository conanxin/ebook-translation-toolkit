# HTML and Obsidian rendering contract

The toolkit renders both HTML and Obsidian-flavoured Markdown from the
same `chapter-XX-zh.json`.

## HTML contract

- Single file per chapter: `output/html/chapter-XX-zh.html`.
- Inline footnote popovers (CSS-only, no JavaScript).
- Page anchors are `<span id="chXX-page-NN" epub:type="pagebreak">`.
- Each chapter is wrapped in `<section id="chapter-XX" epub:type="chapter">`.
- Footnotes are `<aside epub:type="footnote">` inline at the bottom of
  the body block they belong to (not at the end of the file).
- One book-wide `index.html` provides reading order and TOC links.
- No visible italics, ever.
- No JS, ever. (Verified by `test_no_javascript`.)
- Works opened via `file://` with no internet.

## Obsidian contract

- Each chapter → one Markdown note in the Obsidian vault.
- Filenames are sanitized (`/` and special characters removed).
- Notes carry YAML frontmatter with chapter metadata.
- Wiki-style `[[chapter-name]]` cross-references use the sanitized name.
- Images are copied into a sibling `assets/chapter-XX/` directory and
  referenced by relative path.

## Why two formats from one JSON

- HTML is for **offline reading on any device** (single file, no
  plugins).
- Obsidian is for **knowledge work** — the reader keeps the book
  alongside their own notes and bi-directional links.

Both formats MUST stay in lockstep. The QA gates compare the live HTML
rendering against the structured JSON and against the Obsidian copy.

## Rendering rules

1. No italics. (Standards file: `standards/HTML_RENDERING_STANDARD.md`.)
2. No JS. (QA gate: `check-html-render`.)
3. Footnote markers count as `<a epub:type="noteref">` and link to
   `<aside epub:type="footnote">` blocks. Backlinks use
   `<a epub:type="backlink">`.
4. Page anchors render as empty inline `<span>` elements with the
   `epub:type="pagebreak"` semantic.
5. Long English names, URLs, and titles wrap on whitespace — no
   horizontal overflow at 1366×768 or 390×844.
