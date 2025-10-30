# SafeLink Alert Management System

## Overview

The Alert Management System provides production-ready log lifecycle management for SafeLink deployments. Instead of deleting alerts (which violates compliance requirements), this system archives historical data while keeping active alerts clean and manageable.

## Features

### 1. **Alert Archiving**
- Move alerts from active table to archive table
- Preserve complete audit trail
- Track archive reasons for compliance
- Retain all original alert data

### 2. **Automatic Rotation**
- Time-based archiving (default: 30 days)
- Configurable retention policies
- Scheduled background jobs
- No manual intervention required

### 3. **Size Limits**
- Maximum active alerts (default: 10,000)
- Prevents database bloat
- Automatic oldest-first archiving
- Maintains system performance

### 4. **Export Integration**
- Archive alerts after CSV download
- Optional checkbox in UI
- Separates old/new logs automatically
- Production-ready workflow

### 5. **Statistics & Monitoring**
- Active vs archived counts
- Module-based breakdown
- Total alert metrics
- Real-time updates via WebSocket

### 6. **GDPR Compliance**
- Configurable archive retention
- Permanent deletion after N days
- Audit trail preservation
- Privacy-compliant cleanup

## Architecture

### Database Schema

#### Active Alerts Table (`alerts`)
```sql
- id: Primary key
- timestamp: Alert generation time
- module: Detection module (ANN/DFA)
- reason: Alert description
- src_ip: Source IP address
- src_mac: Source MAC address
```

#### Archived Alerts Table (`archived_alerts`)
```sql
- id: Primary key
- original_id: Reference to original alert ID
- timestamp: Original alert timestamp
- module: Detection module
- reason: Alert description
- src_ip: Source IP address
- src_mac: Source MAC address
- archived_at: Archive timestamp
- archive_reason: Why it was archived
```

### Core Components

#### AlertManager Class (`core/alert_manager.py`)
Central management class with methods:

1. **`archive_alerts(alert_ids=None, archive_reason="manual")`**
   - Archives specific alerts or all alerts
   - Returns count of archived alerts
   - Preserves all original data

2. **`auto_rotate_old_alerts(days_to_keep=30)`**
   - Archives alerts older than N days
   - Configurable retention period
   - Returns count of rotated alerts

3. **`limit_active_alerts(max_alerts=10000)`**
   - Keeps only most recent N alerts
   - Archives oldest alerts first
   - Prevents database overflow

4. **`clear_alerts_after_export(exported_ids)`**
   - Archives alerts after CSV download
   - Automatic workflow integration
   - Preserves export history

5. **`get_archived_alerts(days_back=30, limit=1000)`**
   - Retrieves historical alerts
   - Configurable time range
   - Limited result sets

6. **`get_statistics()`**
   - Active/archived counts
   - Module breakdown
   - Total metrics
   - JSON response format

7. **`cleanup_old_archives(days=365)`**
   - GDPR-compliant deletion
   - Permanent removal after N days
   - Irreversible operation
   - Audit log preservation

## API Endpoints

### 1. Download Alerts with Optional Archiving
```
GET /alerts/download?archive_after_download=true
```

**Parameters:**
- `archive_after_download` (bool, optional): Archive alerts after download (default: false)

**Response:**
- CSV file with UTF-8-BOM encoding
- Excel-compatible format
- Automatic archiving if requested

**Example:**
```bash
curl -O "http://localhost:8000/alerts/download?archive_after_download=true"
```

### 2. Manual Archive
```
POST /alerts/archive
```

**Body:**
```json
{
  "alert_ids": [1, 2, 3],  // Optional: null = archive all
  "archive_reason": "manual_clear"
}
```

**Response:**
```json
{
  "archived": 3,
  "reason": "manual_clear"
}
```

### 3. Auto-Rotate Old Alerts
```
POST /alerts/rotate?days_to_keep=30
```

**Parameters:**
- `days_to_keep` (int): Keep alerts from last N days (1-365)

**Response:**
```json
{
  "archived": 142,
  "days_kept": 30
}
```

### 4. Get Management Statistics
```
GET /alerts/stats/management
```

**Response:**
```json
{
  "active_count": 87,
  "archived_count": 1543,
  "total_count": 1630,
  "by_module": {
    "ANN": 45,
    "DFA": 42
  },
  "archived_by_module": {
    "ANN": 892,
    "DFA": 651
  }
}
```

