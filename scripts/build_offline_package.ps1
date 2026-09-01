param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

function Fail($Message) {
    Write-Error $Message
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Version) -or $Version -eq "-h" -or $Version -eq "--help") {
    Write-Host "Usage: .\scripts\build_offline_package.ps1 -Version v1.0.1"
    exit 0
}

if ($Version -notmatch '^v[0-9]+\.[0-9]+\.[0-9]+$') {
    Fail "Version must look like v1.0.1"
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ImageName = "vibration-gateway-offline-builder:arm64"
$Dockerfile = Join-Path $RepoRoot "docker\offline-builder.Dockerfile"

if (-not (Test-Path $Dockerfile)) {
    Fail "Missing Dockerfile: $Dockerfile"
}

Write-Host "[1/2] Building ARM64 Docker builder image"
docker buildx build --platform linux/arm64 --load -f $Dockerfile -t $ImageName $RepoRoot
if ($LASTEXITCODE -ne 0) {
    Fail "Docker buildx failed with exit code $LASTEXITCODE"
}

Write-Host "[2/2] Building offline package inside ARM64 container"
docker run --rm --platform linux/arm64 -v "${RepoRoot}:/workspace" -w /workspace $ImageName bash ./scripts/build_offline_package.sh $Version
if ($LASTEXITCODE -ne 0) {
    Fail "Docker package build failed with exit code $LASTEXITCODE"
}
