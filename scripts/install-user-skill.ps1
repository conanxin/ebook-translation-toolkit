[CmdletBinding()]
param([switch]$SkipWsl)
$ErrorActionPreference = 'Stop'
$toolkit = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source = Join-Path $toolkit 'skill\ebook-translation-zh'
$target = Join-Path $env:USERPROFILE '.agents\skills\ebook-translation-zh'
New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
$mode = 'COPY'
if (Test-Path -LiteralPath $target) {
  $item = Get-Item -LiteralPath $target -Force
  if ($item.LinkType -in @('Junction','SymbolicLink')) { $mode = 'LINK' }
  else { Copy-Item -Path "$source\*" -Destination $target -Recurse -Force }
} else {
  try { New-Item -ItemType Junction -Path $target -Target $source -ErrorAction Stop | Out-Null; $mode = 'LINK' }
  catch { New-Item -ItemType Directory -Force -Path $target | Out-Null; Copy-Item -Path "$source\*" -Destination $target -Recurse -Force; $mode = 'COPY' }
}
python (Join-Path $PSScriptRoot 'update-global-route.py') (Join-Path $env:USERPROFILE '.codex\AGENTS.md')
Write-Output "WINDOWS_SKILL_PATH=$target"
Write-Output "WINDOWS_SKILL_INSTALL_MODE=$mode"
if (-not $SkipWsl -and (Test-Path -LiteralPath '\\wsl.localhost\Ubuntu-24.04\home\conanxin')) {
  wsl.exe -d Ubuntu-24.04 -- bash "$($toolkit -replace '\\','/' -replace '^D:','/mnt/d')/scripts/install-user-skill.sh"
}
