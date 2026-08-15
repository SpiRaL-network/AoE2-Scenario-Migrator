$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    & (Join-Path $PSScriptRoot "setup.ps1")
}

Push-Location $ProjectRoot
try {
    & $Python -m PyInstaller --noconfirm --clean --windowed `
        --name "AoE2ScenarioMigrator" `
        --paths (Join-Path $ProjectRoot "src") `
        --collect-data "AoE2ScenarioParser" `
        --distpath (Join-Path $ProjectRoot "dist") `
        --workpath (Join-Path $ProjectRoot "build\pyinstaller") `
        (Join-Path $ProjectRoot "scripts\gui_entry.py")

    $PortableFolder = Join-Path $ProjectRoot "dist\AoE2ScenarioMigrator"
    foreach ($Document in @(
        "README.md",
        "CHANGELOG.md",
        "LICENSE",
        "NOTICE.md",
        "THIRD_PARTY_NOTICES.md"
    )) {
        Copy-Item -LiteralPath (Join-Path $ProjectRoot $Document) -Destination $PortableFolder
    }
} finally {
    Pop-Location
}
Write-Host "Build complete: $ProjectRoot\dist\AoE2ScenarioMigrator\AoE2ScenarioMigrator.exe"
