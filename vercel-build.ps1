# Vercel Build Script for Windows
# This script prepares the project for Vercel deployment

Write-Host "🚀 Starting Vercel build process..." -ForegroundColor Cyan

# Build Frontend
Write-Host "📦 Building Frontend..." -ForegroundColor Yellow
Set-Location Frontend
npm install
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Frontend build failed" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Frontend build successful" -ForegroundColor Green

# Prepare Backend (API only, no packet sniffing)
Write-Host "🔧 Preparing Backend API..." -ForegroundColor Yellow
Set-Location ..\Backend\SafeLink_Backend

# Use lightweight requirements for Vercel
if (Test-Path "requirements-vercel.txt") {
    Write-Host "📥 Installing production dependencies..." -ForegroundColor Yellow
    pip install -r requirements-vercel.txt
} else {
    Write-Host "⚠️  Warning: requirements-vercel.txt not found, using full requirements" -ForegroundColor Yellow
    pip install -r requirements.txt
}

Set-Location ..\..

Write-Host ""
Write-Host "✅ Build process completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Deployment Summary:" -ForegroundColor Cyan
Write-Host "  - Frontend: Frontend/dist/"
Write-Host "  - Backend API: Backend/SafeLink_Backend/api.py"
Write-Host "  - Configuration: vercel.json"
Write-Host ""
Write-Host "⚠️  Important Reminders:" -ForegroundColor Yellow
Write-Host "  1. Set environment variables in Vercel dashboard"
Write-Host "  2. Configure external PostgreSQL database"
Write-Host "  3. Upload ML models to S3 or external storage"
Write-Host "  4. Update CORS_ORIGINS with your Vercel domain"
Write-Host ""
Write-Host "🎉 Ready for deployment!" -ForegroundColor Green
