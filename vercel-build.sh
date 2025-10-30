#!/bin/bash

# Vercel Build Script for SafeLink
# This script prepares the project for Vercel deployment

echo "🚀 Starting Vercel build process..."

# Build Frontend
echo "📦 Building Frontend..."
cd Frontend
npm install
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Frontend build failed"
    exit 1
fi

echo "✅ Frontend build successful"

# Prepare Backend (API only, no packet sniffing)
echo "🔧 Preparing Backend API..."
cd ../Backend/SafeLink_Backend

# Use lightweight requirements for Vercel
if [ -f "requirements-vercel.txt" ]; then
    echo "📥 Installing production dependencies..."
    pip install -r requirements-vercel.txt
else
    echo "⚠️  Warning: requirements-vercel.txt not found, using full requirements"
    pip install -r requirements.txt
fi

echo "✅ Build process completed successfully!"
echo ""
echo "📊 Deployment Summary:"
echo "  - Frontend: Frontend/dist/"
echo "  - Backend API: Backend/SafeLink_Backend/api.py"
echo "  - Configuration: vercel.json"
echo ""
echo "⚠️  Important Reminders:"
echo "  1. Set environment variables in Vercel dashboard"
echo "  2. Configure external PostgreSQL database"
echo "  3. Upload ML models to S3 or external storage"
echo "  4. Update CORS_ORIGINS with your Vercel domain"
echo ""
echo "🎉 Ready for deployment!"
