"""
Celery tasks for background processing.
Handles automated mitigation, model retraining, and scheduled operations.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from celery import Celery
from celery.schedules import crontab
import os

# Initialize Celery
celery_app = Celery(
    'safelink',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-old-alerts': {
        'task': 'core.tasks.cleanup_old_alerts',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
    'export-alerts-to-siem': {
        'task': 'core.tasks.export_recent_alerts',
        'schedule': crontab(minute='*/15'),  # Run every 15 minutes
    },
}


@celery_app.task(name='core.tasks.execute_mitigation_async')
def execute_mitigation_async(action_id: int, backend: str = 'snmp'):
    """Execute a mitigation action asynchronously."""
    from core.mitigation import MitigationService
    import asyncio
    
    mitigation_service = MitigationService()
    
    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            mitigation_service.execute_mitigation(action_id, backend)
        )
        return {'success': result, 'action_id': action_id}
    finally:
        loop.close()


@celery_app.task(name='core.tasks.enrich_alert_async')
def enrich_alert_async(alert_id: int):
    """Enrich an alert with threat intelligence asynchronously."""
    from core.threat_intel import threat_intel_service
    from core.alert_system import AlertSystem, Alert
    import asyncio
    
    alert_system = AlertSystem()
    session = alert_system.Session()
    
    try:
        alert = session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return {'success': False, 'error': 'Alert not found'}
        
        # Run async enrichment
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            enrichment = loop.run_until_complete(
                threat_intel_service.enrich_alert(
                    ip=alert.src_ip,
                    mac=alert.src_mac
                )
            )
            return {
                'success': True,
                'alert_id': alert_id,
                'enrichment': enrichment
            }
        finally:
            loop.close()
    finally:
        session.close()


@celery_app.task(name='core.tasks.cleanup_old_alerts')
def cleanup_old_alerts(days_to_keep: int = 90):
    """Clean up alerts older than specified days."""
    from datetime import datetime, timedelta, timezone
    from core.alert_system import AlertSystem, Alert
    from config.logger_config import setup_logger
    
    logger = setup_logger("CleanupTask")
    alert_system = AlertSystem()
    session = alert_system.Session()
    
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        deleted_count = session.query(Alert).filter(
            Alert.timestamp < cutoff_date
        ).delete()
        session.commit()
        
        logger.info(f"Cleaned up {deleted_count} old alerts")
        return {'success': True, 'deleted_count': deleted_count}
    except Exception as e:
        session.rollback()
        logger.error(f"Error cleaning up alerts: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        session.close()


@celery_app.task(name='core.tasks.export_recent_alerts')
def export_recent_alerts(minutes: int = 15):
    """Export recent alerts to configured SIEM systems."""
    from datetime import datetime, timedelta, timezone
    from core.alert_system import AlertSystem, Alert
    from core.siem_export import siem_integration
    from config.logger_config import setup_logger
    
    logger = setup_logger("ExportTask")
    alert_system = AlertSystem()
    session = alert_system.Session()
    
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent_alerts = session.query(Alert).filter(
            Alert.timestamp >= cutoff_time
        ).all()
        
        if not recent_alerts:
            logger.debug("No recent alerts to export")
            return {'success': True, 'exported_count': 0}
        
        # Convert to dict
        alert_dicts = [
            {
                'id': alert.id,
                'timestamp': alert.timestamp.isoformat(),
                'module': alert.module,
                'reason': alert.reason,
                'src_ip': alert.src_ip,
                'src_mac': alert.src_mac
            }
            for alert in recent_alerts
        ]
        
        exported_count = siem_integration.export_batch(alert_dicts)
        logger.info(f"Exported {exported_count} alerts to SIEM")
        
        return {'success': True, 'exported_count': exported_count}
    except Exception as e:
        logger.error(f"Error exporting alerts: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        session.close()


@celery_app.task(name='core.tasks.retrain_model')
def retrain_model(dataset_path: str = None):
    """Retrain the ML model with new data."""
    from pathlib import Path
    from core.ann_classifier import train_model_from_csv
    from config.settings import DATASET_CSV, MODEL_FILENAME, MODELS_DIR
    from config.logger_config import setup_logger
    
    logger = setup_logger("RetrainingTask")
    
    try:
        # Use provided dataset or default
        csv_path = Path(dataset_path) if dataset_path else DATASET_CSV
        
        if not csv_path.exists():
            return {'success': False, 'error': 'Dataset not found'}
        
        # Create timestamped model file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_path = MODELS_DIR / f"ann_model_{timestamp}.pt"
        
        logger.info(f"Starting model retraining with {csv_path}")
        train_model_from_csv(csv_path=csv_path, model_out_path=model_path)
        
        logger.info(f"Model retrained successfully: {model_path}")
        return {
            'success': True,
            'model_path': str(model_path),
            'timestamp': timestamp
        }
    except Exception as e:
        logger.error(f"Error retraining model: {e}")
        return {'success': False, 'error': str(e)}


@celery_app.task(name='core.tasks.auto_mitigate_high_risk')
def auto_mitigate_high_risk(risk_threshold: int = 75):
    """Automatically create mitigation requests for high-risk alerts."""
    from datetime import datetime, timedelta, timezone
    from core.alert_system import AlertSystem, Alert
    from core.mitigation import MitigationService, MitigationRequest, MitigationType
    from core.threat_intel import threat_intel_service
    from config.logger_config import setup_logger
    import asyncio
    
    logger = setup_logger("AutoMitigateTask")
    alert_system = AlertSystem()
    mitigation_service = MitigationService()
    session = alert_system.Session()
    
    try:
        # Get alerts from last hour
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_alerts = session.query(Alert).filter(
            Alert.timestamp >= cutoff_time
        ).all()
        
        mitigations_created = 0
        
        for alert in recent_alerts:
            if not alert.src_ip:
                continue
            
            # Check threat intel
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                enrichment = loop.run_until_complete(
                    threat_intel_service.enrich_alert(ip=alert.src_ip)
                )
            finally:
                loop.close()
            
            risk_score = enrichment.get('risk_score', 0)
            
            if risk_score >= risk_threshold:
                # Create mitigation request
                request = MitigationRequest(
                    action_type=MitigationType.BLOCK_IP,
                    target_ip=alert.src_ip,
                    reason=f"Auto-mitigation: High risk score ({risk_score})",
                    auto_approve=False  # Require manual approval
                )
                
                try:
                    mitigation_service.create_mitigation_request(
                        request,
                        created_by="auto_mitigate_task"
                    )
                    mitigations_created += 1
                    logger.info(f"Created mitigation request for {alert.src_ip} (risk: {risk_score})")
                except Exception as e:
                    logger.error(f"Error creating mitigation for {alert.src_ip}: {e}")
        
        return {
            'success': True,
            'mitigations_created': mitigations_created,
            'alerts_processed': len(recent_alerts)
        }
    except Exception as e:
        logger.error(f"Error in auto-mitigation task: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        session.close()
