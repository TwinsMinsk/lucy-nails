param(
    [Parameter(Mandatory = $true)]
    [string]$FrontendUrl,

    [Parameter(Mandatory = $true)]
    [string]$BackendUrl
)

$ErrorActionPreference = "Stop"

function Invoke-SmokeRequest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    Write-Host "Checking $Url"
    $statusCode = & curl.exe --location --silent --show-error --output "NUL" --write-out "%{http_code}" --max-time "20" "$Url"
    if ($LASTEXITCODE -ne 0) {
        throw "Request failed for $Url"
    }

    $status = [int]$statusCode
    if ($status -lt 200 -or $status -ge 400) {
        throw "Unexpected status $status for $Url"
    }
}

$frontend = $FrontendUrl.TrimEnd("/")
$backend = $BackendUrl.TrimEnd("/")

Invoke-SmokeRequest "$backend/health"
Invoke-SmokeRequest "$frontend/"
Invoke-SmokeRequest "$frontend/robots.txt"
Invoke-SmokeRequest "$frontend/sitemap.xml"

Write-Host ""
Write-Host "Automated smoke checks passed."
Write-Host "Manual smoke still required: Prodamus test payment/webhook retry and Kinescope playback with a paid test user."
