import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, Text, ForeignKey, JSON
from app.database import Base


class ConsultationStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    closed = "closed"
    archived = "archived"


class ConsultationScope(str, enum.Enum):
    national = "national"
    regional = "regional"
    communal = "communal"
    local = "local"
    sectorial = "sectorial"
    thematic = "thematic"
    targeted = "targeted"


class QuestionType(str, enum.Enum):
    single_choice = "single_choice"
    multiple_choice = "multiple_choice"
    text = "text"
    yes_no = "yes_no"
    priority_scale = "priority_scale"
    satisfaction_scale = "satisfaction_scale"


class CollectionMethod(str, enum.Enum):
    self_online = "self"
    online_form = "online_form"
    door_to_door = "door_to_door"
    phone_call = "phone_call"
    local_meeting = "local_meeting"
    organization_campaign = "organization_campaign"
    community_event = "community_event"
    ambassador_assisted = "ambassador_assisted"


class ResponseStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    contested = "contested"
    rejected = "rejected"


class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    scope = Column(Enum(ConsultationScope), default=ConsultationScope.national)
    status = Column(Enum(ConsultationStatus), default=ConsultationStatus.draft)

    sector_main = Column(String(50), index=True)
    sectors_related = Column(Text)

    # Ciblage
    target_regions = Column(Text)
    target_age_ranges = Column(Text)
    target_professions = Column(Text)
    min_trust_score = Column(Integer, default=0)

    # Dates
    starts_at = Column(DateTime)
    ends_at = Column(DateTime)

    # Auteur
    created_by = Column(Integer, ForeignKey("users.id"))
    validated_by = Column(Integer, ForeignKey("users.id"))

    is_public = Column(Boolean, default=True)
    allow_proof_upload = Column(Boolean, default=False)

    # Insights IA publiables
    published_insight = Column(Text, nullable=True)
    insight_generated_at = Column(DateTime, nullable=True)
    insight_published = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=False)
    order_index = Column(Integer, default=0)
    question_type = Column(Enum(QuestionType), nullable=False)
    text = Column(Text, nullable=False)
    options = Column(JSON)
    is_required = Column(Boolean, default=True)
    allow_proof = Column(Boolean, default=False)


class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    citizen_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ambassador_id = Column(Integer, ForeignKey("ambassadors.id"))

    answer = Column(Text)
    answer_options = Column(JSON)

    collection_method = Column(Enum(CollectionMethod), default=CollectionMethod.self_online)
    status = Column(Enum(ResponseStatus), default=ResponseStatus.pending)

    region = Column(String(100))
    city = Column(String(100))

    citizen_confirmed_at = Column(DateTime)
    citizen_contested_at = Column(DateTime)
    contest_reason = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
