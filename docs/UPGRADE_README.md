# SafeLink Network Defense System - Upgrade Guide v2.0

## 🚀 Major Enhancements

### Backend Improvements

#### 1. Real-Time Communication (WebSockets)
- **Implementation**: FastAPI WebSocket endpoint at `/ws/updates`
- **Features**:
  - Push-based alert notifications
  - Sniffer status updates
  - Mitigation event broadcasting
  - Auto-reconnection with exponential backoff
  - Heartbeat/ping-pong mechanism
- **Files**: 
  - `core/websocket_manager.py` - Connection manager
  - `api.py` - WebSocket endpoint
  - Frontend: `src/lib/websocket.js`

#### 2. Authentication & Authorization
- **JWT-based authentication** with refresh tokens
- **Role-Based Access Control (RBAC)**:
  - `admin`: Full system access
  - `operator`: Read + mitigation capabilities
  - `viewer`: Read-only access
- **Features**:
  - Password hashing with bcrypt
  - Token expiration and refresh
  - Permission-based endpoint protection
- **Files**: `core/auth.py`
- **Endpoints**:
  - `POST /auth/register` - User registration
  - `POST /auth/login` - Login and get tokens
  - `GET /auth/me` - Get current user info

#### 3. Automated Mitigation
- **Integration backends**:
  - SNMP (for network switches)
  - SSH/NETCONF (for routers/switches)
  - Firewall REST APIs
- **Safety features**:
  - Whitelist protection
  - Manual approval workflow
  - Rollback capabilities
  - Audit trail
- **Files**: `core/mitigation.py`
- **Endpoints**:
  - `POST /mitigation/request` - Create mitigation request
  - `POST /mitigation/approve/{id}` - Approve pending action
  - `POST /mitigation/execute/{id}` - Execute approved action
  - `POST /mitigation/whitelist` - Add whitelist entry

#### 4. Threat Intelligence Integration
- **AbuseIPDB integration** for IP reputation
- **MAC vendor lookup** (OUI database)
- **Features**:
  - Automatic enrichment
  - Risk scoring
  - Response caching
- **Files**: `core/threat_intel.py`
- **Endpoints**:
  - `GET /threat-intel/enrich/{ip}` - IP reputation lookup
  - `GET /threat-intel/enrich-mac/{mac}` - MAC vendor lookup

#### 5. SIEM Integration
- **Export formats**:
  - Syslog (RFC 5424)
  - CEF (Common Event Format)
  - JSON/JSONL
- **Delivery methods**:
  - UDP/TCP network
  - File export
- **Files**: `core/siem_export.py`
- **Endpoints**:
  - `POST /siem/configure` - Configure SIEM exporter
  - `POST /siem/export-alert/{id}` - Manually export alert

#### 6. Background Task Processing (Celery)
- **Automated tasks**:
  - Alert cleanup (daily)
  - SIEM export (every 15 minutes)
  - Model retraining
  - High-risk auto-mitigation
- **Files**: `core/tasks.py`

### Frontend Improvements

#### 1. Authentication UI
- **Login/Register pages** with form validation
- **Token management** with automatic refresh
- **Role-based UI** hiding/showing features
- **Files**: `src/lib/auth.js`

#### 2. Real-Time Updates
- **WebSocket client** for live data
- **Auto-reconnection** with status indicators
- **Event-driven updates** for alerts, sniffer status
- **Files**: `src/lib/websocket.js`

#### 3. Enhanced Data Visualization
- **Time-series charts** for alert trends
- **Advanced filtering** and search
- **Responsive design** for mobile devices

### Deployment & DevOps

#### 1. Containerization
- **Docker** multi-stage builds
- **Docker Compose** orchestration
- **Services**:
  - Backend (FastAPI + Uvicorn)
  - Frontend (Nginx)
  - PostgreSQL
  - Redis
  - Celery Worker
- **Files**: 
  - `Backend/SafeLink_Backend/Dockerfile`
  - `Frontend/Dockerfile`
  - `docker-compose.yml`

#### 2. Configuration Management
- **Environment variables** for all settings
- **`.env.example`** template
- **Secure defaults** with production warnings

---

## 📦 Installation & Setup

### Prerequisites
- Docker & Docker Compose (recommended)
- OR Python 3.11+, Node.js 20+, PostgreSQL 16+, Redis 7+

### Quick Start with Docker

1. **Clone the repository**:
   ```bash
   cd e:\coreproject
   ```

2. **Configure environment**:
   ```bash
   cp Backend/SafeLink_Backend/.env.example Backend/SafeLink_Backend/.env
   # Edit .env and set DB_PASSWORD, SECRET_KEY, etc.
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

4. **Create admin user** (inside backend container):
   ```bash
   docker exec -it safelink-backend python -c "
   from core.auth import AuthService, UserCreate
   auth = AuthService()
   auth.create_user(
       UserCreate(username='admin', email='admin@safelink.local', password='admin123'),
       role_names=['admin']
   )
   "
   ```

5. **Access the application**:
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Manual Installation

#### Backend Setup

1. **Install dependencies**:
   ```bash
   cd Backend/SafeLink_Backend
   pip install -r requirements.txt
   ```

2. **Configure database**:
   ```bash
   cp .env.example .env
   # Edit .env with your PostgreSQL credentials
   ```

3. **Start Redis**:
   ```bash
   redis-server
   ```

4. **Start Celery worker**:
   ```bash
   celery -A core.tasks worker --loglevel=info
   ```

5. **Start Celery beat** (scheduler):
   ```bash
   celery -A core.tasks beat --loglevel=info
   ```

6. **Run the API server**:
   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload
   ```

#### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd Frontend
   npm install
   ```

2. **Configure API URL**:
   ```bash
   # Create .env file
   echo "VITE_API_BASE_URL=http://localhost:8000" > .env
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

4. **Build for production**:
   ```bash
   npm run build
   ```

---

## 🔧 Configuration

### Environment Variables

See `Backend/SafeLink_Backend/.env.example` for all available options:

**Critical settings**:
- `DB_PASSWORD`: PostgreSQL password
- `SECRET_KEY`: JWT signing key (must be secure in production)
- `ABUSEIPDB_API_KEY`: (Optional) For threat intelligence
- `SIEM_ENABLED`: Enable automatic SIEM export

### Threat Intelligence Setup

1. **Get AbuseIPDB API key**:
   - Register at https://www.abuseipdb.com/
   - Get API key from account settings

2. **Configure in .env**:
   ```env
   ABUSEIPDB_API_KEY=your_api_key_here
   ```

### SIEM Integration Setup

1. **Configure in .env**:
   ```env
   SIEM_ENABLED=true
   SIEM_FORMAT=syslog  # or 'cef', 'json'
   SIEM_HOST=siem.example.com
   SIEM_PORT=514
   SIEM_PROTOCOL=udp  # or 'tcp'
   ```

2. **Or configure via API**:
   ```bash
   curl -X POST http://localhost:8000/siem/configure \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{"format": "syslog", "host": "siem.example.com", "port": 514}'
   ```

### Mitigation Backend Setup

**For SNMP**:
```env
MITIGATION_BACKEND=snmp
MITIGATION_SNMP_COMMUNITY=private
```

**For SSH** (requires additional configuration in code):
- Install `paramiko` or `ncclient`
- Configure device credentials
- Implement device-specific commands

---

## 🔒 Security Considerations

### Production Deployment

1. **Change default secrets**:
   ```env
   SECRET_KEY=<generate-secure-random-key>
   DB_PASSWORD=<strong-database-password>
   ```

2. **Enable HTTPS**:
   - Use reverse proxy (Nginx, Traefik)
   - Configure SSL certificates (Let's Encrypt)

3. **Secure Redis**:
   - Set password in `redis.conf`
   - Use `redis://:password@localhost:6379/0`

4. **Limit network access**:
   - Firewall rules for database (port 5432)
   - Internal network for Redis (port 6379)
   - Expose only frontend (80/443) and API (8000)

5. **Review permissions**:
   - Minimize user with least privileges
   - Regular audit of role assignments

### Mitigation Safeguards

1. **Always use whitelist**:
   ```bash
   # Add critical infrastructure to whitelist
   curl -X POST http://localhost:8000/mitigation/whitelist \
     -H "Authorization: Bearer TOKEN" \
     -d '{"ip": "192.168.1.1", "description": "Default Gateway"}'
   ```

2. **Enable manual approval**:
   ```env
   MITIGATION_AUTO_APPROVE=false
   ```

3. **Test in dry-run mode first**
   - Review mitigation backend implementations
   - Add logging before actual execution

---

## 🧪 Testing

### Backend Tests

```bash
cd Backend/SafeLink_Backend
pytest tests/ -v
```

### Integration Tests

```bash
# Test WebSocket connection
pytest tests/test_websocket.py

# Test authentication
pytest tests/test_auth.py

# Test mitigation
pytest tests/test_mitigation.py
```

### Frontend Tests

```bash
cd Frontend
npm test
```

---

## 📊 Monitoring & Observability

### Metrics (TODO - Phase 5)
- Prometheus instrumentation
- Grafana dashboards
- Alert tracking metrics
- Mitigation success rates

### Logging
- Structured JSON logs
- Log levels via `LOG_LEVEL` env var
- Centralized logging with ELK/Loki

---

## 🔄 Migration from v1.0

1. **Backup existing data**:
   ```bash
   pg_dump safelink_db > backup_$(date +%Y%m%d).sql
   ```

2. **Update database schema**:
   - New tables created automatically on first run
   - Users, Roles, MitigationActions, Whitelist

3. **Update frontend**:
   - New authentication required
   - WebSocket connection replaces polling

4. **Configure new features**:
   - Create admin user
   - Set up SIEM if needed
   - Configure threat intelligence

---

## 📝 API Documentation

Access interactive API docs at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Authentication

All protected endpoints require JWT token:
```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=admin123"

# Use token
curl http://localhost:8000/alerts/latest \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 🚧 Roadmap

### Implemented ✅
- WebSocket real-time communication
- JWT authentication with RBAC
- Automated mitigation framework
- Threat intelligence integration
- SIEM export (Syslog, CEF, JSON)
- Celery background tasks
- Docker containerization

### In Progress 🔄
- Frontend UI for all new features
- Advanced data visualization
- Mobile-responsive design
- Comprehensive integration tests

### Planned 📋
- Multi-interface packet capture
- Random Forest classifier comparison
- Enhanced packet-level features
- Automated model retraining pipeline
- CI/CD pipeline (GitHub Actions)
- Kubernetes deployment manifests
- Prometheus metrics
- End-to-end tests

---

## 🤝 Contributing

See implementation phases in project plan for priorities.

---

## 📄 License

See LICENSE file.

---

## 🆘 Support

For issues or questions:
1. Check API documentation at `/docs`
2. Review logs in `Backend/SafeLink_Backend/logs/`
3. Inspect Docker logs: `docker-compose logs -f`

---

**SafeLink v2.0** - Enhanced Network Defense System
