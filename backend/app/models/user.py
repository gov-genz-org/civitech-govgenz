import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Float, Boolean, Text, ForeignKey
from app.database import Base


class UserRole(str, enum.Enum):
    z_citizen = "z_citizen"
    z_ambassador = "z_ambassador"
    moderator = "moderator"
    admin = "admin"
    superadmin = "superadmin"   # Au-dessus de tous — invisible dans les listes publiques


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    suspended = "suspended"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.z_citizen, nullable=False)

    # Profil public
    pseudo = Column(String(100), unique=True, index=True)
    avatar_url = Column(String(500))

    # Profil réel (visible admin uniquement)
    full_name = Column(String(200))
    whatsapp = Column(String(50))
    country = Column(String(100), default="Madagascar")
    city = Column(String(100))
    region = Column(String(100))
    district = Column(String(100))
    commune = Column(String(100))
    fokontany = Column(String(100))

    # Profil socio
    profession = Column(String(200))
    age_range = Column(String(50))
    socio_category = Column(String(100))
    social_links = Column(Text)

    # Engagement citoyen
    priorities = Column(Text)
    contribution_offer = Column(Text)
    injustice_experienced = Column(Text)
    wish_for_madagascar = Column(Text)

    # Statut
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.pending)
    trust_score = Column(Float, default=50.0)
    is_active = Column(Boolean, default=True)

    # Parrainage
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # ID du Z-Ambassador ou admin qui a créé/référé

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
