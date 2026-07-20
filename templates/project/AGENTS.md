# Ebook translation project instructions

- Use the user skill `ebook-translation-zh`.
- Read `.ebook-translation/project.yaml` before taking project actions.
- Do not create a separate translation pipeline; call the canonical toolkit wrappers in `scripts/`.
- Keep book-specific exceptions in `.ebook-translation/paragraph-overrides.yaml`, `image-overrides.yaml`, or `terminology.tsv`.
- Put reusable rule changes in the central toolkit together with regression tests.
