# AGENTS — Agent Operating Manual

This file is for any AI agent (Codex / Hermes / Claude Code / Cursor / …) and
for human maintainers working on the toolkit itself.

## What this repo is

A **structure-first PDF ebook translation pipeline**. The single source of
truth for every downstream format is `chapter-XX-zh.json`. Anything that
bypasses that JSON is a bug.

## Non-negotiable rules

1. **Never** modify a project's translation JSON, HTML, Markdown,
   images, or EPUB **from inside the toolkit source tree**. The toolkit
   is project-agnostic.
2. **Never** ship a book change as a code change. A new translator
   policy belongs in `standards/`, never in a book's repo.
3. **Never** add an LLM as a runtime dependency. The toolkit does not
   translate on its own — it prepares structured input that an external
   agent or human translator fills in.
4. **Never** commit `.venv`, `dist/`, `build/`, `*.egg-info/`,
   `__pycache__`, `.pytest_cache`, `*.pdf`, `*.epub`, the project's
   `intermediate/`, `output/`, or `source/`, or any path containing a
   machine path under `D:\` or `/mnt/d/` or `/home/<user>/`.
5. **Never** run `git push --force` against any branch that was once
   pulled from the public repo.

## Change discipline

A reusable rule change must update **all four** of:

- central implementation under `src/ebook_translation_toolkit/`
- the relevant entry under `standards/`
- the relevant entry in `skill/ebook-translation-zh/references/`
- a regression test under `tests/`

Do not fork a parallel pipeline for an individual book.

## Test conventions

- All tests live under `tests/` and use `unittest.TestCase`.
- Tests must be discoverable by `python -m unittest discover -s tests -p "test_*.py"`.
- Never silently skip a test to make CI green. Use `@unittest.skip` with
  a reason and document it in the report.
- Book-specific fixtures live in `tests/fixtures/`. They must be tiny
  and self-contained.
- When refactoring, the test count must not decrease. New tests may
  appear because new behaviour was added; old tests must keep passing.

## Documentation conventions

- Every public command-line subcommand is documented in the relevant
  `docs/` file and mirrored in the user-level Skill under
  `skill/ebook-translation-zh/`.
- Every public standard lives under `standards/` as a single Markdown
  file with a stable heading order.
- `CHANGELOG.md` records user-visible changes per release. CI does
  **not** read it — humans do. Keep it human.

## EPUB packaging rules

- Reflowable only. No fixed-layout.
- `mimetype` first, ZIP_STORED.
- `dcterms:modified` is **persisted** in
  `.ebook-translation/epub-modified.txt` so byte-identical consecutive
  builds remain possible.
- UUID is **persisted** in `.ebook-translation/epub-identifier.txt`.
- Footnotes use `<aside epub:type="footnote">` with a `<a epub:type="backlink">`.
- Page anchors are inline `<span id="chXX-page-NN" epub:type="pagebreak">`.
- No JavaScript. No external rendering resources. No visible italics.

## Workflow

1. Run `python -m unittest discover -s tests -p "test_*.py" -v`. Must
   pass before any commit.
2. Update `CHANGELOG.md` under the next version heading.
3. Update `VERSION` and `pyproject.toml` if the change is user-visible.
4. Tag `vX.Y.Z` only after the GitHub Actions pipeline is green.

## Release checklist

- [ ] Tests pass locally and on CI
- [ ] `CHANGELOG.md` updated
- [ ] `VERSION` bumped
- [ ] `pyproject.toml` version matches
- [ ] Wheel builds and installs
- [ ] `ebook-translate --help` runs from a fresh install
- [ ] Release notes drafted (link to case study metrics)
