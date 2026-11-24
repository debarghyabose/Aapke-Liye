# Deploy Aapke Liye to Google Cloud Run
param(
    [string]$Region = "us-central1",
    [string]$ProjectId = "trusty-obelisk-515402-p3",
    [string]$ServiceName = "aapke-liye"
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " 🚀 Deploying Aapke Liye (Standalone Real) to Cloud Run   " -ForegroundColor Cyan
Write-Host " Project: $ProjectId | Service: $ServiceName | Region: $Region" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Find gcloud
$gcloud = "gcloud"
if (Get-Command "gcloud.cmd" -ErrorAction SilentlyContinue) { $gcloud = "gcloud.cmd" }

# Build frontend before deployment
Write-Host "`n[1/3] Building Frontend SPA..." -ForegroundColor Yellow
Push-Location "$root\frontend"
cmd.exe /c "npm run build"
Pop-Location

# Submit build and deploy via Google Cloud Build
Write-Host "`n[2/3] Submitting Build & Deploying to Cloud Run..." -ForegroundColor Yellow
& $gcloud builds submit "$root" --config="$root\cloudbuild.yaml" --project=$ProjectId

Write-Host "`n[3/3] Deployment complete!" -ForegroundColor Green
Write-Host "Checking service URL..."
& $gcloud run services describe $ServiceName --region=$Region --project=$ProjectId --format="value(status.url)"
