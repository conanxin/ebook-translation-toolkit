# Installation Report

STATUS: PASS

## Installation

- Toolkit: `D:\home\conanxin\workspace\ebook-translation-toolkit`
- Version: `0.1.0`
- Windows Skill: `C:\Users\haili\.agents\skills\ebook-translation-zh`
- Windows mode: `LINK` (Junction to the D-drive canonical Skill)
- WSL Skill: `/home/conanxin/.agents/skills/ebook-translation-zh`
- WSL mode: `LINK` (symbolic link to `/mnt/d/home/conanxin/workspace/ebook-translation-toolkit/skill/ebook-translation-zh`)
- Windows global routing: `C:\Users\haili\.codex\AGENTS.md`
- WSL global routing: `/home/conanxin/.codex/AGENTS.md`
- Global route marker count: Windows 1, WSL 1
- Current project: project-level `AGENTS.md` and `.ebook-translation/project.yaml` installed; validated final outputs were not rebuilt.

## Verification

- Python unit/regression tests: 28 passed, 0 failed.
- Skill Creator validation: PASS.
- Windows toolkit locator: PASS.
- WSL toolkit locator: PASS.
- Repeated user Skill installation: PASS; both targets remained LINK and route markers remained unique.
- Temporary new-project initialization: PASS; all required directories, configs and lightweight wrappers were created.
- Native text extraction on a one-page temporary PDF: PASS; one reliable page, OCR not used.
- Minimal fixture render and QA: PASS; 10 cross-page blocks, 2 images, 7 footnotes, 28 bilingual names/terms.
- Real Windows Chrome: PASS at 1366×768, 1920×1080 and 390×844 in paged and continuous modes; all 7 popovers passed click/toggle/outside/Escape checks; no console errors or network requests.
- Browser evidence: `reports/browser-validation.json`.

## Discovery note

The required exact WSL Codex CLI command was executed once. It returned `stdin is not a terminal` before loading a task, so live CLI self-report is WARN. Static discovery is PASS on both user Skill paths, SKILL frontmatter, locator order, and global route markers. Open a new Codex Desktop task (or restart if the Skill list is cached) to refresh desktop discovery.

The isolated validation workspace remains under `.validation` because this environment's destructive-action policy rejected its removal. It is not referenced by the installed Skill or toolkit runtime and contains no source ebook PDF.
