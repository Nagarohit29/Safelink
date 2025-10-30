# Vercel Deployment Guide for SafeLink

This guide will help you deploy SafeLink to Vercel via GitHub.

## ⚠️ Important Limitations

**Vercel's serverless environment has restrictions:**

❌ **Cannot run on Vercel (without modifications):**
- Real-time packet sniffing (requires root/raw sockets)
- Network interface monitoring
- Scapy packet capture
- Background packet processing tasks
- TensorFlow models (too large for serverless)

✅ **Can run on Vercel:**
- REST API endpoints
- Machine learning inference (Random Forest only)
- WebSocket connections
- Frontend React application
- Alert management
- Database operations (with external DB)
- Threat intelligence integration

## 🎯 Recommended Architecture for Production

For a **production SafeLink deployment**, use a **hybrid approach**:

### Option 1: Hybrid Deployment (Recommended)
```
Frontend (Vercel)          → Static React app
API Layer (Vercel)         → FastAPI REST endpoints
Backend Worker (VPS/AWS)   → Packet sniffer + ML processing
Database (Managed)         → PostgreSQL (Supabase/Neon)
```

### Option 2: Full VPS Deployment (Best for Network Security)
```
Everything on VPS/AWS EC2  → Complete control, no restrictions
- Use DEPLOYMENT_GUIDE.md for setup
```

## 📋 Prerequisites

