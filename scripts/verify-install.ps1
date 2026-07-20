$ErrorActionPreference = 'Stop'
$toolkit = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$skill = Join-Path $env:USERPROFILE '.agents\skills\ebook-translation-zh\SKILL.md'
if (-not (Test-Path $skill)) { throw 'Windows user skill missing' }
$validator = Join-Path $env:USERPROFILE '.codex\skills\.system\skill-creator\scripts\quick_validate.py'
if (Test-Path -LiteralPath $validator) { python $validator (Join-Path $toolkit 'skill\ebook-translation-zh') }
else { Write-Warning 'skill-creator quick_validate.py is unavailable; structural checks continue' }
python (Join-Path $toolkit 'skill\ebook-translation-zh\scripts\locate_toolkit.py')
$agents = Get-Content -Raw -Encoding UTF8 (Join-Path $env:USERPROFILE '.codex\AGENTS.md')
if (([regex]::Matches($agents, '<!-- BEGIN EBOOK_TRANSLATION_ZH -->').Count) -ne 1) { throw 'Windows global route marker is not unique' }
'PASS'
