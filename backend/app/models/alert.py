import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, Text, ForeignKey
from app.database import Base


class AlertType(str, enum.Enum):
    electricity_cut = "electricity_cut"
    water_cut = "water_cut"
    power_abuse = "power_abuse"
    corruption = "corruption"
    violence = "violence"
    insecurity = "insecurity"
    public_service = "public_service"
    school_problem = "school_problem"
    health_problem = "health_problem"
    infrastructure = "infrastructure"
    environment = "environment"
    other = "other"


class AlertSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertStatus(str, enum.Enum):
    pending = "pending"
    under_review = "under_review"
    verified = "verified"
    published = "published"
    rejected = "rejected"
    archived = "archived"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)

    alert_type = Column(Enum(AlertType), nullable=False)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.medium)
    status = Column(Enum(AlertStatus), default=AlertStatus.pending)

    sector_main = Column(String(50), index=True)
    sectors_related = Column(Text)

    region = Column(String(100))
    district = Column(String(100))
    city = Column(String(100))
    commune = Column(String(100))
    fokontany = Column(String(100))
    location_details = Column(Text)

    proof_urls = Column(Text)   # JSON list of doc URLs
    sources = Column(Text)
    images = Column(Text)       # JSON list of image URLs (carousel)

    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ambassador_id = Column(Integer, ForeignKey("ambassadors.id"))
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)

    is_public = Column(Boolean, default=False)
    is_sensitive = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
