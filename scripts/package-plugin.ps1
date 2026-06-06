# Pack a plugin directory into inkrest-ready .zip
param(
    [Parameter(Mandatory = $true)]
    [string]$PluginDir,
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$src = Resolve-Path $PluginDir
if (-not (Test-Path (Join-Path $src "inkrest.plugin.json"))) {
    Write-Error "目录缺少 inkrest.plugin.json: $src"
}
$manifest = Get-Content (Join-Path $src "inkrest.plugin.json") -Raw | ConvertFrom-Json
$id = $manifest.id
if (-not $id) { Write-Error "manifest 缺少 id" }
$dest = if ($OutDir) { $OutDir } else { Join-Path $root "dist-plugins" }
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$zipPath = Join-Path $dest "$id.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $src "*") -DestinationPath $zipPath -Force
Write-Host "已打包: $zipPath"