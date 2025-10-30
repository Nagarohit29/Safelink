"""
Local Threat Intelligence Database

Stores and manages threat indicators (malicious IPs, MACs, domains, hashes).
Provides CRUD operations and integration with threat_intel module.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

Base = declarative_base()


class ThreatType(str, Enum):
    """Types of threat indicators."""
    IP = "ip"
    MAC = "mac"
    DOMAIN = "domain"
    HASH = "hash"
    URL = "url"


class ThreatSeverity(str, Enum):
    """Threat severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ThreatIndicator(Base):
    """
    Threat indicator database model.
    
    Stores malicious indicators from various threat feeds.
    """
    __tablename__ = "threat_indicators"
    
    id = Column(Integer, primary_key=True, index=True)
    indicator_type = Column(SQLEnum(ThreatType), nullable=False, index=True)
    indicator_value = Column(String(255), nullable=False, unique=True, index=True)
    severity = Column(SQLEnum(ThreatSeverity), nullable=False, default=ThreatSeverity.MEDIUM)
    confidence = Column(Float, default=0.5)  # 0.0 to 1.0
    
    # Metadata
    source = Column(String(100), nullable=True)  # Threat feed name
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # Comma-separated tags
    
    # Timestamps
    first_seen = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    expires_at = Column(DateTime, nullable=True)  # TTL for temporary indicators
    
    # Status
    is_active = Column(Boolean, default=True)
    false_positive = Column(Boolean, default=False)
    
    # Detection stats
    hit_count = Column(Integer, default=0)  # Times this indicator was matched
    last_hit = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<ThreatIndicator {self.indicator_type}:{self.indicator_value}>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "indicator_type": self.indicator_type.value,
            "indicator_value": self.indicator_value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "source": self.source,
            "description": self.description,
            "tags": self.tags.split(",") if self.tags else [],
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "false_positive": self.false_positive,
            "hit_count": self.hit_count,
            "last_hit": self.last_hit.isoformat() if self.last_hit else None
        }


# Pydantic models for API
class ThreatIndicatorCreate(BaseModel):
    """Create threat indicator request."""
    indicator_type: ThreatType
    indicator_value: str = Field(..., min_length=1, max_length=255)
    severity: ThreatSeverity = ThreatSeverity.MEDIUM
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    source: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    ttl_hours: Optional[int] = None  # Auto-expire after N hours


class ThreatIndicatorUpdate(BaseModel):
    """Update threat indicator request."""
    severity: Optional[ThreatSeverity] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    false_positive: Optional[bool] = None


class ThreatIndicatorResponse(BaseModel):
    """Threat indicator response."""
    id: int
    indicator_type: str
    indicator_value: str
    severity: str
    confidence: float
    source: Optional[str]
    description: Optional[str]
    tags: List[str]
    first_seen: str
    last_seen: str
    expires_at: Optional[str]
    is_active: bool
    false_positive: bool
    hit_count: int
    last_hit: Optional[str]
    
    class Config:
        from_attributes = True