### 5. View Archived Alerts
```
GET /alerts/archived?days_back=30&limit=1000
```

**Parameters:**
- `days_back` (int): Number of days to look back (1-365)
- `limit` (int): Maximum results (1-10000)

**Response:**
```json
{
  "count": 87,
  "days_back": 30,
  "alerts": [
    {
      "id": 1,
      "original_id": 523,
      "timestamp": "2024-01-15T10:30:00",
      "module": "ANN",
      "reason": "Suspicious traffic pattern",
      "src_ip": "192.168.1.100",
      "src_mac": "aa:bb:cc:dd:ee:ff",
      "archived_at": "2024-02-14T08:15:00",
      "archive_reason": "auto_rotation"
    }
  ]
}
```

### 6. Cleanup Old Archives
```
DELETE /alerts/cleanup?days_to_keep=365
```

**Parameters:**
- `days_to_keep` (int): Keep archived alerts for N days (30-3650)

**Response:**
```json
{
  "deleted": 234,
  "retention_days": 365
}
```

**⚠️ WARNING:** This permanently deletes archived alerts. Operation is irreversible!

## Frontend Integration

### Alert Management Panel

The frontend Alerts page (`Frontend/src/views/Alerts.jsx`) includes:

#### Statistics Dashboard
- **Active Alerts**: Current unarchived alerts
- **Archived Alerts**: Historical archived alerts
- **Total Alerts**: Combined count
- Color-coded cards for visual clarity

#### Action Buttons

1. **Download CSV**
   - Exports active alerts to CSV
   - Optional archiving after download
   - Checkbox toggle for user preference

2. **Archive All Alerts**
   - Manual archive trigger
   - Confirmation dialog
   - Immediate UI refresh

3. **Rotate Old Alerts**
   - Prompt for retention days
   - Archives older alerts
   - Shows count of archived alerts

4. **View Archived/Active Toggle**
   - Switch between active and archived views
   - Separate tables for each type
   - Load on-demand for performance

#### Archive Option Toggle
```jsx
<input type="checkbox" checked={archiveAfterDownload} />
Archive alerts after downloading CSV (recommended for production)
```

## Production Deployment Guide

### 1. Initial Setup

Enable archive table creation:
```python
# In your database initialization
from core.alert_manager import Base, engine
Base.metadata.create_all(bind=engine)
```

### 2. Configure Retention Policies

Edit `config/settings.py`:
```python
# Alert Management Settings
ALERT_RETENTION_DAYS = 30  # Archive after 30 days
MAX_ACTIVE_ALERTS = 10000  # Maximum active alerts
ARCHIVE_RETENTION_DAYS = 365  # Keep archives for 1 year
```

### 3. Schedule Background Jobs

Use a task scheduler like APScheduler:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from core.alert_manager import alert_manager

scheduler = BackgroundScheduler()

# Daily rotation at 2 AM
scheduler.add_job(
    func=lambda: alert_manager.auto_rotate_old_alerts(30),
    trigger="cron",
    hour=2,
    minute=0
)

# Size limit check every hour
scheduler.add_job(
    func=lambda: alert_manager.limit_active_alerts(10000),
    trigger="interval",
    hours=1
)

# Quarterly archive cleanup
scheduler.add_job(
    func=lambda: alert_manager.cleanup_old_archives(365),
    trigger="cron",
    day=1,
    hour=3,
    minute=0,
    month="1,4,7,10"  # Jan, Apr, Jul, Oct
)

scheduler.start()
```

### 4. Enable Auto-Archive on Download

In production, default to archiving after download:
```jsx
// Frontend/src/views/Alerts.jsx
const [archiveAfterDownload, setArchiveAfterDownload] = useState(true)
```

### 5. Monitor System Health

Create a monitoring dashboard:
```python
@app.get("/alerts/health")
def get_alert_health():
    stats = alert_manager.get_statistics()
    
    # Alert if approaching limits
    warnings = []
    if stats["active_count"] > 8000:
        warnings.append("Approaching active alert limit")
    if stats["archived_count"] > 100000:
        warnings.append("Large archive size, consider cleanup")
    
    return {
        "status": "healthy" if not warnings else "warning",
        "statistics": stats,
        "warnings": warnings
    }
