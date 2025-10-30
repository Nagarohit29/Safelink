from __future__ import annotations

import threading
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List
import numpy as np
import pandas as pd

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from config.settings import MODEL_FILENAME, DEVICE, BASE_DIR
from config.logger_config import setup_logger
from core.alert_system import AlertSystem, Alert
from core.ann_classifier import ANNDetector
from core.packet_sniffer import create_async_sniffer
from core.websocket_manager import manager
from core.auth import (
    AuthService, Token, UserCreate, UserResponse, LoginRequest,
    get_current_active_user, require_permission, User
)
from core.mitigation import (
    MitigationService, MitigationRequest, MitigationAction, 
    MitigationStatus, Whitelist
)
from core.threat_intel import threat_intel_service
from core.siem_export import siem_integration
from core.continuous_learner import initialize_continuous_learner, continuous_learner
from core.threat_intel_db import (
    ThreatIntelService, ThreatIndicatorCreate, ThreatIndicatorUpdate,
    ThreatIndicatorResponse, ThreatType, ThreatSeverity, ThreatIndicator, Base
)
from models.random_forest_trainer import RandomForestTrainer, get_rf_trainer
from models.hyperparameter_tuner import HyperparameterTuner, get_tuner

# Initialize logger
logger = setup_logger("API")

app = FastAPI(title="SafeLink API", version="2.0.0", description="SafeLink Network Defense System")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

alert_store = AlertSystem()
SessionLocal = alert_store.Session

# Initialize services
auth_service = AuthService()
mitigation_service = MitigationService()

ALERT_LOG_PATH = Path(BASE_DIR, "logs", "alerts_log.csv")


def serialize_alert(row: Alert) -> dict:
    return {
        "id": row.id,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        "module": row.module,
        "reason": row.reason,
        "src_ip": row.src_ip,
        "src_mac": row.src_mac,
    }


class SnifferManager:
    def __init__(self, alert_system: AlertSystem):
        self._alert_system = alert_system
        self._lock = threading.Lock()
        self._sniffer = None
        self._detector: Optional[ANNDetector] = None
        self._interface: Optional[str] = None
        self._started_at: Optional[datetime] = None

    def _ensure_detector(self):
        if self._detector is None:
            self._detector = ANNDetector(model_path=str(MODEL_FILENAME), device=DEVICE)
            
            # Initialize continuous learning with the detector
            try:
                global continuous_learner
                if continuous_learner is None:
                    logger.info("Initializing continuous learning system...")
                    initialize_continuous_learner(self._detector, auto_start=True)
                    logger.info("✅ Continuous learning enabled!")
            except Exception as e:
                logger.error(f"Failed to initialize continuous learning: {e}")

    def start(self, interface: Optional[str]):
        with self._lock:
            if self._sniffer and self._sniffer.running:
                raise RuntimeError("Sniffer already running")
            self._ensure_detector()
            sniffer = create_async_sniffer(
                interface=interface,
                ann_detector=self._detector,
                alert_system=self._alert_system,
            )
            sniffer.start()
            self._sniffer = sniffer
            self._interface = interface
            self._started_at = datetime.now(timezone.utc)

    def stop(self) -> bool:
        with self._lock:
            if not self._sniffer:
                return False
            sniffer = self._sniffer
            try:
                sniffer.stop()
                sniffer.join(timeout=5)
            except Exception as e:
                # Scapy may throw errors on Windows when stopping
                # Just log and continue cleanup
                print(f"Warning: Error stopping sniffer: {e}")
            finally:
                self._sniffer = None
                self._interface = None
                self._started_at = None
            return True

    def status(self) -> dict:
        with self._lock:
            running = bool(self._sniffer and self._sniffer.running)
            started_at = self._started_at.isoformat() if self._started_at else None
            uptime_seconds = None
            if running and self._started_at:
                uptime_seconds = (datetime.now(timezone.utc) - self._started_at).total_seconds()
            return {
                "running": running,
                "interface": self._interface,
                "started_at": started_at,
                "uptime_seconds": uptime_seconds,
            }


