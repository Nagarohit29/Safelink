from __future__ import annotations

from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, func
import json
from sqlalchemy.orm import declarative_base, sessionmaker

from config.settings import DATABASE_URL
from config.logger_config import setup_logger
from core.websocket_manager import manager
import asyncio

logger = setup_logger("AlertSystem")

Base = declarative_base()

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP, default=func.now())
    module = Column(String(50))
    reason = Column(Text)
    src_ip = Column(String(50))
    src_mac = Column(String(50))


class AlertSystem:
    """Handles alert generation and relational store logging."""

    def __init__(self, database_url: str | None = None, engine=None):
        self.engine = engine or create_engine(database_url or DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.info("Connected to alert store successfully.")

    def alert(self, module: str, reason: str, ip: str | None = None, mac: str | None = None, details: dict | None = None):
        """Public entry point used by detectors to raise alerts."""
        formatted_reason = reason
        if details:
            formatted_reason = f"{reason} | details={details}"
        self.generate_alert(module=module, reason=formatted_reason, src_ip=ip, src_mac=mac)

    def generate_alert(self, module: str, reason: str, src_ip: str | None, src_mac: str | None):
        """Insert a new alert into the backing store."""
        session = self.Session()
        try:
            alert = Alert(module=module, reason=reason, src_ip=src_ip, src_mac=src_mac)
            session.add(alert)
            session.commit()
            
            # Serialize and broadcast the alert
            alert_data = {
                "id": alert.id,
                "timestamp": alert.timestamp.isoformat(),
                "module": alert.module,
                "reason": alert.reason,
                "src_ip": alert.src_ip,
                "src_mac": alert.src_mac,
            }
            # Run the broadcast in the background
            asyncio.run(manager.broadcast(json.dumps({"type": "new_alert", "data": alert_data})))

            logger.warning(f"[ALERT] ({module}) {reason} | IP={src_ip} | MAC={src_mac}")
        except Exception as exc:  # pragma: no cover - log path
            logger.error(f"Error writing alert to DB: {exc}")
            session.rollback()
        finally:
            session.close()

    def fetch_alerts(self, limit: int = 10):
        """Fetch the latest alerts from DB."""
        session = self.Session()
        try:
            return session.query(Alert).order_by(Alert.id.desc()).limit(limit).all()
        finally:
            session.close()
