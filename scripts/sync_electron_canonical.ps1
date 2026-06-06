# Sync Electron main-process sources from canonical web/frontend/electron to electron_version/electron.
# Usage: .\scripts\sync_electron_canonical.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$src = Join-Path $root "web\frontend\electron"
$dst = Join-Path $root "electron_version\electron"

if (-not (Test-Path $src)) {
    Write-Error "Canonical electron folder not found: $src"
}

New-Item -ItemType Directory -Force -Path $dst | Out-Null
robocopy $src $dst /E /XD node_modules dist dist-electron /NFL /NDL /NJH /NJS /nc /ns /np
if ($LASTEXITCODE -ge 8) { exit $LASTEXITCODE }
Write-Host "Synced electron sources: $src -> $dst"
exit 0