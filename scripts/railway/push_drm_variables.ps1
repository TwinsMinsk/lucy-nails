#requires -Version 5.1
<#
.SYNOPSIS
  Push Kinescope DRM variables from repo .env + PEM into Railway (backend service).

.EXAMPLE
  cd C:\Projects\Oleg\Lucy-nails
  .\scripts\railway\push_drm_variables.ps1 -ServiceName Backend
#>
param(
    [string]$ServiceName = "Backend",
    [string]$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path,
    [string]$PemPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-DotEnvValue {
    param([string]$Path, [string]$Key)
    if (-not (Test-Path -LiteralPath $Path)) { throw "Missing .env: $Path" }
    $pattern = '^\s*' + [regex]::Escape($Key) + '\s*=\s*(.*)\s*$'
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match '^\s*#') { continue }
        $m = [regex]::Match($line, $pattern)
        if ($m.Success) {
            $v = $m.Groups[1].Value.Trim()
            if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
                $v = $v.Substring(1, $v.Length - 2)
            }
            return $v
        }
    }
    return $null
}

$envFile = Join-Path $RepoRoot ".env"
if (-not $PemPath) { $PemPath = Join-Path $RepoRoot "backend\secrets\kinescope_drm_private.pem" }

if (-not (Test-Path -LiteralPath $PemPath)) {
    throw "PEM not found: $PemPath - run scripts/kinescope/setup_drm.py first"
}

$kid = Get-DotEnvValue -Path $envFile -Key "KINESCOPE_JWK_KID"
$user = Get-DotEnvValue -Path $envFile -Key "KINESCOPE_DRM_BASIC_USER"
$pass = Get-DotEnvValue -Path $envFile -Key "KINESCOPE_DRM_BASIC_PASS"
$ttl = Get-DotEnvValue -Path $envFile -Key "KINESCOPE_DRM_TOKEN_TTL_SECONDS"
if (-not $ttl) { $ttl = "300" }

foreach ($req in @(@{ n = "KINESCOPE_JWK_KID"; v = $kid }, @{ n = "KINESCOPE_DRM_BASIC_USER"; v = $user }, @{ n = "KINESCOPE_DRM_BASIC_PASS"; v = $pass })) {
    if (-not $req.v) { throw "Missing $($req.n) in .env" }
}

Write-Host "Pushing DRM variables to Railway service '$ServiceName'..."
Push-Location $RepoRoot
try {
    railway variable set "KINESCOPE_JWK_KID=$kid" -s $ServiceName
    railway variable set "KINESCOPE_DRM_BASIC_USER=$user" -s $ServiceName
    railway variable set "KINESCOPE_DRM_BASIC_PASS=$pass" -s $ServiceName
    railway variable set "KINESCOPE_DRM_TOKEN_TTL_SECONDS=$ttl" -s $ServiceName
    Get-Content -LiteralPath $PemPath -Raw -Encoding UTF8 | railway variable set "KINESCOPE_JWT_PRIVATE_KEY_PEM" --stdin -s $ServiceName
    Write-Host "Done. Redeploy if needed."
}
finally {
    Pop-Location
}
