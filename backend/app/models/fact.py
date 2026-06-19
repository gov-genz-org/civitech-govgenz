from sqlalchemy import Column, Integer, String, Text, Boolean, Float, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class FactType(str, enum.Enum):
    deplacement = "deplacement"           # Voyage, déplacement officiel
    discours = "discours"                 # Prise de parole, déclaration
    promesse = "promesse"                 # Engagement public
    decision = "decision"                 # Décret, loi, nomination, décision
    transaction = "transaction"           # Argent reçu, versé, détourné
    projet = "projet"                     # Programme, infrastructure, aide
    arrestation = "arrestation"           # Emprisonnement, détention
    perquisition = "perquisition"         # Descente, saisie
    propagande = "propagande"             # Distribution d'argent, campagne
    plainte = "plainte"                   # Signalement citoyen, dénonciation
    scandale = "scandale"                 # Révélation, corruption avérée
    accord = "accord"                     # Accord, contrat, traité
    nomination = "nomination"             # Prise de poste, mutation
    autre = "autre"


class VerificationStatus(str, enum.Enum):
    unverified = "unverified"     # ⏳ En attente de vérification
    in_review = "in_review"       # 🔍 En cours de vérification
    verified = "verified"         # ✅ Vérifié
    disputed = "disputed"         # ⚠️ Contesté


class ActorRole(str, enum.Enum):
    author = "author"             # Auteur de l'acte
    victim = "victim"             # Victime
    beneficiary = "beneficiary"   # Bénéficiaire
    witness = "witness"           # Témoin
    accomplice = "accomplice"     # Complice / co-responsable
    target = "target"             # Ciblé par l'acte
    investigator = "investigator" # Enquêteur / institution de contrôle


class SourceType(str, enum.Enum):
    press = "press"               # Article de presse (URL)
    official_doc = "official_doc" # Document officiel (décret, rapport)
    testimony = "testimony"       # Témoignage citoyen / ambassador
    financial = "financial"       # Données financières, transaction
    social_media = "social_media" # Post officiel, capture
    other = "other"


class Fact(Base):
    __tablename__ = "facts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    slug = Column(String(500), unique=True, index=True)

    fact_type = Column(Enum(FactType), nullable=False)

    # Contenu
    official_version = Column(Text, nullable=True)   # Ce que l'État / l'acteur dit
    real_version = Column(Text, nullable=True)        # Ce qui est dessous (iceberg)
    context = Column(Text, nullable=True)             # Contexte historique / politique

    # Temporalité (peut être approximative ou historique)
    event_date = Column(String(20), nullable=True)    # "2019-03", "2018", "vers 2015"
    event_date_end = Column(String(20), nullable=True)
    is_historical = Column(Boolean, default=False)
    republic_period = Column(String(50), nullable=True)

    # Localisation
    location = Column(String(200), nullable=True)     # Région, ville, lieu
    region_code = Column(String(50), nullable=True)

    # Secteurs liés (codes des 15 secteurs)
    sector_codes = Column(String(500), nullable=True)  # ex: "mines,environment,security"

    # Scores (0.0 à 10.0)
    gravity_score = Column(Float, default=0.0)        # Gravité de l'acte
    suspicion_score = Column(Float, default=0.0)      # Niveau de suspicion
    opacity_score = Column(Float, default=0.0)        # Opacité (10 = totalement opaque)

    # Statut de vérification
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.unverified)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_note = Column(Text, nullable=True)

    # Visibilité
    is_published = Column(Boolean, default=False)
    is_sensitive = Column(Boolean, default=False)

    # Médias
    images = Column(Text, nullable=True)  # JSON list of image URLs (carousel)

    # Métadonnées
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    fact_actors = relationship("FactActor", back_populates="fact", cascade="all, delete-orphan")
    sources = relationship("FactSource", back_populates="fact", cascade="all, delete-orphan")
    thread_facts = relationship("ThreadFact", back_populates="fact")


class FactActor(Base):
    """Liaison entre un Fait et une Entité avec le rôle de l'entité dans le fait"""
    __tablename__ = "fact_actors"

    id = Column(Integer, primary_key=True, index=True)
    fact_id = Column(Integer, ForeignKey("facts.id"), nullable=False)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    role = Column(Enum(ActorRole), nullable=False, default=ActorRole.author)
    note = Column(Text, nullable=True)

    fact = relationship("Fact", back_populates="fact_actors")
    entity = relationship("Entity", back_populates="fact_actors")


class FactSource(Base):
    """Source documentaire d'un Fait"""
    __tablename__ = "fact_sources"

    id = Column(Integer, primary_key=True, index=True)
    fact_id = Column(Integer, ForeignKey("facts.id"), nullable=False)

    source_type = Column(Enum(SourceType), nullable=False)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=True)
    description = Column(Text, nullable=True)
    date = Column(String(20), nullable=True)
    reliability_score = Column(Float, default=5.0)   # 0-10 : fiabilité de la source
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    fact = relationship("Fact", back_populates="sources")


class Thread(Base):
    """Fil conducteur — chaîne de faits liés dans le temps"""
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    slug = Column(String(500), unique=True, index=True)
    description = Column(Text, nullable=True)

    # Catégorie du fil
    category = Column(String(100), nullable=True)  # corruption, répression, enrichissement, promesses_non_tenues...

    # Secteurs couverts
    sector_codes = Column(String(500), nullable=True)

    # Temporalité
    start_date = Column(String(20), nullable=True)
    end_date = Column(String(20), nullable=True)
    is_ongoing = Column(Boolean, default=True)

    # Scores globaux du fil
    gravity_score = Column(Float, default=0.0)
    suspicion_score = Column(Float, default=0.0)

    # Statut
    is_published = Column(Boolean, default=False)
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.unverified)

    # Médias
    images = Column(Text, nullable=True)  # JSON list of image URLs (carousel)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    thread_facts = relationship("ThreadFact", back_populates="thread", order_by="ThreadFact.position")


class ThreadFact(Base):
    """Liaison ordonnée entre un Thread et ses Faits"""
    __tablename__ = "thread_facts"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False)
    fact_id = Column(Integer, ForeignKey("facts.id"), nullable=False)
    position = Column(Integer, default=0)   # Ordre chronologique dans le thread
    link_note = Column(Text, nullable=True) # Note sur le lien entre ce fait et le thread

    thread = relationship("Thread", back_populates="thread_facts")
    fact = relationship("Fact", back_populates="thread_facts")
