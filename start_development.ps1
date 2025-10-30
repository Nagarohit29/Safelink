# SafeLink Development Startup Script (Windows)
# Run this to start SafeLink in development mode

Write-Host "========================================" -ForegroundColor Green
Write-Host "SafeLink Development Startup Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Project paths
$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "Backend\SafeLink_Backend"
$FrontendDir = Join-Path $ProjectRoot "Frontend"

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
    Write-Host "Please edit .env file with your configuration." -ForegroundColor Yellow
}

# Check if database exists
if (-not (Test-Path "$BackendDir\data\safelink.db")) {
    Write-Host "Database not found. Initializing..." -ForegroundColor Yellow
    Set-Location $BackendDir
    & "$BackendDir\venv\Scripts\Activate.ps1"
    python Scripts\setup_db.py
    Write-Host "Database initialized." -ForegroundColor Green
}

# Check if frontend dependencies installed
if (-not (Test-Path "$FrontendDir\node_modules")) {
    Write-Host "Frontend dependencies not found. Installing..." -ForegroundColor Yellow
    Set-Location $FrontendDir
    npm install
    Write-Host "Frontend dependencies installed." -ForegroundColor Green
}

Write-Host ""
Write-Host "Starting SafeLink in DEVELOPMENT mode..." -ForegroundColor Green
Write-Host ""

# Start backend in new window
Write-Host "Starting Backend (port 8000)..." -ForegroundColor Yellow
$BackendScript = @"
Set-Location '$BackendDir'
& '$BackendDir\venv\Scripts\Activate.ps1'
Write-Host 'Backend Server Running' -ForegroundColor Green
Write-Host 'API: http://localhost:8000' -ForegroundColor Cyan
Write-Host 'Docs: http://localhost:8000/docs' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
uvicorn api:app --reload --host 127.0.0.1 --port 8000
"@
Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendScript

Start-Sleep -Seconds 3

# Start frontend in new window
Write-Host "Starting Frontend (port 5173)..." -ForegroundColor Yellow
$FrontendScript = @"
Set-Location '$FrontendDir'
Write-Host 'Frontend Server Running' -ForegroundColor Green
Write-Host 'URL: http://localhost:5173' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
npm run dev
"@
Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendScript

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "SafeLink Development Environment Ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend API:     http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs:        http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Frontend:        http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Two PowerShell windows opened for backend and frontend." -ForegroundColor Yellow
Write-Host "Close those windows to stop the services." -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