sniffer_manager = SnifferManager(alert_store)


class SnifferStartRequest(BaseModel):
    interface: Optional[str] = None

class ArchiveAlertsRequest(BaseModel):
    alert_ids: Optional[list[int]] = None
    archive_reason: str = "manual"


# ==================== Authentication Endpoints ====================

@app.post("/auth/register", response_model=UserResponse, tags=["Authentication"])
def register_user(user_data: UserCreate):
    """Register a new user."""
    try:
        user = auth_service.create_user(user_data, role_names=["viewer"])
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            roles=[role.name for role in user.roles]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login", response_model=Token, tags=["Authentication"])
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token."""
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Create tokens
    access_token = auth_service.create_access_token(
        data={"sub": user.username, "roles": [role.name for role in user.roles]}
    )
    refresh_token = auth_service.create_refresh_token(
        data={"sub": user.username}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        roles=[role.name for role in current_user.roles]
    )


# ==================== Alert Endpoints ====================

@app.get("/alerts/latest", tags=["Alerts"])
def get_latest_alerts(
    limit: int = Query(20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user)
):
    session: Session = SessionLocal()
    try:
        records = (
            session.query(Alert)
            .order_by(Alert.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [serialize_alert(row) for row in records]
    finally:
        session.close()


@app.get("/alerts/history", tags=["Alerts"])
def get_alert_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user)
):
    session: Session = SessionLocal()
    try:
        records = (
            session.query(Alert)
            .order_by(Alert.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [serialize_alert(row) for row in records]
    finally:
        session.close()


@app.get("/alerts/attackers")
def get_attackers(limit: int = Query(50, ge=1, le=500)):
    session: Session = SessionLocal()
    try:
        rows = (
            session.query(
                Alert.src_ip,
                Alert.src_mac,
                func.count(Alert.id).label("count"),
                func.max(Alert.timestamp).label("last_seen"),
            )
            .filter(Alert.src_ip.isnot(None))
            .group_by(Alert.src_ip, Alert.src_mac)
            .order_by(func.max(Alert.timestamp).desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "src_ip": row.src_ip,
                "src_mac": row.src_mac,
                "count": row.count,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            }
            for row in rows
        ]
    finally:
        session.close()


@app.get("/alerts/stats")
def get_alert_stats():
    session: Session = SessionLocal()
    try:
        total = session.query(func.count(Alert.id)).scalar() or 0
        by_module = (
            session.query(Alert.module, func.count(Alert.id))
            .group_by(Alert.module)
            .all()
        )
        latest = (
            session.query(func.max(Alert.timestamp))
            .scalar()
        )
        return {
            "total_alerts": total,
            "by_module": {module: count for module, count in by_module},
            "latest_alert": latest.isoformat() if latest else None,
        }
    finally:
        session.close()


@app.get("/alerts/download")
def download_alert_log(archive_after_download: bool = Query(False, description="Archive alerts after download")):
    """
    Generate and download alerts as CSV from database.
    
    Args:
        archive_after_download: If True, alerts will be archived after successful download
    """
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse
    from core.alert_manager import alert_manager
    
    session = SessionLocal()
    try:
        # Fetch all alerts from database
        alerts = session.query(Alert).order_by(Alert.timestamp.desc()).all()
        
        # Track alert IDs for archiving
        alert_ids = [alert.id for alert in alerts]
        
        # Create CSV in memory with UTF-8 BOM for Excel compatibility
        output = StringIO()
        # Write UTF-8 BOM for Excel
        output.write('\ufeff')
        
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # Write headers
        writer.writerow(['ID', 'Timestamp', 'Module', 'Reason', 'Source IP', 'Source MAC'])
        
        # Write data
        for alert in alerts:
            writer.writerow([
                str(alert.id) if alert.id else '',
                alert.timestamp.strftime('%Y-%m-%d %H:%M:%S') if alert.timestamp else '',
                str(alert.module) if alert.module else '',
                str(alert.reason) if alert.reason else '',
                str(alert.src_ip) if alert.src_ip else '',
                str(alert.src_mac) if alert.src_mac else ''
            ])
        
        # Prepare response
        output.seek(0)
        content = output.getvalue()
        
        response = StreamingResponse(
            iter([content.encode('utf-8-sig')]),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
        # Archive alerts after successful download if requested
        if archive_after_download and alert_ids:
            try:
                archived_count = alert_manager.clear_alerts_after_export(alert_ids)
                logger.info(f"Archived {archived_count} alerts after CSV download")
            except Exception as e:
                logger.error(f"Failed to archive alerts after download: {e}")
        
        return response
    finally:
        session.close()


@app.post("/alerts/archive", tags=["Alerts"])
def archive_alerts_endpoint(request: ArchiveAlertsRequest):
    """
    Archive specific alerts or all alerts.
    
    Args:
        request: ArchiveAlertsRequest containing alert_ids and archive_reason
            - alert_ids: List of alert IDs to archive (None = all alerts)
            - archive_reason: Reason for archiving
    
    Returns:
        Number of alerts archived
    """
    from core.alert_manager import alert_manager
    
    try:
        count = alert_manager.archive_alerts(request.alert_ids, request.archive_reason)
        return {"archived": count, "reason": request.archive_reason}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/rotate", tags=["Alerts"])
def rotate_old_alerts(days_to_keep: int = Query(30, ge=1, le=365)):
    """
    Archive alerts older than specified days.
    
    Args:
        days_to_keep: Keep only alerts from last N days
    
    Returns:
        Number of alerts archived
    """
    from core.alert_manager import alert_manager
    
    try:
        count = alert_manager.auto_rotate_old_alerts(days_to_keep)
        return {"archived": count, "days_kept": days_to_keep}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts/stats/management", tags=["Alerts"])
def get_alert_management_stats():
    """
    Get statistics about active and archived alerts.
    
    Returns:
        Alert management statistics
    """
    from core.alert_manager import alert_manager
    
    try:
        stats = alert_manager.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/alerts/cleanup", tags=["Alerts"])
def cleanup_old_archives(days_to_keep: int = Query(365, ge=30, le=3650)):
    """
    Permanently delete archived alerts older than specified days.
    WARNING: This is irreversible!
    
    Args:
        days_to_keep: Keep archived alerts for N days
    
    Returns:
        Number of archived alerts deleted
    """
    from core.alert_manager import alert_manager
    
    try:
        count = alert_manager.cleanup_old_archives(days_to_keep)
        return {"deleted": count, "retention_days": days_to_keep}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts/archived", tags=["Alerts"])
def get_archived_alerts(
    days_back: int = Query(30, ge=1, le=365),
    limit: int = Query(1000, ge=1, le=10000)
):
    """
    Retrieve archived alerts from the last N days.
    
    Args:
        days_back: Number of days to look back
        limit: Maximum number of alerts to return
    
    Returns:
        List of archived alerts
    """
    from core.alert_manager import alert_manager
    
    try:
        alerts = alert_manager.get_archived_alerts(days_back, limit)
        return {
            "count": len(alerts),
            "days_back": days_back,
            "alerts": alerts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/network/devices")
def list_network_devices(limit: int = Query(100, ge=1, le=1000)):
    session: Session = SessionLocal()
    try:
        rows = (
            session.query(
                Alert.src_ip,
                Alert.src_mac,
                func.count(Alert.id).label("alerts"),
                func.max(Alert.timestamp).label("last_seen"),
            )
            .filter(Alert.src_ip.isnot(None))
            .group_by(Alert.src_ip, Alert.src_mac)
            .order_by(func.max(Alert.timestamp).desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "ip": row.src_ip,
                "mac": row.src_mac,
                "alerts": row.alerts,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            }
            for row in rows
        ]
    finally:
        session.close()


@app.get("/sniffer/status")
def get_sniffer_status():
    return sniffer_manager.status()


@app.post("/sniffer/start")
def start_sniffer_endpoint(payload: SnifferStartRequest):
    try:
        sniffer_manager.start(payload.interface)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return sniffer_manager.status()


@app.post("/sniffer/stop")
def stop_sniffer_endpoint():
    stopped = sniffer_manager.stop()
    if not stopped:
        raise HTTPException(status_code=400, detail="Sniffer was not running")
    return {"stopped": True}


@app.get("/live-feed")
def get_live_feed(limit: int = Query(20, ge=1, le=100)):
    return get_latest_alerts(limit=limit)


@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive and handle ping/pong
            data = await websocket.receive_text()
            # Echo back for heartbeat
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ==================== Mitigation Endpoints ====================

@app.post("/mitigation/request", tags=["Mitigation"])
def create_mitigation_request(
    request: MitigationRequest,
    current_user: User = Depends(require_permission("mitigate"))
):
    """Create a new mitigation request."""
    try:
        action = mitigation_service.create_mitigation_request(
            request, 
            created_by=current_user.username
        )
        return {
            "id": action.id,
            "status": action.status,
            "action_type": action.action_type,
            "requires_approval": action.requires_approval
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/mitigation/approve/{action_id}", tags=["Mitigation"])
async def approve_mitigation(
    action_id: int,
    current_user: User = Depends(require_permission("mitigate"))
):
    """Approve a pending mitigation action."""
    try:
        success = mitigation_service.approve_mitigation(action_id, current_user.username)
        if not success:
            raise HTTPException(status_code=404, detail="Action not found")
        return {"status": "approved", "action_id": action_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/mitigation/execute/{action_id}", tags=["Mitigation"])
async def execute_mitigation(
    action_id: int,
    backend: str = "snmp",
    current_user: User = Depends(require_permission("mitigate"))
):
    """Execute an approved mitigation action."""
    success = await mitigation_service.execute_mitigation(action_id, backend)
    if not success:
        raise HTTPException(status_code=400, detail="Execution failed")
    return {"status": "executed", "action_id": action_id}


@app.get("/mitigation/pending", tags=["Mitigation"])
def get_pending_mitigations(
    current_user: User = Depends(require_permission("mitigate"))
):
    """Get all pending mitigation actions."""
    actions = mitigation_service.get_pending_actions()
    return [
        {
            "id": action.id,
            "timestamp": action.timestamp.isoformat(),
            "action_type": action.action_type,
            "target_ip": action.target_ip,
            "target_mac": action.target_mac,
            "reason": action.reason,
            "status": action.status
        }
        for action in actions
    ]


@app.get("/mitigation/history", tags=["Mitigation"])
def get_mitigation_history(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user)
):
    """Get mitigation action history."""
    actions = mitigation_service.get_action_history(limit)
    return [
        {
            "id": action.id,
            "timestamp": action.timestamp.isoformat(),
            "action_type": action.action_type,
            "target_ip": action.target_ip,
            "target_mac": action.target_mac,
            "status": action.status,
            "approved_by": action.approved_by,
            "executed_at": action.executed_at.isoformat() if action.executed_at else None
        }
        for action in actions
    ]


@app.get("/mitigation/actions", tags=["Mitigation"])
def get_all_mitigation_actions(
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user)
):
    """Get all mitigation actions (pending, approved, executed, rejected)."""
    actions = mitigation_service.get_action_history(limit)
    return [
        {
            "id": action.id,
            "timestamp": action.timestamp.isoformat(),
            "action_type": action.action_type,
            "target_ip": action.target_ip,
            "target_mac": action.target_mac,
            "reason": action.reason,
            "status": action.status,
            "approved_by": action.approved_by,
            "executed_at": action.executed_at.isoformat() if action.executed_at else None
        }
        for action in actions
    ]


@app.post("/mitigation/whitelist", tags=["Mitigation"])
def add_whitelist_entry(
    ip: Optional[str] = None,
    mac: Optional[str] = None,
    description: str = "",
    current_user: User = Depends(require_permission("configure"))
):
    """Add an entry to the mitigation whitelist."""
    try:
        entry = mitigation_service.add_to_whitelist(
            ip=ip, 
            mac=mac, 
            description=description,
            created_by=current_user.username
        )
        return {
            "id": entry.id,
            "ip_address": entry.ip_address,
            "mac_address": entry.mac_address,
            "description": entry.description
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/mitigation/whitelist", tags=["Mitigation"])
def get_whitelist(
    current_user: User = Depends(get_current_active_user)
):
    """Get all whitelist entries."""
    entries = mitigation_service.get_whitelist()
    return [
        {
            "id": entry.id,
            "ip_address": entry.ip_address,
            "mac_address": entry.mac_address,
            "description": entry.description,
            "created_at": entry.created_at.isoformat(),
            "created_by": entry.created_by
        }
        for entry in entries
    ]


@app.delete("/mitigation/whitelist/{whitelist_id}", tags=["Mitigation"])
def remove_whitelist_entry(
    whitelist_id: int,
    current_user: User = Depends(require_permission("configure"))
):
    """Remove an entry from the mitigation whitelist."""
    try:
        mitigation_service.remove_from_whitelist(whitelist_id)
        return {"message": "Whitelist entry removed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Threat Intelligence Endpoints ====================

@app.get("/threat-intel/enrich/{ip}", tags=["Threat Intelligence"])
async def enrich_ip(
    ip: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get threat intelligence for an IP address."""
    enrichment = await threat_intel_service.enrich_alert(ip=ip)
    return enrichment


