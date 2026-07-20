# EPUB 3 Pipeline

How the toolkit turns structured chapter JSON into a reflowable EPUB 3
that survives byte-for-byte reproducibility and ships with a working
table of contents, NCX, and page-list.

## Goals

1. **Reflowable** — no fixed-layout property anywhere.
2. **Renderable offline** — no JS, no remote CSS, no remote fonts.
3. **Deterministic** — two consecutive builds with the same inputs
   produce byte-identical archives.
4. **Footnote-standard** — `<aside epub:type="footnote">` with backlinks.
5. **Page-anchored** — printed-page anchors live in a `page-list` nav.
6. **CJK-friendly** — `dc:language=zh-CN`, `lang="zh-CN"` on every
   XHTML, no italics.

## Container layout

```text
the-cybernetic-brain-zh.epub
├── mimetype                          (ZIP_STORED, must be first)
├── META-INF/
│   └── container.xml
├── EPUB/
│   ├── package.opf
│   ├── nav.xhtml
│   ├── toc.ncx
│   ├── styles/
│   │   └── book.css
│   ├── text/
│   │   ├── titlepage.xhtml
│   │   ├── chapter-01.xhtml
│   │   └── ...
│   ├── images/
│   │   ├── cover.jpg
│   │   └── ...
│   └── package.opf (DC + meta + manifest + spine)
```

## Determinism mechanisms

| Source of nondeterminism | Mitigation |
|---|---|
| `uuid.uuid4()` for book UUID | Persist to `.ebook-translation/epub-identifier.txt` |
| `datetime.now()` for `dcterms:modified` | Persist to `.ebook-translation/epub-modified.txt` |
| ZIP entry timestamps | Force DOS `0x80000000` (1980-01-01) |
| Glob iteration order | `sorted()` throughout |
| Dict iteration order | Manifest built from sorted container JSON keys |

## Chapter 1 legacy adapter

The first chapter of a long translation project often exists only as a
hand-curated Markdown with standard `[^N]` footnotes, not as
structured JSON. The `legacy_chapter_adapter` parses:

- YAML frontmatter (`title`, `original_title`)
- Markdown headings / blockquotes / paragraphs
- Standard `[^N]` references
- `[^N]:` footnote definitions (including multi-line / indented continuations)
- Inline images `![alt](src)` and inline page anchors

It returns an `EpubChapter` with the same `block_id` shape as the
structured chapters, so the downstream renderer is unchanged.

## QA

`validate-epub` performs all of:

- mimetype first, ZIP_STORED
- All XHTML parses
- OPF metadata complete
- Manifest contains every referenced item
- Spine order matches chapter order
- nav.xhtml has `toc`, `page-list`, `landmarks`
- toc.ncx lists every spine item
- Page anchors are unique across the book
- Noteref/aside/backlink pairs match
- Internal hrefs resolve
- No `<script>` anywhere
- No external CSS/JS dependencies
- No visible italics (`<em>`, `<i>`)
- No `://`-style entries in the archive
- No leaked `source/original.pdf`

## Environmental limits (no fail)

- `EPUBCheck` (Java jar) is not bundled; not a blocker.
- Calibre is not installed; not a blocker.
- A real third-party EPUB reader is not in CI.

The internal validator covers the same structural checks that
EPUBCheck runs; external validators would only add cross-vendor
verification.
