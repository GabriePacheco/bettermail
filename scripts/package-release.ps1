param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$releaseRoot = Join-Path $projectRoot "release"
$packageName = "BetterMail-AI-$Version"
$packageDirectory = Join-Path $releaseRoot $packageName
$zipPath = Join-Path $releaseRoot "$packageName.zip"
$resolvedProjectRoot = [System.IO.Path]::GetFullPath($projectRoot)
$resolvedReleaseRoot = [System.IO.Path]::GetFullPath($releaseRoot)

if (-not $resolvedReleaseRoot.StartsWith($resolvedProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "La carpeta de release debe permanecer dentro del proyecto."
}

if (Test-Path -LiteralPath $packageDirectory) {
    Remove-Item -LiteralPath $packageDirectory -Recurse -Force
}
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

New-Item -ItemType Directory -Path $packageDirectory -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot "manifest.xml") -Destination $packageDirectory
Copy-Item -LiteralPath (Join-Path $projectRoot "docs\instalacion-usuarios.md") -Destination (Join-Path $packageDirectory "INSTALACION.md")
Copy-Item -LiteralPath (Join-Path $projectRoot "docs\guia-usuario.md") -Destination (Join-Path $packageDirectory "GUIA-USUARIO.md")
Copy-Item -LiteralPath (Join-Path $projectRoot "docs\checklist-pruebas-release.md") -Destination (Join-Path $packageDirectory "CHECKLIST-PRUEBAS.md")

Compress-Archive -Path (Join-Path $packageDirectory "*") -DestinationPath $zipPath -CompressionLevel Optimal
Write-Output $zipPath
