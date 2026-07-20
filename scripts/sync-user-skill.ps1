$ErrorActionPreference = 'Stop'
$toolkit = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source = Join-Path $toolkit 'skill\ebook-translation-zh'
$target = Join-Path $env:USERPROFILE '.agents\skills\ebook-translation-zh'
if (-not (Test-Path -LiteralPath $target)) { & (Join-Path $PSScriptRoot 'install-user-skill.ps1'); exit $LASTEXITCODE }
$item = Get-Item -LiteralPath $target -Force
if ($item.LinkType -in @('Junction','SymbolicLink')) { 'LINK: already synchronized' }
else { Copy-Item -Path "$source\*" -Destination $target -Recurse -Force; 'COPY: synchronized' }