```

### 6. Configure Backup Strategy

Regular database backups including archived_alerts table:
```bash
# SQLite backup
sqlite3 safelink.db ".backup backup_$(date +%Y%m%d).db"

# PostgreSQL backup
pg_dump -t alerts -t archived_alerts safelink > alerts_backup.sql
```

## Best Practices

### For Development
1. Use short retention (7 days) for faster testing
2. Small max_alerts (1000) to test rotation logic
3. Manual archiving for controlled testing
4. Frequent statistics checks

### For Production
1. **30-day retention** for active alerts
2. **10,000 max active** alerts for performance
3. **365-day archive** retention for compliance
4. **Automatic rotation** enabled via scheduler
5. **Archive on download** enabled by default
6. **Regular backups** of both tables
7. **Monitoring alerts** for approaching limits

### For Compliance (GDPR/HIPAA)
1. Document retention policies
2. Regular archive cleanup (e.g., 1 year)
3. Audit trail preservation
4. User data anonymization options
5. Deletion request handling
6. Access logging

## Troubleshooting

### Issue: Alerts not archiving after download
**Solution:** Check browser console for errors, verify `archive_after_download` parameter in URL

### Issue: Statistics not updating
**Solution:** Ensure WebSocket connection is active, check backend logs for errors

### Issue: Archive table doesn't exist
**Solution:** Run database migrations: `Base.metadata.create_all(bind=engine)`

### Issue: Too many active alerts
**Solution:** Run manual rotation: `POST /alerts/rotate?days_to_keep=7`

### Issue: Performance degradation
**Solution:** 
1. Check archive size with statistics endpoint
2. Run cleanup on old archives
3. Consider database indexing
4. Reduce max_active_alerts limit

## Migration from Old System

If upgrading from a system without archiving:

1. **Create archive table:**
   ```python
   from core.alert_manager import Base, engine
   Base.metadata.create_all(bind=engine)
   ```

2. **Archive existing old alerts:**
   ```python
   from core.alert_manager import alert_manager
   alert_manager.auto_rotate_old_alerts(days_to_keep=30)
   ```

3. **Update frontend:**
   - Replace old Alerts.jsx with new version
   - Test all archive features

4. **Enable scheduled jobs:**
   - Add APScheduler to requirements.txt
   - Configure cron jobs as shown above

5. **Monitor initial run:**
   - Check statistics after first rotation
   - Verify archive table populated
   - Test CSV download with archiving

## Performance Considerations

### Database Indexing
```sql
CREATE INDEX idx_alerts_timestamp ON alerts(timestamp);
CREATE INDEX idx_archived_timestamp ON archived_alerts(timestamp);
CREATE INDEX idx_archived_reason ON archived_alerts(archive_reason);
```

### Query Optimization
- Use pagination for large datasets
- Limit result sets with `limit` parameter
- Index frequently queried columns
- Archive old data regularly

### Memory Management
- Stream large CSV downloads
- Batch archive operations
- Limit in-memory alert lists
- Use database cursors for large queries

## Security Considerations

1. **Authentication:** All endpoints should require valid JWT tokens
2. **Authorization:** Limit archive deletion to admin users only
3. **Rate Limiting:** Prevent abuse of archive/download endpoints
4. **Input Validation:** Sanitize all query parameters
5. **SQL Injection:** Use SQLAlchemy ORM (already protected)
6. **Audit Logging:** Log all archive/deletion operations

## Future Enhancements

- [ ] Export archived alerts to external storage (S3, Azure Blob)
- [ ] Advanced filtering (by module, IP range, date range)
- [ ] Alert deduplication before archiving
- [ ] Compression for archived data
- [ ] Multi-tenant archive isolation
- [ ] Machine learning on archived patterns
- [ ] Automated anomaly detection in archives
- [ ] Custom retention policies per module
- [ ] Role-based archive access control
- [ ] Archive encryption at rest

## Support

For issues or questions:
1. Check backend logs: `Backend/SafeLink_Backend/logs/`
2. Review API documentation: `http://localhost:8000/docs`
3. Test endpoints with Swagger UI
4. Verify database schema matches documentation

---

**Version:** 1.0  
**Last Updated:** 2024  
**Maintainer:** SafeLink Development Team
