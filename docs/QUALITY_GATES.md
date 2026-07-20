# Quality Gates

Every render leaves through one of the following gates. Each gate
returns one of `PASS`, `WARN`, `FAIL`.

| Gate | PASS | WARN | FAIL |
|---|---|---|---|
| `check-paragraph-reflow` | no paragraph split across page | only whitespace differences | any structural split |
| `check-page-anchors` | every printed page has one anchor | duplicate pages | missing printed pages |
| `check-image-anchors` | every body image anchored to its paragraph | one missing anchor | image lost |
| `check-bilingual-terms` | every PERSON has English on first occurrence | minor inconsistency | required PERSON missing English |
| `check-terminology-lock` | `preferred_zh` used everywhere; `deprecated_zh` gone; `context_required` honoured | minor edge case | `deprecated_zh` used in body |
| `check-footnotes` | every noteref has aside; every aside has backlink; no stranded markers | footnote defined without caller | noteref with no aside |
| `check-html-render` | no italics / no JS / no overflow at desktop+mobile | minor warning | blocker |
| `check-obsidian-sync` | chapter Markdown SHA matches Obsidian copy | one chapter drifted | chapters missing |
| `validate-epub` | all EPUB structural checks | warning but ship-able | blocker |

## Levels

- **PASS**: ship.
- **WARN**: may ship; record the warning in the per-chapter or per-book
  report and revisit before the next chapter.
- **FAIL**: block. Fix before re-rendering downstream.

## Where each gate runs

- All HTML / Markdown / Obsidian / terminology gates → `qa` subcommand
  with project root + chapter number.
- `validate-epub` → standalone `validate-epub --epub <EPUB>`.

## Pipeline invariant

A chapter does not move from `REVIEWED → RENDERED` until every gate
relevant to it is `PASS` or `WARN`.

A chapter does not move to `QA_PASS` until at least:

- `check-page-anchors` PASS
- `check-image-anchors` PASS
- `check-bilingual-terms` PASS
- `check-footnotes` PASS

The remaining gates may return `WARN` and still allow `OBSIDIAN_SYNCED`.
