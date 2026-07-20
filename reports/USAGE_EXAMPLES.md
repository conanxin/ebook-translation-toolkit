# Usage Examples

## Initialize

```powershell
D:\home\conanxin\workspace\ebook-translation-toolkit\scripts\ebook-translate.ps1 init `
  -Pdf "D:\Books\book.pdf" `
  -ProjectRoot "D:\home\conanxin\workspace\ebook-first-chapter-cn\book-slug" `
  -ObsidianVault "D:\OBSIDIAN_NOV\conanxin" `
  -BookSlug "book-slug" -Chapter 1
```

```bash
/mnt/d/home/conanxin/workspace/ebook-translation-toolkit/scripts/ebook-translate.sh init \
  --pdf /mnt/d/Books/book.pdf \
  --project-root /mnt/d/home/conanxin/workspace/ebook-first-chapter-cn/book-slug \
  --obsidian-vault /mnt/d/OBSIDIAN_NOV/conanxin \
  --book-slug book-slug --chapter 1
```

## Extract, detect, normalize, and prepare

```powershell
$tool = 'D:\home\conanxin\workspace\ebook-translation-toolkit\scripts\ebook-translate.ps1'
& $tool extract -ProjectRoot 'D:\path\book-slug' -Chapter 1
& $tool detect -ProjectRoot 'D:\path\book-slug' -Chapter 1
& $tool normalize -ProjectRoot 'D:\path\book-slug' -Chapter 1
& $tool prepare -ProjectRoot 'D:\path\book-slug' -Chapter 1
```

Codex reads `chapter-01-translation-packets.jsonl`, the terminology TSV, glossary and standards, then writes the complete `intermediate/chapter-01-zh.json`. No wrapper calls an external translation API.

## Render and QA

```powershell
& $tool render -ProjectRoot 'D:\path\book-slug' -Chapter 1
& $tool qa -ProjectRoot 'D:\path\book-slug' -Chapter 1
```

`qa` returns 0 for PASS, 1 for WARN and 2 for FAIL. Review both `reports/qa.json` and `reports/QA_REPORT.md`.

## Safe Obsidian synchronization

```powershell
& $tool sync -ProjectRoot 'D:\path\book-slug' -Chapter 1 -DryRun -CopyAssets
& $tool sync -ProjectRoot 'D:\path\book-slug' -Chapter 1 -CopyAssets
```

The destination comes from `.ebook-translation/project.yaml` unless `-Vault` and `-Destination` are provided. The sync command refuses `.obsidian` and path escape.

## One pipeline command

```powershell
& $tool all -ProjectRoot 'D:\path\book-slug' -Chapter 1
```

If `chapter-01-zh.json` is absent, `all` stops after generating translation packets with WARN. Once Codex writes the translation JSON, the same command renders and runs QA; add `-Sync` only when actual Vault synchronization is intended.

## Project overrides

```yaml
# .ebook-translation/paragraph-overrides.yaml
merge:
  - [raw-0012-004, raw-0013-001]
split:
  - block: p-020
    after: "指定文本"
```

```yaml
# .ebook-translation/image-overrides.yaml
anchors:
  figure-001: p-012
```

Use `.ebook-translation/terminology.tsv` for book-specific terms. Reusable behavior belongs in central modules, standards, Skill references and tests.
