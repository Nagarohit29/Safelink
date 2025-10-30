# SafeLink Migration Guide: v1.0 → v2.0

## Overview
This guide helps you migrate from SafeLink v1.0 to v2.0 with minimal downtime and data loss.

---

## Pre-Migration Checklist

### 1. Backup Everything
```powershell
# Backup PostgreSQL database
pg_dump -U postgres -h localhost safelink_db > backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql

# Backup configuration
Copy-Item Backend\SafeLink_Backend\.env backup_env_$(Get-Date -Format 'yyyyMMdd').txt

# Backup models
Copy-Item -Recurse Backend\SafeLink_Backend\models models_backup_$(Get-Date -Format 'yyyyMMdd')

# Backup logs
Copy-Item -Recurse Backend\SafeLink_Backend\logs logs_backup_$(Get-Date -Format 'yyyyMMdd')
```

### 2. Document Current Setup
```powershell
# Note current API endpoints being used
# List all users/clients accessing the system
# Document any custom configurations
# Record current database schema
```

### 3. Review New Features
- Read `UPGRADE_README.md`
- Review `IMPLEMENTATION_SUMMARY.md`
- Understand breaking changes (below)

---

## Breaking Changes

### API Authentication Required
**Impact**: All API endpoints now require JWT authentication

**Migration**:
1. Create admin user using setup script
2. Update clients to include JWT token in requests
3. Implement login flow in applications

**Example**:
```python
# OLD (v1.0)
response = requests.get('http://localhost:8000/alerts/latest')

# NEW (v2.0)
# First, get token
login_response = requests.post(
    'http://localhost:8000/auth/login',
    data={'username': 'admin', 'password': 'your_password'}
)
token = login_response.json()['access_token']

# Then use token
response = requests.get(
    'http://localhost:8000/alerts/latest',
    headers={'Authorization': f'Bearer {token}'}
)
```

### WebSocket Replaces Polling
**Impact**: Frontend should use WebSockets instead of polling `/live-feed`

**Migration**:
```javascript
// OLD (v1.0)
setInterval(() => {
  fetch('/alerts/latest').then(r => r.json()).then(updateUI)
}, 5000)

// NEW (v2.0)
import wsClient from './lib/websocket'
wsClient.connect()
wsClient.on('alert', (alert) => updateUI(alert))
```

### New Database Tables
**Impact**: New tables created automatically, but existing data preserved

**Tables Added**:
- `users`
- `roles`
- `user_roles`
- `mitigation_actions`
- `whitelist`

**Existing Tables**:
- `alerts` - **No changes**, all data preserved

---

## Migration Steps

### Step 1: Stop Current System
```powershell
# If using Docker
docker-compose down

# If running manually
# Stop uvicorn server
# Stop any packet sniffers
# Stop background workers
```

### Step 2: Update Codebase
```powershell
# Pull latest changes
git fetch origin
git checkout main
git pull origin main

# Or download release
# Unzip to project directory
```

### Step 3: Update Dependencies
```powershell
cd Backend\SafeLink_Backend

# Create new virtual environment (recommended)
python -m venv venv_v2
.\venv_v2\Scripts\Activate.ps1

# Install new dependencies
pip install -r requirements.txt
```

### Step 4: Configure Environment
```powershell
# Copy example configuration
Copy-Item .env.example .env

# Edit .env with your settings
# REQUIRED:
# - DB_PASSWORD (use existing or set new)
# - SECRET_KEY (generate random string)

# OPTIONAL:
# - ABUSEIPDB_API_KEY (for threat intel)
# - SIEM_* (for SIEM export)
```

**Generate SECRET_KEY**:
```python
import secrets
print(secrets.token_urlsafe(32))
```

### Step 5: Migrate Database
```powershell
# Start PostgreSQL (if not running)
# Docker:
docker-compose up -d postgres

# Manual:
# Ensure PostgreSQL service is running

# Run setup (creates new tables)
cd Backend\SafeLink_Backend
python setup.py
```

