# Example: The Cybernetic Brain (case study)

This folder is the **public** summary of a long-form case study. The
complete translated book, including the final EPUB, lives in the
**private** companion repository `conanxin/the-cybernetic-brain-zh-example`.

What this folder ships:

- `project.example.yaml` — minimal scrubbed project configuration
- `terminology-lock.example.yaml` — 3 example locked terms
- `metrics.json` — final numbers from the book
- `manifest-check.json` — file inventory the verifier checks against
- `expected-structure.txt` — tree of what the case-study repo contains
- `CASE_STUDY.md` — short-form case study (this folder)
- `README.md` — this file
- `screenshots/` — small previews (intentionally limited)

What this folder does NOT ship:

- The original PDF
- The full English source text
- The full Chinese translation
- The 85 body images
- The final EPUB

## Quick links

- Long-form case study: [`docs/CASE_STUDY_THE_CYBERNETIC_BRAIN.md`](../../docs/CASE_STUDY_THE_CYBERNETIC_BRAIN.md)
- Development history: [`docs/DEVELOPMENT_HISTORY.md`](../../docs/DEVELOPMENT_HISTORY.md)
- Architecture: [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md)
- Workflow: [`docs/WORKFLOW.md`](../../docs/WORKFLOW.md)

## Re-using this configuration

```bash
# Copy project.example.yaml to your own project:
cp examples/the-cybernetic-brain/project.example.yaml /<MY_PROJECT>/.ebook-translation/project.yaml
cp examples/the-cybernetic-brain/terminology-lock.example.yaml /<MY_PROJECT>/.ebook-translation/terminology-lock.yaml

# Edit <MY_PROJECT>/.ebook-translation/project.yaml to point at your own book:
#   book.title, book.author, book.title_zh, source.pdf, language, render.* , epub.*
```

## Validation

The `manifest-check.json` in this folder is the source of truth that
`the-cybernetic-brain-zh-example/scripts/verify-example.py` validates
against. If you fork the case-study repo, do not edit the manifest's
checksums without re-running the build.
