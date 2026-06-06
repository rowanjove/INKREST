# Desktop portable build: Vue + Electron + PyInstaller + portable exe
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Frontend = Join-Path $Root "web\frontend"
$Out = Join-Path $Root "dist-portable"

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -match 'NovelAgent|novel-agent-backend' -or
        ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($Out, [System.StringComparison]::OrdinalIgnoreCase)) -or
        ($_.ExecutablePath -and $_.ExecutablePath.StartsWith((Join-Path $Frontend "dist-desktop\win-unpacked"), [System.StringComparison]::OrdinalIgnoreCase))
    } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Push-Location $Frontend
try {
    npm run dist:win
    if ($LASTEXITCODE -ne 0) {
        throw "npm run dist:win failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

$srcDesktop = Join-Path $Frontend "dist-desktop"
$portable = Get-ChildItem $srcDesktop -File -Filter "*.exe" |
    Where-Object { $_.Name -notmatch 'Setup' } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $portable) {
    throw "Portable executable not found in: $srcDesktop"
}

New-Item -ItemType Directory -Force -Path $Out | Out-Null
Copy-Item $portable.FullName (Join-Path $Out $portable.Name) -Force
Copy-Item $portable.FullName (Join-Path $Out "NovelAgent.exe") -Force
$icon = Join-Path $srcDesktop "win-unpacked\resources\app.asar.unpacked\build\icon.ico"
if (Test-Path $icon) {
    $iconDir = Join-Path $Out "resources"
    New-Item -ItemType Directory -Force -Path $iconDir | Out-Null
    Copy-Item $icon (Join-Path $iconDir "icon.ico") -Force
}
$unpackedDst = Join-Path $Out "win-unpacked"
if (Test-Path $unpackedDst) { Remove-Item $unpackedDst -Recurse -Force }
Copy-Item (Join-Path $srcDesktop "win-unpacked") $unpackedDst -Recurse -Force

Write-Host "Done. Portable executable: $(Join-Path $Out $portable.Name)"
Write-Host "Compatibility alias: $(Join-Path $Out 'NovelAgent.exe')"
Write-Host "Unpacked directory: $unpackedDst"
