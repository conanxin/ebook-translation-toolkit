[CmdletBinding()]
param(
  [Parameter(Position=0, Mandatory=$true)][string]$Action,
  [string]$Pdf,
  [string]$ProjectRoot,
  [string]$ObsidianVault,
  [string]$BookSlug,
  [int]$Chapter = 1,
  [string]$Language = 'zh-CN',
  [string]$Vault,
  [string]$Destination,
  [string]$OutputName,
  [string]$Status,
  [string[]]$Field,
  [string]$Translations,
  [string]$ObsidianMarkdown,
  [switch]$CopyAssets,
  [switch]$DryRun,
  [switch]$OcrMissing,
  [switch]$Sync
)
$ErrorActionPreference = 'Stop'
$toolkit = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$prior = $env:PYTHONPATH
$env:PYTHONPATH = Join-Path $toolkit 'src'
if ($prior) { $env:PYTHONPATH += [IO.Path]::PathSeparator + $prior }
$commandMap = @{ detect='detect'; prepare='prepare'; render='render'; qa='qa'; sync='sync'; all='all'; extract='extract'; normalize='normalize'; init='init'; 'plan-book'='plan-book'; 'render-index'='render-index'; progress='progress'; 'extract-notes'='extract-notes'; 'extract-images'='extract-images'; 'anchor-images'='anchor-images'; 'build-page-anchors'='build-page-anchors'; 'compile-translation'='compile-translation'; 'apply-translation'='apply-translation'; 'check-bilingual-terms'='check-bilingual-terms'; 'render-epub'='render-epub'; 'validate-epub'='validate-epub'; 'check-terminology-lock'='check-terminology-lock' }
if (-not $commandMap.ContainsKey($Action)) { throw "Unsupported action: $Action" }
$arguments = @('-m','ebook_translation_toolkit',$commandMap[$Action])
if ($Action -eq 'init') {
  if (-not $Pdf -or -not $ProjectRoot -or -not $BookSlug) { throw 'init requires -Pdf, -ProjectRoot and -BookSlug' }
  $arguments += @('--pdf',$Pdf,'--project-root',$ProjectRoot,'--book-slug',$BookSlug,'--chapter',[string]$Chapter,'--language',$Language)
  if ($ObsidianVault) { $arguments += @('--obsidian-vault',$ObsidianVault) }
} else {
  if (-not $ProjectRoot) { throw "$Action requires -ProjectRoot" }
  $arguments += @('--project-root',$ProjectRoot)
  if ($Action -notin @('plan-book','render-index')) { $arguments += @('--chapter',[string]$Chapter) }
  if ($Pdf -and $Action -in @('extract','all')) { $arguments += @('--pdf',$Pdf) }
  if ($Action -eq 'all' -and $BookSlug) { $arguments += @('--book-slug',$BookSlug) }
  if ($Action -eq 'all' -and $ObsidianVault) { $arguments += @('--obsidian-vault',$ObsidianVault) }
  if ($Action -eq 'all') { $arguments += @('--language',$Language) }
  if ($OcrMissing -and $Action -in @('extract','all')) { $arguments += '--ocr-missing' }
  if ($Action -eq 'sync') {
    if ($Vault) { $arguments += @('--vault',$Vault) }
    if ($Destination) { $arguments += @('--destination',$Destination) }
    if ($OutputName) { $arguments += @('--output-name',$OutputName) }
    if ($CopyAssets) { $arguments += '--copy-assets' }
    if ($DryRun) { $arguments += '--dry-run' }
  }
  if ($Action -eq 'all' -and $Sync) { $arguments += '--sync' }
  if ($Action -eq 'progress') {
    if (-not $Status) { throw 'progress requires -Status' }
    $arguments += @('--status',$Status)
    foreach ($item in $Field) { $arguments += @('--field',$item) }
  }
  if ($Action -eq 'apply-translation') {
    if (-not $Translations) { throw 'apply-translation requires -Translations' }
    $arguments += @('--translations',$Translations)
  }
  if ($Action -eq 'qa' -and $ObsidianMarkdown) { $arguments += @('--obsidian-markdown',$ObsidianMarkdown) }
}
try { & python @arguments; exit $LASTEXITCODE }
finally { $env:PYTHONPATH = $prior }
