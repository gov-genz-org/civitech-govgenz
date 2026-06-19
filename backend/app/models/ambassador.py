import enum
import secrets
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, Text, ForeignKey, Float
from app.database import Base


class AmbassadorStatus(str, enum.Enum):
    candidate = "candidate"
    under_review = "under_review"
    active = "active"
    suspended = "suspended"
    rejected = "rejected"


class AmbassadorType(str, enum.Enum):
    individual = "individual"
    organization = "organization"
    association = "association"
    collective = "collective"
    influencer = "influencer"
    artist = "artist"
    content_creator = "content_creator"
    community_leader = "community_leader"
    local_actor = "local_actor"
    partner = "partner"
    public_figure = "public_figure"


class Ambassador(Base):
    __tablename__ = "ambassadors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    ambassador_type = Column(Enum(AmbassadorType), default=AmbassadorType.individual)
    status = Column(Enum(AmbassadorStatus), default=AmbassadorStatus.candidate)

    # Identité publique
    public_name = Column(String(200))
    bio = Column(Text)
    zone_action = Column(String(300))
    sectors_interest = Column(Text)
    objectives = Column(Text)

    # Capacité
    mobilization_capacity = Column(Integer, default=0)
    associated_members = Column(Text)

    # Vérification
    verify_code = Column(String(32), unique=True, index=True)
    charter_signed = Column(Boolean, default=False)
    charter_signed_at = Column(DateTime)

    # Documents (chemins)
    documents = Column(Text)

    # Candidature
    motivation = Column(Text)
    experience = Column(Text)

    # Stats
    total_responses_collected = Column(Integer, default=0)
    valid_responses = Column(Integer, default=0)
    trust_score = Column(Float, default=50.0)

    # Admin
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)

    valid_from = Column(DateTime)
    valid_until = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def generate_verify_code(self):
        self.verify_code = secrets.token_urlsafe(16)
