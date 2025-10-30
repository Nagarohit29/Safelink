# SafeLink Production Startup Script (Windows)
# Run as Administrator

Write-Host "========================================" -ForegroundColor Green
Write-Host "SafeLink Production Startup Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Error: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Project paths
$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "Backend\SafeLink_Backend"

# Check if virtual environment exists
if (-not (Test-Path "$BackendDir\venv")) {
    Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
    Set-Location $BackendDir
    python -m venv venv
    & "$BackendDir\venv\Scripts\Activate.ps1"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    Write-Host "Virtual environment created successfully." -ForegroundColor Green
} else {
    Write-Host "Virtual environment found." -ForegroundColor Green
}

# Check if .env file exists
if (-not (Test-Path "$BackendDir\.env")) {
    Write-Host "Warning: .env file not found!" -ForegroundColor Yellow
    Write-Host "Copying .env.example to .env..."
    Copy-Item "$BackendDir\.env.example" "$BackendDir\.env"
    Write-Host "IMPORTANT: Edit .env file with your configuration before running!" -ForegroundColor Red
    Write-Host "Especially: SECRET_KEY, NETWORK_INTERFACE" -ForegroundColor Yellow
    exit 1
}

# Check if database exists
if (-not (Test-Path "$BackendDir\data\safelink.db")) {
    Write-Host "Database not found. Initializing..." -ForegroundColor Yellow
    Set-Location $BackendDir
    & "$BackendDir\venv\Scripts\Activate.ps1"
    python Scripts\setup_db.py
    Write-Host "Database initialized." -ForegroundColor Green
}

# Check if Npcap is installed
Write-Host "Checking Npcap installation..." -ForegroundColor Yellow
$npcapPath = "C:\Windows\System32\Npcap\wpcap.dll"
if (-not (Test-Path $npcapPath)) {
    Write-Host "Warning: Npcap not found!" -ForegroundColor Red
    Write-Host "Please download and install Npcap from: https://npcap.com/#download" -ForegroundColor Yellow
    Write-Host "Enable 'WinPcap Compatibility Mode' during installation." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "Npcap found." -ForegroundColor Green
}

# Start backend
Write-Host ""
Write-Host "Starting SafeLink backend..." -ForegroundColor Green
Set-Location $BackendDir
& "$BackendDir\venv\Scripts\Activate.ps1"

# Production mode: 4 workers, no reload
Write-Host "Running in PRODUCTION mode (4 workers)" -ForegroundColor Cyan
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info

Write-Host ""
Write-Host "SafeLink backend started successfully!" -ForegroundColor Green
Write-Host "Access the API at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
