# SafeLink v2.0 - Developer Quick Reference

## Quick Start

### Start Development Environment
```powershell
# Start all services
.\deploy.ps1 start

# Run initial setup (first time only)
.\deploy.ps1 setup

# Check status
.\deploy.ps1 status
```

### Access Points
- **Frontend**: http://localhost
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

---

## API Authentication

### Get Token
```bash
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=your_password"

# Response:
# {
#   "access_token": "eyJ...",
#   "refresh_token": "eyJ...",
#   "token_type": "bearer"
# }
```

### Use Token
```bash
curl http://localhost:8000/alerts/latest \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Common Tasks

### Create User
```python
from core.auth import AuthService, UserCreate

auth = AuthService()
user = auth.create_user(
    UserCreate(
        username="operator1",
        email="operator@example.com",
        password="secure_password"
    ),
    role_names=["operator"]
)
```

### Create Mitigation Request
```bash
curl -X POST http://localhost:8000/mitigation/request \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "block_ip",
    "target_ip": "192.168.1.100",
    "reason": "ARP spoofing detected",
    "auto_approve": false
  }'
```

### Approve & Execute Mitigation
```bash
# Approve
curl -X POST http://localhost:8000/mitigation/approve/1 \
  -H "Authorization: Bearer TOKEN"

# Execute
curl -X POST http://localhost:8000/mitigation/execute/1?backend=snmp \
  -H "Authorization: Bearer TOKEN"
```

### Add to Whitelist
```bash
curl -X POST http://localhost:8000/mitigation/whitelist \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.1",
    "description": "Default Gateway"
  }'
```

### Get Threat Intelligence
```bash
# IP reputation
curl http://localhost:8000/threat-intel/enrich/8.8.8.8 \
  -H "Authorization: Bearer TOKEN"

# MAC vendor
curl http://localhost:8000/threat-intel/enrich-mac/00:11:22:33:44:55 \
  -H "Authorization: Bearer TOKEN"
```

### Configure SIEM Export
```bash
curl -X POST http://localhost:8000/siem/configure \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "syslog",
    "host": "siem.example.com",
    "port": 514,
    "protocol": "udp"
  }'
```

---

## WebSocket Client (JavaScript)

```javascript
import wsClient from './lib/websocket'

// Connect
wsClient.connect()

// Listen for alerts
wsClient.on('alert', (alert) => {
  console.log('New alert:', alert)
})

// Listen for sniffer status
wsClient.on('sniffer_status', (status) => {
  console.log('Sniffer status:', status)
})

// Check connection
if (wsClient.isConnected()) {
  console.log('Connected to WebSocket')
}
```

---

## Celery Tasks

### Execute Task Manually
```python
from core.tasks import cleanup_old_alerts, retrain_model

# Cleanup alerts older than 30 days
result = cleanup_old_alerts.delay(days_to_keep=30)

# Retrain model
result = retrain_model.delay(dataset_path="/path/to/data.csv")

# Check result
print(result.get())
```

### Monitor Tasks
```bash
# View Celery logs
docker logs -f safelink-celery-worker

# Or if running manually
celery -A core.tasks inspect active
celery -A core.tasks inspect scheduled
```

---

## Database Access

### Via Docker
```bash
# Connect to PostgreSQL
docker exec -it safelink-postgres psql -U postgres -d safelink_db

# Common queries
SELECT * FROM users;
SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 10;
SELECT * FROM mitigation_actions WHERE status='pending';
```

### Via Python
```python
from core.alert_system import AlertSystem, Alert

alerts = AlertSystem()
session = alerts.Session()

# Query alerts
recent = session.query(Alert).order_by(Alert.timestamp.desc()).limit(10).all()

# Print
for alert in recent:
    print(f"{alert.timestamp} - {alert.module} - {alert.reason}")

session.close()
```

---

## Testing

### Run All Tests
```bash
cd Backend/SafeLink_Backend
pytest tests/ -v
```

### Run Specific Test
```bash
pytest tests/test_auth.py -v
pytest tests/test_mitigation.py::test_create_request -v
```

### With Coverage
```bash
pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html
```

---

## Docker Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery-worker
```

### Restart Service
```bash
docker-compose restart backend
```

### Rebuild After Code Changes
```bash
docker-compose up -d --build
```

### Execute Command in Container
```bash
# Backend shell
docker exec -it safelink-backend bash

# Run Python script
docker exec -it safelink-backend python script.py

# Database shell
docker exec -it safelink-postgres psql -U postgres -d safelink_db
```

---

## Configuration

### Environment Variables
```bash
# Edit .env file
nano Backend/SafeLink_Backend/.env

# Or set in docker-compose.yml
# Or export in shell
export ABUSEIPDB_API_KEY="your_key"
```

### Reload After Config Changes
```bash
# Restart services
.\deploy.ps1 restart

# Or specific service
docker-compose restart backend
```

---

## Debugging

### Enable Debug Logging
```env
LOG_LEVEL=DEBUG
```

### View Real-time Logs
```bash
# All services
.\deploy.ps1 logs

# Specific service
docker-compose logs -f backend
```

### Python Debugger
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use modern breakpoint()
breakpoint()
```

### Check Service Health
```bash
# System status
curl http://localhost:8000/system/status

# Or use deployment script
.\deploy.ps1 status
```

---

## Permissions Reference

### Roles & Permissions

| Role     | Permissions                                    |
|----------|------------------------------------------------|
| Admin    | read, write, delete, configure, mitigate      |
| Operator | read, mitigate                                |
| Viewer   | read                                          |

### Protected Endpoints

| Endpoint | Required Permission |
|----------|---------------------|
| `/alerts/*` | read |
| `/mitigation/request` | mitigate |
| `/mitigation/approve` | mitigate |
| `/mitigation/whitelist` | configure |
| `/siem/configure` | configure |
| `/auth/*` | (public) |

---

## Common Issues

### "Database connection failed"
```bash
# Check if PostgreSQL is running
.\deploy.ps1 status

# Check credentials in .env
cat Backend/SafeLink_Backend/.env | grep DB_
```

### "401 Unauthorized"
```bash
# Get new token
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=your_password"

# Check token expiration (default: 60 minutes)
```

### "WebSocket connection failed"
```javascript
// Check CORS settings
// Check if backend is running
// Check WebSocket URL (ws:// not http://)
```

### "Celery task not running"
```bash
# Check Celery worker
docker logs safelink-celery-worker

# Check Redis
docker exec safelink-redis redis-cli ping
```

---

## Development Workflow

1. **Make code changes**
   ```bash
   # Edit files in Backend/SafeLink_Backend or Frontend
   ```

2. **Rebuild containers**
   ```bash
   docker-compose up -d --build
   ```

3. **Run tests**
   ```bash
   pytest tests/ -v
   ```

4. **Check logs**
   ```bash
   .\deploy.ps1 logs
   ```

5. **Commit changes**
   ```bash
   git add .
   git commit -m "Description"
   git push
   ```

---

## Useful Links

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Celery**: https://docs.celeryproject.org/
- **JWT**: https://jwt.io/
- **Docker Compose**: https://docs.docker.com/compose/

---

## Keyboard Shortcuts (API Docs)

When viewing http://localhost:8000/docs:
- **Authorize** button (top right) - Add JWT token
- **Try it out** - Test endpoints interactively
- **Schema** tab - View request/response models

---

**Quick Reference Version**: 1.0  
**Last Updated**: October 28, 2025
