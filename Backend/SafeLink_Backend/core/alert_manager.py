"""
Alert Management System - Production-Ready Implementation
Handles alert archiving, rotation, and cleanup for SafeLink.
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, Boolean, func
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
import json

from config.settings import DATABASE_URL
from config.logger_config import setup_logger

logger = setup_logger("AlertManager")

Base = declarative_base()

class ArchivedAlert(Base):
    """Archived alerts table for historical data."""
    __tablename__ = "archived_alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_id = Column(Integer)  # ID from original alerts table
    timestamp = Column(TIMESTAMP)
    module = Column(String(50))
    reason = Column(Text)
    src_ip = Column(String(50))
    src_mac = Column(String(50))
    archived_at = Column(TIMESTAMP, default=func.now())
    archive_reason = Column(String(100))  # e.g., "csv_export", "auto_rotation", "manual"


class AlertManager:
    """Manages alert lifecycle: creation, archiving, rotation, and cleanup."""
    
    def __init__(self, database_url: str = None):
        self.engine = create_engine(database_url or DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.info("AlertManager initialized")
    
    def archive_alerts(self, alert_ids: list = None, archive_reason: str = "manual"):
        """
        Archive alerts to archived_alerts table.
        
        Args:
            alert_ids: List of alert IDs to archive (None = all alerts)
            archive_reason: Reason for archiving (csv_export, auto_rotation, manual)
        
        Returns:
            int: Number of alerts archived
        """
        session = self.Session()
        try:
            from core.alert_system import Alert
            
            # Get alerts to archive
            query = session.query(Alert)
            if alert_ids:
                query = query.filter(Alert.id.in_(alert_ids))
            
            alerts_to_archive = query.all()
            count = 0
            
            for alert in alerts_to_archive:
                # Create archived copy
                archived = ArchivedAlert(
                    original_id=alert.id,
                    timestamp=alert.timestamp,
                    module=alert.module,
                    reason=alert.reason,
                    src_ip=alert.src_ip,
                    src_mac=alert.src_mac,
                    archive_reason=archive_reason
                )
                session.add(archived)
                
                # Delete from active alerts
                session.delete(alert)
                count += 1
            
            session.commit()
            logger.info(f"Archived {count} alerts (reason: {archive_reason})")
            return count
            
        except Exception as e:
            logger.error(f"Error archiving alerts: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def auto_rotate_old_alerts(self, days_to_keep: int = 30):
        """
        Automatically archive alerts older than specified days.
        
        Args:
            days_to_keep: Keep only alerts from last N days
        
        Returns:
            int: Number of alerts archived
        """
        session = self.Session()
        try:
            from core.alert_system import Alert
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            old_alerts = session.query(Alert).filter(
                Alert.timestamp < cutoff_date
            ).all()
            
            old_ids = [alert.id for alert in old_alerts]
            
            if old_ids:
                return self.archive_alerts(old_ids, archive_reason="auto_rotation")
            
            return 0
            
        except Exception as e:
            logger.error(f"Error during auto-rotation: {e}")
            raise
        finally:
            session.close()
    
    def limit_active_alerts(self, max_alerts: int = 10000):
        """
        Keep only the most recent N alerts, archive the rest.
        
        Args:
            max_alerts: Maximum number of active alerts to keep
        
        Returns:
            int: Number of alerts archived
        """
        session = self.Session()
        try:
            from core.alert_system import Alert
            
            total_count = session.query(func.count(Alert.id)).scalar()
            
            if total_count > max_alerts:
                # Get IDs of oldest alerts to archive
                alerts_to_archive = total_count - max_alerts
                
                old_alerts = session.query(Alert.id).order_by(
                    Alert.timestamp.asc()
                ).limit(alerts_to_archive).all()
                
                old_ids = [alert.id for alert in old_alerts]
                
                return self.archive_alerts(old_ids, archive_reason="size_limit")
            
            return 0
            
        except Exception as e:
            logger.error(f"Error limiting active alerts: {e}")
            raise
        finally:
            session.close()
    
    def clear_alerts_after_export(self, exported_alert_ids: list):
        """
        Archive alerts that were just exported to CSV.
        
        Args:
            exported_alert_ids: List of alert IDs that were exported
        
        Returns:
            int: Number of alerts archived
        """
        return self.archive_alerts(exported_alert_ids, archive_reason="csv_export")
    
    def get_archived_alerts(self, days: int = 30, limit: int = 100):
        """
        Retrieve archived alerts for analysis.
        
        Args:
            days: Get archived alerts from last N days
            limit: Maximum number of results
        
        Returns:
            list: Archived alerts
        """
        session = self.Session()
        try:
            cutoff = datetime.now() - timedelta(days=days)
            
            results = session.query(ArchivedAlert).filter(
                ArchivedAlert.archived_at >= cutoff
            ).order_by(
                ArchivedAlert.archived_at.desc()
            ).limit(limit).all()
            
            return results
            
        finally:
            session.close()
    
    def get_statistics(self):
        """
        Get alert statistics for monitoring.
        
        Returns:
            dict: Statistics about active and archived alerts
        """
        session = self.Session()
        try:
            from core.alert_system import Alert
            
            active_count = session.query(func.count(Alert.id)).scalar()
            archived_count = session.query(func.count(ArchivedAlert.id)).scalar()
            
            # Get counts by module
            active_by_module = {}
            for module, count in session.query(
                Alert.module, func.count(Alert.id)
            ).group_by(Alert.module).all():
                active_by_module[module] = count
            
            # Get oldest and newest active alert
            oldest = session.query(func.min(Alert.timestamp)).scalar()
            newest = session.query(func.max(Alert.timestamp)).scalar()
            
            return {
                "active_alerts": active_count,
                "archived_alerts": archived_count,
                "total_alerts": active_count + archived_count,
                "active_by_module": active_by_module,
                "oldest_active": oldest.isoformat() if oldest else None,
                "newest_active": newest.isoformat() if newest else None,
            }
            
        finally:
            session.close()
    
    def cleanup_old_archives(self, days_to_keep: int = 365):
        """
        Permanently delete archived alerts older than specified days.
        Use this for GDPR compliance or storage management.
        
        Args:
            days_to_keep: Keep archived alerts for N days
        
        Returns:
            int: Number of archived alerts deleted
        """
        session = self.Session()
        try:
            cutoff = datetime.now() - timedelta(days=days_to_keep)
            
            result = session.query(ArchivedAlert).filter(
                ArchivedAlert.archived_at < cutoff
            ).delete()
            
            session.commit()
            logger.info(f"Deleted {result} old archived alerts (older than {days_to_keep} days)")
            return result
            
        except Exception as e:
            logger.error(f"Error cleaning up archives: {e}")
            session.rollback()
            raise
        finally:
            session.close()


# Singleton instance
alert_manager = AlertManager()
