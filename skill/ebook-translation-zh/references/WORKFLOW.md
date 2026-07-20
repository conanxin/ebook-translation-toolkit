# Canonical workflow

1. Locate the canonical toolkit and read `.ebook-translation/project.yaml`.
2. Freeze hashes of any protected existing outputs before repairs or migration.
3. Run `extract`; keep reliable native text and OCR only unreliable pages.
4. Run `detect`; apply explicit chapter page overrides only in project YAML.
5. Run `normalize`; review cross-page blocks and project paragraph overrides.
6. Run `extract-images`, `build-page-anchors`, and `anchor-images`; images must follow complete blocks. Multi-object panels sharing one printed figure number are extracted as one high-resolution composite bounded by their native PDF boxes.
7. Run `prepare`; translate each packet with previous/next context and the terminology table.
8. Write `chapter-XX-zh.json`; never maintain separate HTML and Markdown bodies.
9. Run `render`, then `qa`. Resolve every FAIL before sync.
10. Run `sync` only to the configured destination and compare Markdown and asset hashes.

For a whole book, run `plan-book` once, then close one chapter at a time: detect → normalize → extract-notes → prepare → translate → compile-translation → apply-translation → render → QA → sync. Translation may be reviewed in block, footnote, and caption JSONL workfiles; `compile-translation` must consume every workfile row exactly once and produce the strict map used to create `chapter-XX-zh.json`. Declare retained pre-normalization fragments under `.ebook-translation/translation-overrides.yaml` at `chapters.<chapter>.merge`; stable block IDs restart in every chapter, so merge rules must never leak across chapters. Update `reports/BOOK_TRANSLATION_PROGRESS.json` after every state transition. Resume at the first chapter that is not both `OBSIDIAN_SYNCED` and QA `PASS`; never rebuild a protected completed chapter. Run `render-index` after each newly synced chapter.

For later chapters, canonical chapter data lives in `intermediate/chapters/`. Native PDF line indentation must be used when coarse extracted blocks contain several logical paragraphs. Display-quote line boxes may be coalesced, but ordinary indented paragraphs must remain separate. Endnotes are sliced from `Notes to Chapter N` up to the next chapter heading, bound one-to-one to正文 markers, and translated before rendering.

When maintaining an already validated project, do not re-extract or freely retranslate. Make minimal structured changes and preserve the frozen outputs unless the task explicitly authorizes rebuilding them.
