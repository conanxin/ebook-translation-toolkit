# Troubleshooting

Symptom → diagnosis → fix cookbook. Read top-down for the most common
issues first.

## "EPUB chapter 1 has zero footnotes but the Markdown has 7"

**Symptom**: `validate-epub` reports ch01 with 0 `epub:type="footnote"`
and the chapter shows `[^N]` literals in the body.

**Cause**: the renderer does not match the legacy Markdown `[^N]`
syntax against the structured `[[FN:N]]` syntax.

**Fix**: confirm `epub_notes._MD_FN_REF_PATTERN` is present in
`src/ebook_translation_toolkit/epub_notes.py` and that
`_normalize_footnote_markers` substitutes both shapes. Re-render.

## "Two consecutive EPUB builds produce different SHA-256"

**Symptom**: `validate-epub --epub A.epub` and `validate-epub --epub B.epub` differ.

**Cause**: `dcterms:modified` is being regenerated on each build.

**Fix**: confirm `.ebook-translation/epub-modified.txt` exists. If not,
re-run `render-epub` once to seed it.

## "PDF page boundaries split my paragraphs"

**Symptom**: a logical paragraph in the source becomes two blocks in
`chapter-XX-source.json`.

**Cause**: `paragraph_normalize.py` not aware of the source's column
width or font.

**Fix**: check that the PDF extraction flag for column-detection is on.
Re-run `extract --column-detection on`.

## "Footnote `<aside>` is empty in EPUB chapter 1"

**Symptom**: 7 noterefs but 0 asides.

**Cause**: legacy adapter registers every footnote against the last
block (`blocks[-1]`). Renderer lookup by `(block_id, N)` fails.

**Fix**: confirm `fn_number_lookup` fallback is in `render_chapter_xhtml`.
If the fallback is missing, footnote asides won't appear when block_id
resolution fails.

## "Renderer crashes with `'EpubImage' object is not subscriptable`"

**Symptom**: `TypeError: 'EpubImage' object is not subscriptable` in
`render_epub.py`.

**Cause**: legacy code path mixing dict-style and dataclass-style
access.

**Fix**: confirm `render_epub.py` uses `_*_id`, `_*_file_name`,
`_*_mime_type` helpers which handle both dict and dataclass shapes.

## "`unittest discover` skips `test_epub_package.py`"

**Symptom**: 84 tests reported, no EpubPackage tests.

**Cause**: tests defined as module-level functions. CPython's
`unittest.TestLoader.discover` only enumerates `test_*` methods inside
`unittest.TestCase` subclasses.

**Fix**: rewrite as `class TestX(unittest.TestCase): def test_y(self): ...`.
Create `tests/__init__.py` if needed.

## "First footnote in a chapter renders N=1 instead of chapter-local number"

**Symptom**: footnote anchors are off-by-one against the chapter
translation.

**Cause**: `_normalize_footnote_markers` was positionally renumbering
explicit `[[FN:N]]` references.

**Fix**: in `src/ebook_translation_toolkit/epub_notes.py`, confirm the
`replace_fn` closure honours explicit numeric markers before falling
back to positional numbering.

## "HTML shows visible italics"

**Symptom**: `<em>` or `<i>` in the rendered HTML.

**Cause**: structured JSON or Markdown contained literal italics.

**Fix**: normalize during Markdown rendering. Re-run `render-markdown`
and `render-html`.

## "HTML footnote popover does not toggle"

**Symptom**: clicking the footnote number does nothing.

**Cause**: the inline `<a epub:type="noteref">` does not target an
`id` attribute (or targets the wrong anchor).

**Fix**: confirm `epub_notes.build_footnote_id(chapter, n)` returns
the same id as the `<a epub:type="noteref" href="#...">` in the body.

## "EPUBCheck finds warnings about external links"

**Symptom**: 8 `EXTERNAL_LINK` warnings during external validation.

**Expected**: footnote URLs are `CONTENT_EXTERNAL_LINKS`, not
rendering dependencies. The internal validator categorises them
correctly; external EPUBCheck does not.

**Mitigation**: leave them. Disabling network on the reader still
renders the entire book. The warning is informational, not a blocker.
