# Aapke Liye — Start the Standalone Real Product
param(
    [int]$Port = 8080,
    [switch]$DevFrontend
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " 🤝 Aapke Liye (आपके लिए) — Standalone Real Stack         " -ForegroundColor Cyan
Write-Host " Database: Firebase Firestore (Project: trusty-obelisk-515402-p3)" -ForegroundColor Cyan
Write-Host " AI: Google Gemini 3.5 Flash Multilingual + Vision        " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Build frontend if dist doesn't exist
$dist = Join-Path $root "frontend\dist"
if (-not (Test-Path (Join-Path $dist "index.html"))) {
    Write-Host "`nBuilding frontend assets..." -ForegroundColor Yellow
    Push-Location "$root\frontend"
    cmd.exe /c "npm run build"
    Pop-Location
}

# 2. Check Python packages
Write-Host "`nChecking Python dependencies..." -ForegroundColor Yellow
& python -c "import fastapi, uvicorn, google.cloud.firestore, gtts, reportlab, PIL, cryptography" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing missing dependencies..." -ForegroundColor Yellow
    & python -m pip install -q -r "$root\backend\requirements.txt"
}

# 3. Print URLs and staff credentials
Write-Host "`nReady to launch!" -ForegroundColor Green
Write-Host "----------------------------------------------------------"
Write-Host "  Claimant App & Tracking:  http://localhost:$Port" -ForegroundColor White
Write-Host "  Officials Dashboard:      http://localhost:$Port/official" -ForegroundColor White
Write-Host "  API Documentation:        http://localhost:$Port/docs" -ForegroundColor White
Write-Host "  Pre-disaster Vault:       http://localhost:$Port/prepare" -ForegroundColor White
Write-Host "  Offline Mesh Relay:       http://localhost:$Port/mesh" -ForegroundColor White
Write-Host "----------------------------------------------------------"
Write-Host "  Officials Staff Key:      (see STAFF_API_KEYS in backend/.env)" -ForegroundColor Cyan
Write-Host "----------------------------------------------------------`n"

# 4. Start backend server
Push-Location "$root\backend"
& python -m uvicorn app.main:app --host 127.0.0.1 --port $Port --reload
Pop-Location
