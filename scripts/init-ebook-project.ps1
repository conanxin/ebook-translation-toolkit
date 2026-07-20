[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Pdf,[Parameter(Mandatory=$true)][string]$ProjectRoot,[Parameter(Mandatory=$true)][string]$BookSlug,[string]$ObsidianVault,[int]$Chapter=1,[string]$Language='zh-CN')
& (Join-Path $PSScriptRoot 'ebook-translate.ps1') init -Pdf $Pdf -ProjectRoot $ProjectRoot -BookSlug $BookSlug -ObsidianVault $ObsidianVault -Chapter $Chapter -Language $Language
exit $LASTEXITCODE
