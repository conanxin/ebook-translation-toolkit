# Data Model

The structured chapter JSON is the single source of truth for every
downstream format.

## Top-level structure

```text
{
  "chapter": {
    "number": 1,
    "title_en": "The Adaptive Brain",
    "title_zh": "适应性大脑"
  },
  "blocks": [ ... ],
  "footnotes": [ ... ],
  "images": [ ... ]
}
```

## Blocks

```text
{
  "block_id": "p-001",
  "type": "paragraph | epigraph | subsection | image_ref",
  "translated_text": "...",
  "source_text": "...",
  "page_anchor": "13"
}
```

`block_id` is **stable across the entire book lifecycle**: it is the
key every renderer, footnote binder, image anchorer, and OB linkage
tool uses.

## Footnotes

```text
{
  "number": 6,
  "block_id": "p-001",
  "translated_text": "..."
}
```

Numbering is **per-chapter**, never global. The legacy Markdown adapter
emits `[^N]` footnotes and the structured chapter emits `[[FN:N]]` for
the renderer; both resolve to the same `<a id="chXX-fnref-NNN">` +
`<aside id="chXX-fn-NNN">` pairs.

## Images

```text
{
  "image_id": "figure-001",
  "path": "assets/chapter-01/figure-001.jpg",
  "caption_zh": "...",
  "caption_source": "...",
  "media_type": "image/jpeg"
}
```

## Schema file

The full JSON Schema lives at `schemas/structured-chapter.schema.json`.
Every project validates its own `chapter-XX-zh.json` against this file
before rendering.

## Invariants

1. `block_id` is unique within a chapter and never reused.
2. `page_anchor` may repeat (a chapter spans many pages) but the
   printed-page anchor is unique within the EPUB page-list.
3. `footnote.number` is unique within a chapter.
4. Image `image_id` is unique within a chapter.
5. Every footnote is referenced exactly once in the body of its
   chapter (counted by `[[FN:N]]` or `[^N]` markers).