class ThreatIntelService:
    """
    Service for managing threat intelligence database.
    
    Provides CRUD operations and integration with threat_intel module.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize threat intel service.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        logger.info("ThreatIntelService initialized")
    
    def add_indicator(self, data: ThreatIndicatorCreate) -> ThreatIndicator:
        """
        Add new threat indicator.
        
        Args:
            data: Indicator creation data
            
        Returns:
            Created ThreatIndicator
        """
        # Check if already exists
        existing = self.db.query(ThreatIndicator).filter(
            ThreatIndicator.indicator_value == data.indicator_value
        ).first()
        
        if existing:
            logger.warning(f"Indicator {data.indicator_value} already exists (ID: {existing.id})")
            # Update last_seen
            existing.last_seen = datetime.now()
            self.db.commit()
            return existing
        
        # Calculate expiration
        expires_at = None
        if data.ttl_hours:
            expires_at = datetime.now() + timedelta(hours=data.ttl_hours)
        
        # Create new indicator
        indicator = ThreatIndicator(
            indicator_type=data.indicator_type,
            indicator_value=data.indicator_value,
            severity=data.severity,
            confidence=data.confidence,
            source=data.source,
            description=data.description,
            tags=",".join(data.tags) if data.tags else None,
            expires_at=expires_at
        )
        
        self.db.add(indicator)
        self.db.commit()
        self.db.refresh(indicator)
        
        logger.info(f"Added threat indicator: {indicator.indicator_type}:{indicator.indicator_value}")
        return indicator
    
    def get_indicator(self, indicator_id: int) -> Optional[ThreatIndicator]:
        """Get indicator by ID."""
        return self.db.query(ThreatIndicator).filter(
            ThreatIndicator.id == indicator_id
        ).first()
    
    def search_indicator(self, value: str) -> Optional[ThreatIndicator]:
        """
        Search for indicator by value.
        
        Args:
            value: Indicator value (IP, MAC, domain, etc.)
            
        Returns:
            ThreatIndicator if found, None otherwise
        """
        indicator = self.db.query(ThreatIndicator).filter(
            ThreatIndicator.indicator_value == value,
            ThreatIndicator.is_active == True,
            ThreatIndicator.false_positive == False
        ).first()
        
        if indicator:
            # Check if expired
            if indicator.expires_at and indicator.expires_at < datetime.now():
                logger.info(f"Indicator {value} expired, deactivating")
                indicator.is_active = False
                self.db.commit()
                return None
            
            # Update hit count
            indicator.hit_count += 1
            indicator.last_hit = datetime.now()
            self.db.commit()
        
        return indicator
    
    def list_indicators(self, 
                       indicator_type: Optional[ThreatType] = None,
                       severity: Optional[ThreatSeverity] = None,
                       is_active: bool = True,
                       limit: int = 100,
                       offset: int = 0) -> List[ThreatIndicator]:
        """
        List threat indicators with filters.
        
        Args:
            indicator_type: Filter by type
            severity: Filter by severity
            is_active: Filter by active status
            limit: Max results
            offset: Result offset for pagination
            
        Returns:
            List of ThreatIndicator
        """
        query = self.db.query(ThreatIndicator)
        
        if indicator_type:
            query = query.filter(ThreatIndicator.indicator_type == indicator_type)
        if severity:
            query = query.filter(ThreatIndicator.severity == severity)
        if is_active is not None:
            query = query.filter(ThreatIndicator.is_active == is_active)
        
        # Remove expired indicators
        query = query.filter(
            (ThreatIndicator.expires_at == None) | 
            (ThreatIndicator.expires_at > datetime.now())
        )
        
        return query.order_by(ThreatIndicator.last_seen.desc()).offset(offset).limit(limit).all()
    
    def update_indicator(self, indicator_id: int, data: ThreatIndicatorUpdate) -> Optional[ThreatIndicator]:
        """
        Update threat indicator.
        
        Args:
            indicator_id: Indicator ID
            data: Update data
            
        Returns:
            Updated ThreatIndicator or None if not found
        """
        indicator = self.get_indicator(indicator_id)
        if not indicator:
            return None
        
        # Update fields
        if data.severity:
            indicator.severity = data.severity
        if data.confidence is not None:
            indicator.confidence = data.confidence
        if data.description:
            indicator.description = data.description
        if data.tags is not None:
            indicator.tags = ",".join(data.tags) if data.tags else None
        if data.is_active is not None:
            indicator.is_active = data.is_active
        if data.false_positive is not None:
            indicator.false_positive = data.false_positive
        
        self.db.commit()
        self.db.refresh(indicator)
        
        logger.info(f"Updated indicator {indicator_id}")
        return indicator
    
    def delete_indicator(self, indicator_id: int) -> bool:
        """
        Delete threat indicator.
        
        Args:
            indicator_id: Indicator ID
            
        Returns:
            True if deleted, False if not found
        """
        indicator = self.get_indicator(indicator_id)
        if not indicator:
            return False
        
        self.db.delete(indicator)
        self.db.commit()
        
        logger.info(f"Deleted indicator {indicator_id}")
        return True
    
    def bulk_import(self, indicators: List[ThreatIndicatorCreate]) -> Dict[str, int]:
        """
        Bulk import threat indicators.
        
        Args:
            indicators: List of indicators to import
            
        Returns:
            Stats dict with counts
        """
        stats = {"added": 0, "updated": 0, "failed": 0}
        
        for ind_data in indicators:
            try:
                self.add_indicator(ind_data)
                stats["added"] += 1
            except Exception as e:
                logger.error(f"Failed to import {ind_data.indicator_value}: {e}")
                stats["failed"] += 1
        
        logger.info(f"Bulk import complete: {stats}")
        return stats
    
    def cleanup_expired(self) -> int:
        """
        Remove expired indicators.
        
        Returns:
            Number of indicators removed
        """
        expired = self.db.query(ThreatIndicator).filter(
            ThreatIndicator.expires_at < datetime.now()
        ).delete()
        
        self.db.commit()
        logger.info(f"Cleaned up {expired} expired indicators")
        
        return expired
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get threat intelligence statistics."""
        total = self.db.query(ThreatIndicator).count()
        active = self.db.query(ThreatIndicator).filter(
            ThreatIndicator.is_active == True
        ).count()
        
        by_type = {}
        for threat_type in ThreatType:
            count = self.db.query(ThreatIndicator).filter(
                ThreatIndicator.indicator_type == threat_type,
                ThreatIndicator.is_active == True
            ).count()
            by_type[threat_type.value] = count
        
        by_severity = {}
        for severity in ThreatSeverity:
            count = self.db.query(ThreatIndicator).filter(
                ThreatIndicator.severity == severity,
                ThreatIndicator.is_active == True
            ).count()
            by_severity[severity.value] = count
        
        return {
            "total_indicators": total,
            "active_indicators": active,
            "by_type": by_type,
            "by_severity": by_severity
        }