@app.get("/threat-intel/enrich-mac/{mac}", tags=["Threat Intelligence"])
async def enrich_mac(
    mac: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get vendor information for a MAC address."""
    enrichment = await threat_intel_service.enrich_alert(mac=mac)
    return enrichment


# ==================== SIEM Export Endpoints ====================

@app.post("/siem/configure", tags=["SIEM"])
def configure_siem(
    format: str,
    host: str,
    port: int = 514,
    protocol: str = "udp",
    current_user: User = Depends(require_permission("configure"))
):
    """Configure SIEM export."""
    if format.lower() == "syslog":
        siem_integration.add_syslog_exporter(host=host, port=port, protocol=protocol)
    elif format.lower() == "cef":
        siem_integration.add_cef_exporter(host=host, port=port, protocol=protocol)
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
    
    return {"status": "configured", "format": format, "host": host, "port": port}


@app.post("/siem/export-alert/{alert_id}", tags=["SIEM"])
def export_alert_to_siem(
    alert_id: int,
    current_user: User = Depends(require_permission("write"))
):
    """Manually export a specific alert to configured SIEM systems."""
    session: Session = SessionLocal()
    try:
        alert = session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert_dict = serialize_alert(alert)
        results = siem_integration.export_alert(alert_dict)
        return {"alert_id": alert_id, "export_results": results}
    finally:
        session.close()


# ==================== System Status Endpoints ====================

@app.get("/system/status", tags=["System"])
def get_system_status(current_user: User = Depends(get_current_active_user)):
    """Get overall system status."""
    sniffer_status = sniffer_manager.status()
    
    session: Session = SessionLocal()
    try:
        total_alerts = session.query(func.count(Alert.id)).scalar() or 0
        pending_mitigations = len(mitigation_service.get_pending_actions())
        
        return {
            "sniffer": sniffer_status,
            "alerts": {
                "total": total_alerts,
                "pending_mitigations": pending_mitigations
            },
            "websocket_connections": manager.get_connection_count(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    finally:
        session.close()


# ==================== Continuous Learning Endpoints ====================

@app.get("/learning/status", tags=["Continuous Learning"])
def get_learning_status(current_user: User = Depends(get_current_active_user)):
    """
    Get continuous learning system status.
    
    Returns:
        Statistics about the continuous learning system
    """
    if continuous_learner is None:
        return {
            "enabled": False,
            "message": "Continuous learning not initialized. Start the sniffer to enable."
        }
    
    stats = continuous_learner.get_statistics()
    return {
        "enabled": True,
        **stats
    }


@app.post("/learning/train-now", tags=["Continuous Learning"])
def trigger_training(current_user: User = Depends(require_permission("manage_system"))):
    """
    Manually trigger a training cycle.
    
    Requires: Admin permission
    """
    if continuous_learner is None:
        raise HTTPException(status_code=503, detail="Continuous learning not initialized")
    
    if continuous_learner.is_training:
        raise HTTPException(status_code=409, detail="Training already in progress")
    
    # Trigger in background thread
    import threading
    threading.Thread(
        target=continuous_learner.force_training_cycle,
        daemon=True
    ).start()
    
    return {"message": "Training cycle started", "status": "in_progress"}


@app.post("/learning/start", tags=["Continuous Learning"])
def start_continuous_learning(current_user: User = Depends(require_permission("manage_system"))):
    """
    Start continuous learning system.
    
    Requires: Admin permission
    """
    if continuous_learner is None:
        raise HTTPException(status_code=503, detail="Continuous learning not initialized")
    
    continuous_learner.start_continuous_learning()
    return {"message": "Continuous learning started", "status": "active"}


@app.post("/learning/stop", tags=["Continuous Learning"])
def stop_continuous_learning(current_user: User = Depends(require_permission("manage_system"))):
    """
    Stop continuous learning system.
    
    Requires: Admin permission
    """
    if continuous_learner is None:
        raise HTTPException(status_code=503, detail="Continuous learning not initialized")
    
    continuous_learner.stop_continuous_learning()
    return {"message": "Continuous learning stopped", "status": "inactive"}


@app.get("/learning/history", tags=["Continuous Learning"])
def get_training_history(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get recent training history.
    
    Args:
        limit: Number of recent training cycles to return
    """
    if continuous_learner is None:
        raise HTTPException(status_code=503, detail="Continuous learning not initialized")
    
    stats = continuous_learner.get_statistics()
    history = stats.get('recent_history', [])
    
    return {
        "total_cycles": stats.get('total_training_cycles', 0),
        "history": history[-limit:]
    }


# ============================================
# THREAT INTELLIGENCE ENDPOINTS
# ============================================

def get_threat_intel_db():
    """Dependency to get threat intel service with DB session."""
    db = SessionLocal()
    try:
        yield ThreatIntelService(db)
    finally:
        db.close()


@app.post("/threat_intel/indicators", response_model=ThreatIndicatorResponse, status_code=201)
async def add_threat_indicator(
    indicator: ThreatIndicatorCreate,
    service: ThreatIntelService = Depends(get_threat_intel_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add new threat indicator."""
    result = service.add_indicator(indicator)
    return result.to_dict()


@app.get("/threat_intel/indicators", response_model=List[ThreatIndicatorResponse])
async def list_threat_indicators(
    indicator_type: Optional[ThreatType] = None,
    severity: Optional[ThreatSeverity] = None,
    is_active: bool = True,
    limit: int = 100,
    offset: int = 0,
    service: ThreatIntelService = Depends(get_threat_intel_db),
    current_user: User = Depends(get_current_active_user)
):
    """List threat indicators with filters."""
    indicators = service.list_indicators(
        indicator_type=indicator_type,
        severity=severity,
        is_active=is_active,
        limit=limit,
        offset=offset
    )
    return [ind.to_dict() for ind in indicators]


@app.get("/threat_intel/indicators/{indicator_id}", response_model=ThreatIndicatorResponse)
async def get_threat_indicator(
    indicator_id: int,
    service: ThreatIntelService = Depends(get_threat_intel_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get threat indicator by ID."""
    indicator = service.get_indicator(indicator_id)
    if not indicator:
        raise HTTPException(status_code=404, detail="Indicator not found")
    return indicator.to_dict()


@app.get("/threat_intel/search/{value}")
async def search_threat_indicator(
    value: str,
    service: ThreatIntelService = Depends(get_threat_intel_db),
    current_user: User = Depends(get_current_active_user)
):
    """Search for threat indicator by value (IP, MAC, etc.)."""
    indicator = service.search_indicator(value)
    if not indicator:
        return {"found": False, "value": value}
    return {"found": True, "indicator": indicator.to_dict()}


@app.put("/threat_intel/indicators/{indicator_id}", response_model=ThreatIndicatorResponse)
async def update_threat_indicator(
    indicator_id: int,
    update_data: ThreatIndicatorUpdate,
    service: ThreatIntelService = Depends(get_threat_intel_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update threat indicator."""
    indicator = service.update_indicator(indicator_id, update_data)
    if not indicator:
        raise HTTPException(status_code=404, detail="Indicator not found")
    return indicator.to_dict()


@app.delete("/threat_intel/indicators/{indicator_id}", status_code=204)
async def delete_threat_indicator(
    indicator_id: int,
    service: ThreatIntelService = Depends(get_threat_intel_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete threat indicator."""
    success = service.delete_indicator(indicator_id)
    if not success:
        raise HTTPException(status_code=404, detail="Indicator not found")


@app.post("/threat_intel/bulk_import")
async def bulk_import_indicators(
    indicators: List[ThreatIndicatorCreate],
    service: ThreatIntelService = Depends(get_threat_intel_db),
    current_user: User = Depends(get_current_active_user)
):
    """Bulk import threat indicators."""
    stats = service.bulk_import(indicators)
    return stats


@app.post("/threat_intel/cleanup")
async def cleanup_expired_indicators(
    service: ThreatIntelService = Depends(get_threat_intel_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove expired threat indicators."""
    removed_count = service.cleanup_expired()
    return {"removed": removed_count}


@app.get("/threat_intel/statistics")
async def get_threat_intel_statistics(
    service: ThreatIntelService = Depends(get_threat_intel_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get threat intelligence statistics."""
    return service.get_statistics()


# ============================================
# RANDOM FOREST ENDPOINTS
# ============================================

class RFTrainRequest(BaseModel):
    """Random Forest training request."""
    dataset_path: str
    n_estimators: int = 100
    max_depth: Optional[int] = None
    min_samples_split: int = 2
    min_samples_leaf: int = 1
    class_weight: Optional[str] = 'balanced'
    test_size: float = 0.2


class RFPredictRequest(BaseModel):
    """Random Forest prediction request."""
    features: List[List[float]]


@app.post("/models/train/rf")
async def train_random_forest(
    request: RFTrainRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Train Random Forest classifier."""
    try:
        from models.random_forest_trainer import train_from_csv
        
        trainer, train_metrics, test_metrics = train_from_csv(
            csv_path=request.dataset_path,
            test_size=request.test_size,
            n_estimators=request.n_estimators,
            max_depth=request.max_depth,
            min_samples_split=request.min_samples_split,
            min_samples_leaf=request.min_samples_leaf,
            class_weight=request.class_weight
        )
        
        return {
            "status": "success",
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "model_path": "models/random_forest_model.joblib"
        }
    except Exception as e:
        logger.error(f"RF training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/predict/rf")
async def predict_random_forest(
    request: RFPredictRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Predict using Random Forest classifier."""
    try:
        trainer = get_rf_trainer()
        
        X = np.array(request.features)
        predictions = trainer.predict(X)
        probabilities = trainer.predict_proba(X)
        
        return {
            "predictions": predictions.tolist(),
            "probabilities": probabilities.tolist()
        }
    except Exception as e:
        logger.error(f"RF prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/rf/info")
async def get_rf_info(current_user: User = Depends(get_current_active_user)):
    """Get Random Forest model information."""
    try:
        trainer = get_rf_trainer()
        
        if trainer.model is None:
            return {"status": "not_trained"}
        
        return {
            "status": "trained",
            "n_estimators": trainer.model.n_estimators,
            "max_depth": trainer.model.max_depth,
            "training_history": trainer.training_history
        }
    except Exception as e:
        logger.error(f"Failed to get RF info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/rf/feature_importance")
async def get_rf_feature_importance(
    current_user: User = Depends(get_current_active_user)
):
    """Get Random Forest feature importances."""
    try:
        trainer = get_rf_trainer()
        importances = trainer.get_feature_importance()
        
        return {
            "feature_importance": importances
        }
    except Exception as e:
        logger.error(f"Failed to get feature importance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/compare/rf_vs_ann")
async def compare_rf_vs_ann(
    current_user: User = Depends(get_current_active_user)
):
    """Compare Random Forest vs ANN performance."""
    try:
        trainer = get_rf_trainer()
        
        # Get ANN metrics (assuming from detector)
        # You would load actual ANN metrics here
        ann_metrics = {
            "accuracy": 0.95,  # Placeholder
            "precision": 0.94,
            "recall": 0.96,
            "f1_score": 0.95,
            "roc_auc": 0.97
        }
        
        comparison = trainer.compare_with_ann(ann_metrics)
        
        return comparison
    except Exception as e:
        logger.error(f"Model comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# HYPERPARAMETER TUNING ENDPOINTS
# ============================================

class TuneRequest(BaseModel):
    """Hyperparameter tuning request."""
    model_type: str  # 'ann' or 'random_forest'
    method: str  # 'optuna' or 'grid_search'
    dataset_path: str
    n_trials: int = 50
    test_size: float = 0.2


@app.post("/models/tune/{model_type}")
async def tune_model(
    model_type: str,
    request: TuneRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Tune model hyperparameters.
    
    Args:
        model_type: 'ann' or 'random_forest'
        request: Tuning configuration
    """
    try:
        tuner = get_tuner()
        
        # Load dataset
        df = pd.read_csv(request.dataset_path)
        X = df.drop(columns=['label']).values
        y = df['label'].values
        
        # Train/val split
        from sklearn.model_selection import train_test_split
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=request.test_size, random_state=42, stratify=y
        )
        
        # Tune based on model type and method
        if model_type == 'random_forest':
            if request.method == 'optuna':
                result = tuner.tune_random_forest_optuna(
                    X_train, y_train, X_val, y_val, 
                    n_trials=request.n_trials
                )
            else:
                result = tuner.tune_random_forest_grid(X_train, y_train)
        
        elif model_type == 'ann':
            if request.method == 'optuna':
                result = tuner.tune_ann_optuna(
                    X_train, y_train, X_val, y_val,
                    n_trials=request.n_trials
                )
            else:
                result = tuner.tune_ann_grid(X_train, y_train)
        
        else:
            raise HTTPException(status_code=400, detail="Invalid model_type")
        
        return result
    
    except Exception as e:
        logger.error(f"Tuning failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/best_params/{model_type}")
async def get_best_params(
    model_type: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get best hyperparameters for model type."""
    try:
        tuner = get_tuner()
        return tuner.get_recommended_params(model_type)
    except Exception as e:
        logger.error(f"Failed to get best params: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/tuning/compare")
async def compare_tuning_methods(
    current_user: User = Depends(get_current_active_user)
):
    """Compare results from different tuning methods."""
    try:
        tuner = get_tuner()
        return tuner.compare_tuning_methods()
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


