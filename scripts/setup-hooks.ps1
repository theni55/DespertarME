# Activa los hooks de git versionados en .githooks/ para este clon.
# Uso:  pwsh scripts/setup-hooks.ps1

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    git config core.hooksPath .githooks
    Write-Host "core.hooksPath -> .githooks configurado." -ForegroundColor Green
    Write-Host "El hook pre-commit regenera el indice de memoria/ y vigila handoff.md."
} finally {
    Pop-Location
}
