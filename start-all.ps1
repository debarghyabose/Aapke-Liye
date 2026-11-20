# Aapke Liye: start the whole product on this computer (localhost only).
#
#   .\start-all.ps1            install anything missing, then start all four services
#   .\start-all.ps1 -Setup     only install and write the .env files
#   .\start-all.ps1 -Stop      stop all four services
#
# Opens one window per service (close a window to stop that service):
#   Member 4  the app             http://localhost:5173        <- open this
#   Member 2  core backend        http://localhost:8000/docs   (the app talks only to this)
#   Member 1  speech + claim AI   http://localhost:8001/docs   (8011 if 8001 is taken)
#   Member 3  photo verification  http://localhost:8002/docs   (+ WhatsApp / IVR / dashboard API)
# Every service listens on 127.0.0.1 only, so nothing is reachable from other computers.
param([switch]$Setup, [switch]$Stop)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

function Get-PortOwner([int]$port) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
}

# Stops only processes started from this project folder (never other apps on the same ports).
function Stop-AppServices {
    foreach ($port in 5173, 8000, 8001, 8002, 8011) {
        $c = Get-PortOwner $port
        if (-not $c) { continue }
        $p = Get-CimInstance Win32_Process -Filter "ProcessId=$($c.OwningProcess)"
        if ($p.CommandLine -like "*$root*" -or $p.ExecutablePath -like "$root*") {
            Stop-Process -Id $c.OwningProcess -Force
            Write-Host "Stopped port $port"
        }
    }
}

if ($Stop) { Stop-AppServices; return }

function Initialize-Venv($dir, $reqs) {
    $py = Join-Path $dir '.venv\Scripts\python.exe'
    if (-not (Test-Path $py)) {
        Write-Host "Creating Python environment in $dir ..."
        & python -m venv (Join-Path $dir '.venv')
        & $py -m pip install -q -r (Join-Path $dir $reqs)
    }
    return $py
}

$m1 = Initialize-Venv "$root\Member-1" 'requirements.txt'
$m2 = Initialize-Venv "$root\Member-2\backend" 'requirements-dev.txt'
$m3 = Initialize-Venv "$root\Member-3" 'requirements.txt'
if (-not (Test-Path "$root\Member-4\frontend\node_modules")) {
    Write-Host 'Installing app packages (npm) ...'
    Push-Location "$root\Member-4\frontend"; npm install --no-audit --no-fund; Pop-Location
}

& python "$root\scripts\setup_dev.py"
if ($Setup) { return }

# Restart cleanly if an earlier run of this project is still up.
Stop-AppServices

# Member 1 normally uses 8001; move it if another program already has that port.
$m1Port = 8001
if (Get-PortOwner 8001) {
    $m1Port = 8011
    Write-Host 'Port 8001 is used by another program; Member 1 will run on 8011.'
}
foreach ($port in 5173, 8000, 8002) {
    if (Get-PortOwner $port) { throw "Port $port is used by another program. Close it and run again." }
}

# Voice needs ffmpeg (winget install Gyan.FFmpeg). A fresh install may not be on PATH yet.
$ffmpegDir = ''
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    $ff = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($ff) { $ffmpegDir = $ff.DirectoryName }
    else { Write-Host 'ffmpeg not found: typed claims work, voice needs  winget install Gyan.FFmpeg' }
}

function Start-AppService($title, $dir, $exe, $arguments, $envSetup = '') {
    $cmd = "`$host.UI.RawUI.WindowTitle = '$title'; $envSetup Set-Location '$dir'; & '$exe' $arguments"
    Start-Process powershell -ArgumentList '-NoExit', '-Command', $cmd | Out-Null
}

$m1Env = if ($ffmpegDir) { "`$env:PATH = '$ffmpegDir;' + `$env:PATH;" } else { '' }
# A variable set here wins over Member 2's .env, so the backend always finds Member 1.
$m2Env = "`$env:MEMBER1_AI_URL = 'http://localhost:$m1Port';"

Start-AppService "Aapke Liye - Member 1 AI ($m1Port)" "$root\Member-1" $m1 "-m uvicorn app.main:app --host 127.0.0.1 --port $m1Port" $m1Env
Start-AppService 'Aapke Liye - Member 3 verify (8002)' "$root\Member-3" $m3 '-m uvicorn app.main:app --host 127.0.0.1 --port 8002'
Start-AppService 'Aapke Liye - Member 2 backend (8000)' "$root\Member-2\backend" $m2 '-m uvicorn app.main:app --host 127.0.0.1 --port 8000' $m2Env
Start-AppService 'Aapke Liye - Member 4 app (5173)' "$root\Member-4\frontend" 'npm' 'run dev -- --host 127.0.0.1 --port 5173 --strictPort'

Write-Host ''
Write-Host 'Waiting for the services ...'
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 2
    try {
        $h = Invoke-RestMethod http://127.0.0.1:8000/health -TimeoutSec 3
        if ($h.member1_ai -eq 'ok' -and $h.member3_verify -eq 'ok') { break }
    } catch { }
}
if ($h) { Write-Host "Backend: database $($h.database), Member 1 $($h.member1_ai), Member 3 $($h.member3_verify)" }
Write-Host ''
Write-Host 'Open http://localhost:5173'
Start-Process 'http://localhost:5173'
