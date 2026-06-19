from sqlalchemy import Column, Integer, String, Text, Boolean, Float, Enum, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class EntityType(str, enum.Enum):
    # Acteurs nationaux
    politician = "politician"     # Politicien malgache
    institution = "institution"   # Institution d'État malgache
    company = "company"           # Entreprise nationale
    media = "media"               # Média malgache
    ngo = "ngo"                   # ONG nationale
    group = "group"               # Groupe / réseau / mafia
    person = "person"             # Personne physique

    # Acteurs internationaux opérant à Madagascar
    ptf = "ptf"                   # Partenaire Technique et Financier / bailleur
    intl_org = "intl_org"         # Organisation internationale (ONU, UA, FMI…)
    embassy = "embassy"           # Ambassade, consulat, représentation diplomatique
    foreign_co = "foreign_co"     # Entreprise étrangère active à Madagascar
    diaspora_org = "diaspora_org" # Organisation de la diaspora malgache


class EntitySubtype(str, enum.Enum):
    government = "government"
    opposition = "opposition"
    judiciary = "judiciary"
    military = "military"
    religious = "religious"
    economic = "economic"
    foreign = "foreign"
    independent = "independent"
    suspect = "suspect"


class RepublicPeriod(str, enum.Enum):
    republic_1 = "republic_1"        # 1ere République
    republic_2 = "republic_2"        # 2eme République
    republic_3 = "republic_3"        # 3eme République
    republic_4 = "republic_4"        # 4eme République (actuelle)
    transition_2009 = "transition_2009"
    transition_other = "transition_other"
    all_periods = "all_periods"


class LinkType(str, enum.Enum):
    finances = "finances"
    allied = "allied"
    employs = "employs"
    owns = "owns"
    protects = "protects"
    threatens = "threatens"
    controls = "controls"
    belongs_to = "belongs_to"
    opposes = "opposes"
    investigated_by = "investigated_by"


class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, index=True)
    entity_type = Column(Enum(EntityType), nullable=False)
    subtype = Column(Enum(EntitySubtype), nullable=True)

    description = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)

    # Période active
    active_since = Column(String(10), nullable=True)   # Année ou date approximative
    active_until = Column(String(10), nullable=True)
    republic_period = Column(Enum(RepublicPeriod), nullable=True)

    # Localisation
    region = Column(String(100), nullable=True)

    # Scores
    suspicion_score = Column(Float, default=0.0)   # 0-10
    power_index = Column(Float, default=0.0)        # 0-10

    # Flags
    is_sensitive = Column(Boolean, default=False)    # Mafia, réseau suspect
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)        # False = visible connectés seulement

    # Secteurs liés (JSON string des codes de secteur)
    sector_codes = Column(String(500), nullable=True)  # ex: "mines,environment,security"

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    fact_actors = relationship("FactActor", back_populates="entity")
    links_from = relationship("EntityLink", foreign_keys="EntityLink.from_entity_id", back_populates="from_entity")
    links_to = relationship("EntityLink", foreign_keys="EntityLink.to_entity_id", back_populates="to_entity")


class EntityLink(Base):
    """Relation entre deux entités"""
    __tablename__ = "entity_links"

    id = Column(Integer, primary_key=True, index=True)
    from_entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    to_entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)

    link_type = Column(Enum(LinkType), nullable=False)
    description = Column(Text, nullable=True)
    date_start = Column(String(20), nullable=True)
    date_end = Column(String(20), nullable=True)
    strength = Column(Float, default=5.0)   # 0-10 : force du lien
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    from_entity = relationship("Entity", foreign_keys=[from_entity_id], back_populates="links_from")
    to_entity = relationship("Entity", foreign_keys=[to_entity_id], back_populates="links_to")
