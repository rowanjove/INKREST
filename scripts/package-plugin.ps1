# Pack a plugin directory into inkrest-ready .zip
param(
    [Parameter(Mandatory = $true)]
    [string]$PluginDir,
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$src = (Resolve-Path $PluginDir).Path
if (-not (Test-Path (Join-Path $src "inkrest.plugin.json"))) {
    Write-Error "目录缺少 inkrest.plugin.json: $src"
}
$manifest = Get-Content (Join-Path $src "inkrest.plugin.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$id = $manifest.id
if (-not $id) { Write-Error "manifest 缺少 id" }
$pluginName = if ($manifest.display_name) { $manifest.display_name } elseif ($manifest.name) { $manifest.name } else { $id }
$safeName = ($pluginName -replace '[\\/:*?"<>|]', '_').Trim()
if (-not $safeName) { $safeName = $id }
$defaultDir = "$([char]0x63D2)$([char]0x4EF6)"
$dest = if ($OutDir) { $OutDir } else { Join-Path $root $defaultDir }
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$zipPath = Join-Path $dest "$safeName.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
# Create temporary staging directory to exclude caches and test suites
$stageDir = Join-Path ([System.IO.Path]::GetTempPath()) ("inkrest-plugin-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $stageDir | Out-Null
try {
    Get-ChildItem -Path $src -Recurse | ForEach-Object {
        $rel = $_.FullName.Substring($src.Length).TrimStart('\', '/')
        if ($_.FullName -match '[\\/](__pycache__|\.pytest_cache|tests)(\\|$)' -or $_.Name -match '\.(pyc|pyo|log|tmp)$') {
            return
        }
        $target = Join-Path $stageDir $rel
        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Force -Path $target | Out-Null
        } else {
            $parent = Split-Path -Parent $target
            if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
            Copy-Item -Path $_.FullName -Destination $target -Force
        }
    }
    Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $zipPath -Force
} finally {
    Remove-Item -Recurse -Force -Path $stageDir -ErrorAction SilentlyContinue
}
Write-Host "已打包: $zipPath"