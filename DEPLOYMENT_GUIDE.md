# SafeLink Network Defense System - Production Deployment Guide

**Version:** 1.0  
**Date:** October 31, 2025  
**Status:** Production Ready (with Development Support)

================================================================================
## 📋 TABLE OF CONTENTS
================================================================================

1. [System Requirements](#system-requirements)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Production Installation](#production-installation)
4. [Configuration for Production](#configuration-for-production)
5. [Database Setup](#database-setup)
6. [Security Hardening](#security-hardening)
7. [Running in Production](#running-in-production)
8. [Monitoring & Maintenance](#monitoring--maintenance)
9. [Development Mode](#development-mode)
10. [Troubleshooting](#troubleshooting)

================================================================================
## 🖥️ SYSTEM REQUIREMENTS
================================================================================

### Minimum Requirements (Small Networks: <100 devices)
- **OS:** Ubuntu 20.04+ / Windows Server 2019+ / Windows 10/11
- **CPU:** 4 cores @ 2.5 GHz
- **RAM:** 8 GB
- **Storage:** 20 GB available
- **Network:** Gigabit Ethernet
- **Privileges:** Administrator/root access

### Recommended Requirements (Enterprise: 100-1000 devices)
- **OS:** Ubuntu 22.04 LTS Server
- **CPU:** 8 cores @ 3.0 GHz
- **RAM:** 16 GB
- **Storage:** 100 GB SSD
- **Network:** 10 Gbps network card
- **Privileges:** Dedicated service account with CAP_NET_RAW

### Software Dependencies
- **Python:** 3.11.9 (exact version recommended)
- **Node.js:** 20.x LTS
- **npm:** 10.x
- **Npcap:** Latest (Windows only)
- **libpcap:** Built-in (Linux)

================================================================================
## ✅ PRE-DEPLOYMENT CHECKLIST
================================================================================

### Infrastructure Readiness
- [ ] Network segment identified for monitoring
- [ ] Static IP address assigned (recommended)
- [ ] Firewall rules configured (ports 8000, 5173)
- [ ] Backup server/storage configured
- [ ] Monitoring system integration planned

### Security Requirements
- [ ] SSL/TLS certificate obtained (for HTTPS)
- [ ] Secure password policy defined
- [ ] Network segmentation reviewed
- [ ] Incident response plan documented
- [ ] Compliance requirements verified (PCI-DSS, HIPAA, etc.)

### Team Readiness
- [ ] SOC team trained on SafeLink interface
- [ ] Administrator trained on system maintenance
- [ ] Escalation procedures documented
- [ ] 24/7 coverage plan established (if required)

================================================================================
## 🚀 PRODUCTION INSTALLATION
================================================================================

### Step 1: System Preparation

#### For Ubuntu/Linux:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11.9
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# Install Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y

# Install system dependencies
sudo apt install build-essential libpcap-dev -y

# Set capabilities for packet capture (non-root)
sudo setcap cap_net_raw+eip $(which python3.11)
```

#### For Windows:
```powershell
# Install Python 3.11.9 (download from python.org)
# Install Node.js 20.x (download from nodejs.org)

# Install Npcap (required for packet capture)
# Download from: https://npcap.com/#download
# Run installer with "WinPcap Compatibility Mode" enabled
```

### Step 2: Clone/Copy Project

```bash
# Create production directory
sudo mkdir -p /opt/safelink
sudo chown $USER:$USER /opt/safelink

# Copy project files (adjust source path)
cp -r /path/to/coreproject/* /opt/safelink/

# Or use Git (if repository exists)
cd /opt/safelink
git clone <repository-url> .
```

### Step 3: Backend Setup

```bash
cd /opt/safelink/Backend/SafeLink_Backend

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux
# OR
.\venv\Scripts\Activate.ps1  # Windows

# Upgrade pip
pip install --upgrade pip

# Install production dependencies only
pip install -r requirements.txt

# Verify installation
python --version  # Should show 3.11.9
pip list | grep fastapi  # Verify FastAPI installed
```

### Step 4: Frontend Setup

```bash
cd /opt/safelink/Frontend

# Install dependencies
npm install

# Build for production
npm run build

# Output will be in dist/ folder
```

================================================================================
## ⚙️ CONFIGURATION FOR PRODUCTION
================================================================================

### 1. Environment Variables (.env file)

Create `.env` file in `Backend/SafeLink_Backend/`:

```bash
# Database Configuration
DATABASE_URL=sqlite:///data/safelink.db
# For PostgreSQL (recommended for production):
# DATABASE_URL=postgresql://user:password@localhost:5432/safelink

# Security
SECRET_KEY=<GENERATE_STRONG_32_CHAR_SECRET>
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"

# Network Interface (check with: ip addr or ipconfig)
NETWORK_INTERFACE=eth0  # Linux
# NETWORK_INTERFACE=Ethernet  # Windows

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# CORS (adjust for your frontend domain)
CORS_ORIGINS=http://localhost:5173,https://yourdomain.com

# AbuseIPDB API (optional - for threat intelligence)
ABUSEIPDB_API_KEY=your_api_key_here

# Logging
LOG_LEVEL=INFO  # Use INFO for production, DEBUG for development
LOG_FILE=logs/safelink.log

# Production Mode
ENVIRONMENT=production
DEBUG=false
```

**Security Note:** Never commit `.env` to version control!

### 2. Generate Strong Secret Key

```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

Copy the output to your `.env` file.

### 3. Network Interface Configuration

**Find your network interface:**

Linux:
```bash
ip addr show
# OR
ip link show
```

Windows:
```powershell
Get-NetAdapter | Select-Object Name, InterfaceDescription, Status
```

Update `NETWORK_INTERFACE` in `.env` with the correct interface name.

### 4. Frontend Configuration

Edit `Frontend/src/lib/api.js` (or equivalent):

```javascript
// Change baseURL to your production backend
const api = axios.create({
  baseURL: 'https://your-domain.com/api',  // Production URL
  // OR for same server: baseURL: window.location.origin + '/api'
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});
```

================================================================================
## 🗄️ DATABASE SETUP
================================================================================

### Initialize Database

```bash
cd /opt/safelink/Backend/SafeLink_Backend

# Activate virtual environment
source venv/bin/activate

# Run database setup script
python Scripts/setup_db.py

# Verify database created
ls -lh data/safelink.db
```

### For PostgreSQL (Production Recommended)

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Create database and user
sudo -u postgres psql
```

```sql
CREATE DATABASE safelink;
CREATE USER safelink_user WITH PASSWORD 'strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE safelink TO safelink_user;
\q
```

Update `.env`:
```
DATABASE_URL=postgresql://safelink_user:strong_password_here@localhost:5432/safelink
```

================================================================================
## 🔒 SECURITY HARDENING
================================================================================

### 1. SSL/TLS Setup (HTTPS)

#### Using Nginx as Reverse Proxy (Recommended)

Install Nginx:
```bash
sudo apt install nginx -y
```

Create Nginx configuration (`/etc/nginx/sites-available/safelink`):

```nginx
# SafeLink Production Configuration
upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Certificate (use Let's Encrypt or your certificate)
    ssl_certificate /etc/ssl/certs/safelink.crt;
    ssl_certificate_key /etc/ssl/private/safelink.key;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Frontend (static files)
    location / {
        root /opt/safelink/Frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # Backend API
    location /api {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

Enable and start Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/safelink /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
sudo systemctl enable nginx
```

#### Get Free SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

### 2. Firewall Configuration

```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable

# Block direct access to backend port
sudo ufw deny 8000/tcp
```

### 3. Create Service User (Linux)

```bash
# Create dedicated user (no login shell)
sudo useradd -r -s /bin/false safelink

# Set ownership
sudo chown -R safelink:safelink /opt/safelink

# Grant packet capture capability
sudo setcap cap_net_raw+eip /opt/safelink/Backend/SafeLink_Backend/venv/bin/python3.11
```

### 4. Rate Limiting (Add to FastAPI)

Install dependency:
```bash
pip install slowapi
```

Update `api.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/auth/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
async def login(request: Request, ...):
    # ... existing code
```

================================================================================
## 🏃 RUNNING IN PRODUCTION
================================================================================

### Option 1: Systemd Service (Linux - Recommended)

Create systemd service file (`/etc/systemd/system/safelink-backend.service`):

```ini
[Unit]
Description=SafeLink Network Defense System - Backend
After=network.target

[Service]
Type=simple
User=safelink
Group=safelink
WorkingDirectory=/opt/safelink/Backend/SafeLink_Backend
Environment="PATH=/opt/safelink/Backend/SafeLink_Backend/venv/bin"

# Load environment variables
EnvironmentFile=/opt/safelink/Backend/SafeLink_Backend/.env

# Run with 4 workers (adjust based on CPU cores)
ExecStart=/opt/safelink/Backend/SafeLink_Backend/venv/bin/uvicorn api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    --access-log

# Restart on failure
Restart=on-failure
RestartSec=5s

# Security
NoNewPrivileges=true
PrivateTmp=true
AmbientCapabilities=CAP_NET_RAW

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable safelink-backend
sudo systemctl start safelink-backend

# Check status
sudo systemctl status safelink-backend

# View logs
sudo journalctl -u safelink-backend -f
```

### Option 2: PM2 (Node.js Process Manager)

```bash
# Install PM2
npm install -g pm2

# Create PM2 ecosystem file (ecosystem.config.js)
cd /opt/safelink
```

Create `ecosystem.config.js`:
```javascript
module.exports = {
  apps: [{
    name: 'safelink-backend',
    script: '/opt/safelink/Backend/SafeLink_Backend/venv/bin/uvicorn',
    args: 'api:app --host 0.0.0.0 --port 8000 --workers 4',
    cwd: '/opt/safelink/Backend/SafeLink_Backend',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production'
    }
  }]
};
```

Start with PM2:
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup  # Enable on boot
```

### Option 3: Docker (Alternative)

Create `Dockerfile` in `Backend/SafeLink_Backend/`:

```dockerfile
FROM python:3.11.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

Build and run:
```bash
docker build -t safelink-backend .
docker run -d -p 8000:8000 --name safelink --cap-add=NET_RAW safelink-backend
```

================================================================================
## 📊 MONITORING & MAINTENANCE
================================================================================

### 1. Log Monitoring

**View logs:**
```bash
# Systemd service logs
sudo journalctl -u safelink-backend -f

# Application logs
tail -f /opt/safelink/Backend/SafeLink_Backend/logs/safelink.log

# Alert logs
tail -f /opt/safelink/Backend/SafeLink_Backend/logs/alerts_log.csv
```

**Log rotation setup** (`/etc/logrotate.d/safelink`):
```
/opt/safelink/Backend/SafeLink_Backend/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 640 safelink safelink
}
```

### 2. Database Maintenance

**Backup database (daily cron job):**
```bash
# Add to crontab (crontab -e)
0 2 * * * /usr/bin/sqlite3 /opt/safelink/Backend/SafeLink_Backend/data/safelink.db ".backup '/backup/safelink_$(date +\%Y\%m\%d).db'"
```

**Archive old alerts (monthly):**
```bash
# Add to crontab
0 3 1 * * cd /opt/safelink/Backend/SafeLink_Backend && venv/bin/python -c "from core.alert_system import archive_old_alerts; archive_old_alerts(days=90)"
```

### 3. Health Check Endpoint

Add to `api.py`:
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0"
    }
```

Monitor with:
```bash
curl http://localhost:8000/health
```

### 4. Performance Monitoring

Install monitoring tools:
```bash
pip install prometheus-client
```

Add metrics endpoint to `api.py`:
```python
from prometheus_client import Counter, Histogram, generate_latest

alerts_counter = Counter('alerts_total', 'Total alerts generated')
inference_time = Histogram('inference_duration_seconds', 'Model inference time')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### 5. Alert Volume Monitoring

Create monitoring script (`/opt/safelink/scripts/monitor_alerts.sh`):
```bash
#!/bin/bash
ALERT_COUNT=$(tail -100 /opt/safelink/Backend/SafeLink_Backend/logs/alerts_log.csv | wc -l)

if [ $ALERT_COUNT -gt 50 ]; then
    echo "HIGH ALERT VOLUME: $ALERT_COUNT alerts in last 100 entries" | \
    mail -s "SafeLink Alert Spike" admin@company.com
fi
```

Add to crontab (every 10 minutes):
```bash
*/10 * * * * /opt/safelink/scripts/monitor_alerts.sh
```

================================================================================
## 🔧 DEVELOPMENT MODE
================================================================================

### Running in Development Mode

When you need to develop/test without affecting production:

```bash
# 1. Switch to development branch (if using Git)
git checkout development

# 2. Use separate .env file
cp .env .env.production
cp .env.example .env.development

# Edit .env.development:
# ENVIRONMENT=development
# DEBUG=true
# LOG_LEVEL=DEBUG

# 3. Run backend in development mode
cd Backend/SafeLink_Backend
source venv/bin/activate
uvicorn api:app --reload --host 127.0.0.1 --port 8001

# 4. Run frontend in development mode
cd ../../Frontend
npm run dev
```

### Development vs Production Differences

| Feature | Development | Production |
|---------|-------------|------------|
| Auto-reload | ✅ Yes (`--reload`) | ❌ No |
| Debug mode | ✅ Enabled | ❌ Disabled |
| Workers | 1 | 4+ |
| Logging | DEBUG | INFO/WARNING |
| Port | 8001 | 8000 |
| Host | 127.0.0.1 | 0.0.0.0 |
| HTTPS | ❌ HTTP | ✅ HTTPS |
| Database | SQLite (dev) | PostgreSQL |

### Testing Changes Before Deployment

```bash
# 1. Make changes in development
# 2. Run tests
cd Backend/SafeLink_Backend
pytest tests/

# 3. Run local production simulation
uvicorn api:app --host 127.0.0.1 --port 8000 --workers 4

# 4. If tests pass, merge to production
git checkout main
git merge development

# 5. Deploy to production
sudo systemctl restart safelink-backend
```

================================================================================
## 🐛 TROUBLESHOOTING
================================================================================

### Issue: Cannot capture packets (Permission Denied)

**Solution (Linux):**
```bash
sudo setcap cap_net_raw+eip $(which python3.11)
# OR run with sudo (not recommended)
```

**Solution (Windows):**
```powershell
# Run PowerShell as Administrator
# Verify Npcap installed correctly
```

### Issue: Port 8000 already in use

**Solution:**
```bash
# Find process using port 8000
sudo lsof -i :8000
# OR
sudo netstat -tulpn | grep 8000

# Kill process
sudo kill -9 <PID>
```

### Issue: Frontend cannot connect to backend

**Solution:**
1. Check CORS settings in `.env`
2. Verify API URL in frontend `api.js`
3. Check firewall rules
4. Verify backend is running: `curl http://localhost:8000/health`

### Issue: High memory usage

**Solution:**
```bash
# Reduce number of workers
# Edit systemd service: --workers 2 (instead of 4)

# Clear old logs
cd /opt/safelink/Backend/SafeLink_Backend
rm logs/*.log.gz
```

### Issue: Database locked

**Solution:**
```bash
# SQLite limitation - switch to PostgreSQL
# OR reduce concurrent write operations
```

### Common Commands Cheat Sheet

```bash
# Start backend
sudo systemctl start safelink-backend

# Stop backend
sudo systemctl stop safelink-backend

# Restart backend
sudo systemctl restart safelink-backend

# View logs
sudo journalctl -u safelink-backend -f

# Check status
sudo systemctl status safelink-backend

# Test API
curl http://localhost:8000/health

# Check network interface
ip addr show

# View recent alerts
tail -f Backend/SafeLink_Backend/logs/alerts_log.csv
```

================================================================================
## 📚 ADDITIONAL RESOURCES
================================================================================

- **Documentation:** `/opt/safelink/docs/`
- **Support:** Create GitHub issue or contact admin
- **Updates:** Check for updates monthly
- **Backup Location:** `/backup/safelink_*`

================================================================================
## ✅ POST-DEPLOYMENT VERIFICATION
================================================================================

After deployment, verify everything works:

```bash
# 1. Check service running
sudo systemctl status safelink-backend

# 2. Test health endpoint
curl https://your-domain.com/api/health

# 3. Check logs for errors
sudo journalctl -u safelink-backend --since "10 minutes ago"

# 4. Verify packet capture
# Login to web interface and check system status

# 5. Generate test alert
cd /opt/safelink/Backend/SafeLink_Backend/utils
python generate_attack_traffic.py

# 6. Verify alert appears in web interface
```

================================================================================
## 🎉 DEPLOYMENT COMPLETE!
================================================================================

Your SafeLink system is now running in production mode while maintaining
development capabilities. 

**Production URL:** https://your-domain.com
**API Endpoint:** https://your-domain.com/api
**Health Check:** https://your-domain.com/api/health

For questions or issues, refer to the troubleshooting section or contact
the system administrator.

**Remember:**
- Keep `.env` file secure (never commit to Git)
- Regular backups (daily recommended)
- Monitor logs for anomalies
- Update dependencies monthly
- Review alerts daily

Happy hunting! 🛡️🔍