1. **GitHub Account** - To host your repository
2. **Vercel Account** - Sign up at [vercel.com](https://vercel.com)
3. **External Database** - PostgreSQL (Supabase, Neon, or AWS RDS)
4. **Model Storage** - AWS S3 or similar for `.h5`/`.pt` files

## 🚀 Step-by-Step Deployment

### Step 1: Initialize Git Repository

```powershell
# Navigate to project root
cd E:\coreproject

# Initialize git
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: SafeLink Network Defense System"
```

### Step 2: Create GitHub Repository

1. Go to [GitHub](https://github.com/new)
2. Create a new repository (e.g., `safelink-network-defense`)
3. **DO NOT** initialize with README (you already have one)
4. Copy the repository URL

### Step 3: Push to GitHub

```powershell
# Add remote origin
git remote add origin https://github.com/YOUR_USERNAME/safelink-network-defense.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 4: Configure External Services

#### A. Set up PostgreSQL Database

**Option 1: Supabase (Free tier available)**
```
1. Go to supabase.com
2. Create new project
3. Get connection string: postgresql://user:pass@host:5432/db
4. Save for Vercel environment variables
```

**Option 2: Neon (Serverless Postgres)**
```
1. Go to neon.tech
2. Create new project
3. Copy connection string
```

#### B. Upload ML Models to S3/Storage

```powershell
# Your trained models need external storage
# Upload these files to S3 or similar:
Backend/SafeLink_Backend/models/ann_model.h5
Backend/SafeLink_Backend/models/ann_model.pt
Backend/SafeLink_Backend/models/random_forest_model.pkl
```

### Step 5: Deploy to Vercel

#### Via Vercel Dashboard (Easiest)

1. **Go to [Vercel Dashboard](https://vercel.com/dashboard)**
2. **Click "Add New" → "Project"**
3. **Import your GitHub repository**
4. **Configure settings:**
   ```
   Framework Preset: Other
   Root Directory: ./
   Build Command: cd Frontend && npm run build
   Output Directory: Frontend/dist
   Install Command: npm install
   ```

5. **Add Environment Variables:**
   ```
   # Database
   DATABASE_URL=postgresql://user:pass@host:5432/db
   
   # Security
   SECRET_KEY=your-super-secret-key-min-32-chars
   JWT_SECRET_KEY=your-jwt-secret-key
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   
   # Application
   APP_MODE=production
   NETWORK_INTERFACE=disabled
   ENABLE_PACKET_SNIFFING=false
   
   # API
   API_HOST=0.0.0.0
   API_PORT=8000
   CORS_ORIGINS=https://your-domain.vercel.app
   
   # Frontend
   FRONTEND_URL=https://your-domain.vercel.app
   
   # Threat Intelligence
   ABUSEIPDB_API_KEY=your-api-key-here
   
   # Logging
   LOG_LEVEL=INFO
   LOG_FILE_PATH=/tmp/safelink.log
   
   # Model Configuration (S3 URLs)
   RF_MODEL_PATH=https://s3.amazonaws.com/your-bucket/random_forest_model.pkl
   ANN_MODEL_PATH=https://s3.amazonaws.com/your-bucket/ann_model.h5
   ```

6. **Click "Deploy"**

#### Via Vercel CLI (Alternative)

```powershell
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy
vercel

# Follow prompts:
# - Link to existing project? No
# - Project name: safelink-network-defense
# - Directory: ./
# - Override settings? No

# Deploy to production
vercel --prod
```

### Step 6: Configure GitHub Actions (Optional)

The `.github/workflows/vercel-deploy.yml` file is already created.

**Add these secrets to your GitHub repository:**

1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add secrets:
   ```
   VERCEL_TOKEN          # Get from vercel.com/account/tokens
   VERCEL_ORG_ID         # Get from vercel.json after first deploy
   VERCEL_PROJECT_ID     # Get from vercel.json after first deploy
   ```

3. Push to main branch to trigger auto-deployment

### Step 7: Set Up Backend Worker (For Packet Sniffing)

Since Vercel can't capture packets, set up a separate worker:

**Option A: AWS EC2 Instance**
```bash
# SSH into EC2 instance
ssh ubuntu@your-ec2-ip

# Clone repository
git clone https://github.com/YOUR_USERNAME/safelink-network-defense.git
cd safelink-network-defense/Backend/SafeLink_Backend

# Setup (follow DEPLOYMENT_GUIDE.md)
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run only the packet sniffer
sudo python start_sniffer.py
```

**Option B: DigitalOcean Droplet**
```bash
# Similar to EC2, follow DEPLOYMENT_GUIDE.md
# Configure to send alerts to Vercel API
```

## 🔧 Modified Architecture for Vercel

Update `Backend/SafeLink_Backend/api.py` to work in serverless:

```python
# Add at the top
import os

# Disable packet sniffing in serverless environment
ENABLE_PACKET_SNIFFING = os.getenv("ENABLE_PACKET_SNIFFING", "false").lower() == "true"

if not ENABLE_PACKET_SNIFFING:
    # Skip starting packet sniffer
    # Only provide API endpoints for:
    # - Alert management
    # - ML inference API
    # - Threat intelligence
    # - WebSocket connections
    pass
```

## 📊 What Works on Vercel

✅ **Working Features:**
- Frontend dashboard (React)
- API endpoints (FastAPI)
- User authentication
- Alert viewing/management
- Threat intelligence lookups
- ML model inference (RF only, if model loaded from S3)
- WebSocket notifications

❌ **Non-Working Features:**
- Real-time packet capture
- Network interface monitoring
- Background packet processing
- Model training
- Local database (must use external DB)

## 🔒 Security Configuration

1. **Update CORS origins** in Vercel environment:
   ```
   CORS_ORIGINS=https://your-app.vercel.app,https://your-custom-domain.com
   ```

2. **Enable HTTPS** (automatic with Vercel)

3. **Set secure environment variables** in Vercel dashboard

4. **Use strong SECRET_KEY** (32+ characters)

## 🧪 Testing Deployment

After deployment:

```powershell
# Test API
curl https://your-app.vercel.app/api/health

# Test Frontend
# Open browser: https://your-app.vercel.app
```

## 📈 Monitoring

**Vercel provides:**
- Real-time logs
- Analytics dashboard
- Error tracking
- Performance monitoring

Access at: https://vercel.com/dashboard

## 🔄 Continuous Deployment

Every push to `main` branch will:
1. Trigger GitHub Actions workflow
2. Run tests (if configured)
3. Build frontend
4. Deploy to Vercel
5. Update production site

## ⚡ Performance Optimization

1. **Enable Edge Caching:**
   ```json
   // In vercel.json
   {
     "headers": [
       {
         "source": "/api/(.*)",
         "headers": [
           {
             "key": "Cache-Control",
             "value": "s-maxage=60, stale-while-revalidate"
           }
         ]
       }
     ]
   }
   ```

2. **Use Edge Functions** for faster response times

3. **Optimize model loading** (lazy load, use smaller models)

## 🚨 Important Notes

1. **Packet Sniffing Won't Work** - Vercel is serverless, can't access raw network
2. **Use External Database** - SQLite won't work in serverless
3. **Model File Size** - Must be <50MB or use external storage
4. **Cold Starts** - First request may be slow (3-5 seconds)
5. **Execution Time Limit** - 30 seconds max per request
6. **Memory Limit** - 3GB max (Vercel Pro)

## 🎯 Recommended Production Setup

**For full SafeLink functionality:**

```
┌─────────────────────────────────────────┐
│  Vercel (Frontend + API)                │
│  - React Dashboard                      │
│  - FastAPI REST endpoints               │
│  - User authentication                  │
│  - Alert management API                 │
└──────────────┬──────────────────────────┘
               │
               │ HTTPS/WebSocket
               │
┌──────────────▼──────────────────────────┐
│  VPS/EC2 (Packet Processing)            │
│  - Packet sniffer (Scapy)               │
│  - ML models (RF + ANN)                 │
│  - Continuous learning                  │
│  - Sends alerts to Vercel API           │
└──────────────┬──────────────────────────┘
               │
               │
┌──────────────▼──────────────────────────┐
│  Managed PostgreSQL                     │
│  - Supabase / Neon / AWS RDS            │
│  - Alerts, users, threat intel          │
└─────────────────────────────────────────┘
```

## 🆘 Troubleshooting

### Build Fails
```
Error: Module 'scapy' not found
→ Solution: Use requirements-vercel.txt (excludes Scapy)
```

### Database Connection Error
```
Error: Cannot connect to database
→ Solution: Add DATABASE_URL environment variable in Vercel
```

### Model Loading Error
```
Error: Model file too large
→ Solution: Upload to S3, load from URL in environment variable
```

### Cold Start Timeout
```
Error: Function execution timed out
→ Solution: Optimize imports, use smaller models, increase timeout
```

## 📞 Support

For deployment issues:
- Vercel Documentation: https://vercel.com/docs
- GitHub Issues: https://github.com/YOUR_USERNAME/safelink-network-defense/issues

## ✅ Pre-Deployment Checklist

- [ ] Git repository initialized
- [ ] GitHub repository created and pushed
- [ ] External PostgreSQL database set up
- [ ] ML models uploaded to S3/storage
- [ ] Environment variables configured in Vercel
- [ ] CORS origins updated
- [ ] SECRET_KEY generated (32+ chars)
- [ ] Frontend build tested locally (`npm run build`)
- [ ] API endpoints tested
- [ ] Backend worker VPS set up (for packet capture)
- [ ] GitHub Actions secrets configured (optional)

## 🎉 After Successful Deployment

Your SafeLink application will be live at:
- **Frontend:** https://your-app.vercel.app
- **API:** https://your-app.vercel.app/api
- **Docs:** https://your-app.vercel.app/docs

---

**Note:** For production network security monitoring, use the full VPS deployment from DEPLOYMENT_GUIDE.md. Vercel is best suited for the frontend and API layer only.
