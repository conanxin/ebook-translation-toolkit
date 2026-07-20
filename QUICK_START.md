# Quick Start

The shortest path from a fresh checkout to a passing render.

## PowerShell (Windows)

```powershell
git clone https://github.com/conanxin/ebook-translation-toolkit
cd ebook-translation-toolkit
pip install -e ".[test]"
pip install PyMuPDF PyYAML Jinja2 beautifulsoup4

# Substitute the toolkit path, project root, and book slug for your environment.
$t = '<TOOLKIT_ROOT>\scripts\ebook-translate.ps1'
& $t init       -Pdf '<PDF>' -ProjectRoot '<PROJECT_ROOT>' -ObsidianVault '<OBSIDIAN_VAULT>' -BookSlug '<slug>' -Chapter 1
& $t extract    -ProjectRoot '<PROJECT_ROOT>'
& $t detect     -ProjectRoot '<PROJECT_ROOT>'
& $t normalize  -ProjectRoot '<PROJECT_ROOT>'
& $t prepare    -ProjectRoot '<PROJECT_ROOT>' -Chapter 1

# Translate the packet with your preferred agent, then:
& $t apply-translation -ProjectRoot '<PROJECT_ROOT>' -Chapter 1 -Translations '<PROJECT_ROOT>\intermediate\chapters\chapter-01-translation-map.json'

& $t render       -ProjectRoot '<PROJECT_ROOT>' -Chapter 1
& $t render-epub  -ProjectRoot '<PROJECT_ROOT>'
& $t validate-epub -Epub '<PROJECT_ROOT>\output\epub\<slug>-zh.epub'
```

## Bash / WSL

```bash
git clone https://github.com/conanxin/ebook-translation-toolkit
cd ebook-translation-toolkit
pip install -e ".[test]"
pip install PyMuPDF PyYAML Jinja2 beautifulsoup4

scripts/ebook-translate.sh init       --pdf <PDF> --project-root <PROJECT_ROOT>
scripts/ebook-translate.sh extract    --project-root <PROJECT_ROOT>
scripts/ebook-translate.sh detect     --project-root <PROJECT_ROOT>
scripts/ebook-translate.sh normalize  --project-root <PROJECT_ROOT>
scripts/ebook-translate.sh prepare    --project-root <PROJECT_ROOT> --chapter 1

scripts/ebook-translate.sh apply-translation --project-root <PROJECT_ROOT> --chapter 1 \
    --translations <PROJECT_ROOT>/intermediate/chapters/chapter-01-translation-map.json

scripts/ebook-translate.sh render       --project-root <PROJECT_ROOT> --chapter 1
scripts/ebook-translate.sh render-epub  --project-root <PROJECT_ROOT>
scripts/ebook-translate.sh validate-epub --epub <PROJECT_ROOT>/output/epub/<slug>-zh.epub
```

## Python (no shell wrapper)

```bash
python -m ebook_translation_toolkit init \
    --pdf <PDF> --project-root <PROJECT_ROOT> --obsidian-vault <OBSIDIAN_VAULT> \
    --book-slug <slug> --chapter 1
python -m ebook_translation_toolkit extract  --project-root <PROJECT_ROOT>
python -m ebook_translation_toolkit detect   --project-root <PROJECT_ROOT>
python -m ebook_translation_toolkit normalize --project-root <PROJECT_ROOT>
python -m ebook_translation_toolkit prepare  --project-root <PROJECT_ROOT> --chapter 1

python -m ebook_translation_toolkit apply-translation \
    --project-root <PROJECT_ROOT> --chapter 1 \
    --translations <PROJECT_ROOT>/intermediate/chapters/chapter-01-translation-map.json

python -m ebook_translation_toolkit render       --project-root <PROJECT_ROOT> --chapter 1
python -m ebook_translation_toolkit render-epub  --project-root <PROJECT_ROOT>
python -m ebook_translation_toolkit validate-epub \
    --epub <PROJECT_ROOT>/output/epub/<slug>-zh.epub
```

## Run the toolkit's own test suite

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected on a clean checkout: `Ran 106 tests ... OK (skipped=4)`.