**What happens**:
- New tables created (users, roles, mitigation_actions, whitelist)
- Existing `alerts` table unchanged
- Default roles created (admin, operator, viewer)
- Admin user created (you'll be prompted)

### Step 6: Update Frontend
```powershell
cd Frontend

# Install new dependencies
npm install

# Update .env with API URL
echo "VITE_API_BASE_URL=http://localhost:8000" > .env

# Build
npm run build
```

### Step 7: Start Services
```powershell
# Using Docker (recommended)
.\deploy.ps1 start

# Or manually:
# Terminal 1: Backend
cd Backend\SafeLink_Backend
uvicorn api:app --host 0.0.0.0 --port 8000

# Terminal 2: Celery Worker
celery -A core.tasks worker --loglevel=info

# Terminal 3: Celery Beat
celery -A core.tasks beat --loglevel=info

# Terminal 4: Frontend
cd Frontend
npm run dev
```

### Step 8: Verify Migration
```powershell
# Check system status
.\deploy.ps1 status

# Or manually:
curl http://localhost:8000/system/status

# Check database
docker exec -it safelink-postgres psql -U postgres -d safelink_db -c "SELECT COUNT(*) FROM alerts;"

# Should show your existing alerts
```

### Step 9: Update Client Applications
```powershell
# Update any scripts/applications using the API
# Add authentication flow
# Update to use WebSockets for real-time updates
```

---

## Rollback Plan

### If Migration Fails

1. **Stop v2.0 services**:
   ```powershell
   .\deploy.ps1 stop
   ```

2. **Restore database**:
   ```powershell
   # Drop current database
   docker exec -it safelink-postgres psql -U postgres -c "DROP DATABASE safelink_db;"
   docker exec -it safelink-postgres psql -U postgres -c "CREATE DATABASE safelink_db;"
   
   # Restore from backup
   Get-Content backup_YYYYMMDD_HHMMSS.sql | docker exec -i safelink-postgres psql -U postgres -d safelink_db
   ```

3. **Restore code**:
   ```powershell
   git checkout v1.0
   # Or restore from backup
   ```

4. **Restart v1.0**:
   ```powershell
   # Start services with v1.0 configuration
   ```

---

## Post-Migration Tasks

### 1. Configure New Features

#### Set up Threat Intelligence
```powershell
# Edit .env
ABUSEIPDB_API_KEY=your_api_key_here

# Restart backend
.\deploy.ps1 restart backend
```

#### Configure SIEM Export
```bash
curl -X POST http://localhost:8000/siem/configure \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "format": "syslog",
    "host": "siem.example.com",
    "port": 514
  }'
```

#### Add Whitelist Entries
```bash
curl -X POST http://localhost:8000/mitigation/whitelist \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "ip": "192.168.1.1",
    "description": "Default Gateway"
  }'
```

### 2. Create Additional Users
```python
# Using setup script or Python
from core.auth import AuthService, UserCreate

auth = AuthService()

# Operator
auth.create_user(
    UserCreate(username="operator", email="op@example.com", password="secure_pass"),
    role_names=["operator"]
)

# Viewer
auth.create_user(
    UserCreate(username="viewer", email="view@example.com", password="secure_pass"),
    role_names=["viewer"]
)
```

### 3. Update Monitoring
```powershell
# Set up log monitoring
# Configure alerts for new services (Celery, Redis)
# Update dashboards to include new metrics
```

### 4. Update Documentation
```powershell
# Document new API endpoints used
# Update runbooks with new commands
# Train users on new features
```

---

## Testing After Migration

### 1. Basic Functionality
```bash
# Test authentication
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=your_password"

# Test alerts endpoint
curl http://localhost:8000/alerts/latest \
  -H "Authorization: Bearer TOKEN"

# Test WebSocket (use browser console or wscat)
wscat -c ws://localhost:8000/ws/updates
```

### 2. Data Integrity
```sql
-- Check alert count matches backup
SELECT COUNT(*) FROM alerts;

-- Check latest alerts
SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 10;

-- Verify new tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema='public';
```

### 3. New Features
```bash
# Test mitigation request
curl -X POST http://localhost:8000/mitigation/request \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "block_ip",
    "target_ip": "192.168.1.100",
    "reason": "Test",
    "auto_approve": false
  }'

# Test threat intel
curl http://localhost:8000/threat-intel/enrich/8.8.8.8 \
  -H "Authorization: Bearer TOKEN"
```

---

## Common Migration Issues

### Issue: "Could not connect to database"
**Solution**:
```powershell
# Check PostgreSQL is running
.\deploy.ps1 status

# Verify credentials in .env
Get-Content Backend\SafeLink_Backend\.env | Select-String "DB_"

# Test connection manually
docker exec -it safelink-postgres psql -U postgres -d safelink_db
```

### Issue: "JWT token errors"
**Solution**:
```powershell
# Verify SECRET_KEY is set in .env
# Generate new key if needed
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Restart backend
.\deploy.ps1 restart backend
```

### Issue: "WebSocket connection fails"
**Solution**:
```javascript
// Check CORS settings in api.py
// Verify WebSocket URL (ws:// not http://)
// Check if backend is accessible

// Test from browser console:
const ws = new WebSocket('ws://localhost:8000/ws/updates')
ws.onopen = () => console.log('Connected')
ws.onerror = (e) => console.error('Error:', e)
```

### Issue: "Celery tasks not running"
**Solution**:
```powershell
# Check Redis is running
docker exec safelink-redis redis-cli ping

# Check Celery worker logs
docker logs safelink-celery-worker

# Manually test task
python -c "from core.tasks import cleanup_old_alerts; cleanup_old_alerts.delay()"
```

### Issue: "Missing alerts after migration"
**Solution**:
```sql
-- Check if alerts table exists
SELECT COUNT(*) FROM alerts;

-- If 0, restore from backup
-- See Rollback Plan section
```

---

## Performance Tuning After Migration

### Database
```sql
-- Analyze tables
ANALYZE alerts;
ANALYZE mitigation_actions;

-- Add indexes if needed
CREATE INDEX idx_alerts_timestamp ON alerts(timestamp);
CREATE INDEX idx_mitigation_status ON mitigation_actions(status);
```

### Redis
```redis
# Check memory usage
INFO memory

# Adjust maxmemory if needed
CONFIG SET maxmemory 256mb
```

### WebSocket
```python
# In websocket_manager.py, adjust connection limit if needed
MAX_CONNECTIONS = 100
```

---

## Support During Migration

### Before Starting
- Review all documentation
- Test migration in development environment first
- Schedule migration during maintenance window

### During Migration
- Monitor logs continuously
- Keep backup accessible
- Have rollback plan ready

### After Migration
- Monitor system for 24-48 hours
- Check for any errors in logs
- Verify all features working

### Get Help
- Check `DEV_QUICK_REFERENCE.md` for common commands
- Review logs: `.\deploy.ps1 logs`
- Check API docs: http://localhost:8000/docs

---

## Timeline Estimate

| Task | Estimated Time |
|------|----------------|
| Pre-migration backup | 15 minutes |
| Code update | 10 minutes |
| Dependency installation | 15 minutes |
| Configuration | 20 minutes |
| Database migration | 10 minutes |
| Service startup | 10 minutes |
| Testing | 30 minutes |
| **Total** | **~2 hours** |

*Add more time for large deployments or complex configurations*

---

## Success Criteria

✅ All services running and healthy  
✅ All existing alerts preserved in database  
✅ Authentication working (can login)  
✅ WebSocket connections established  
✅ API endpoints responding correctly  
✅ Background tasks running (Celery)  
✅ No errors in logs  
✅ Frontend accessible and functional  

---

**Migration Guide Version**: 1.0  
**Target Version**: SafeLink v2.0  
**Last Updated**: October 28, 2025
