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
    $response = Invoke-WebRequest -Uri $Url -Method GET -MaximumRedirection 5 -TimeoutSec 20
    if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
        throw "Unexpected status $($response.StatusCode) for $Url"
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
