param(
    [switch]$CopyOnly
)

$ErrorActionPreference = "Continue"
$project = "teleasnews"
$secretName = "bettermail-admin-api-secret"
$adminUrl = "https://bettermailai.web.app/internal-admin"
$secretConsoleUrl = "https://console.cloud.google.com/security/secret-manager/secret/$secretName/versions?project=$project"

$secret = & gcloud.cmd secrets versions access latest `
    --secret=$secretName `
    --project=$project 2>$null

if ($LASTEXITCODE -ne 0 -or -not $secret) {
    Write-Warning "No se pudo copiar la clave con gcloud. Se abrira Secret Manager para obtenerla manualmente."
    Start-Process $secretConsoleUrl
    if (-not $CopyOnly) {
        Start-Process $adminUrl
    }
    exit 1
}

$secret.Trim() | Set-Clipboard
Write-Host "Clave administrativa copiada al portapapeles."

if (-not $CopyOnly) {
    Start-Process $adminUrl
    Write-Host "Panel abierto: $adminUrl"
}
