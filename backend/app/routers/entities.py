from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import re

from app.database import get_db
from app.models.entity import Entity, EntityLink, EntityType, EntitySubtype, RepublicPeriod, LinkType
from app.models.fact import Fact, FactActor
from app.services.auth import get_current_user, get_optional_user, require_role
from app.models.user import User, UserRole

router = APIRouter(prefix="/entities", tags=["entities"])


def make_slug(name: str, id: int = None) -> str:
    slug = name.lower()
    slug = re.sub(r'[àáâã]', 'a', slug)
    slug = re.sub(r'[èéêë]', 'e', slug)
    slug = re.sub(r'[îï]', 'i', slug)
    slug = re.sub(r'[ôö]', 'o', slug)
    slug = re.sub(r'[ùûü]', 'u', slug)
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    if id:
        slug = f"{slug}-{id}"
    return slug


# --- Schemas ---

class EntityLinkOut(BaseModel):
    id: int
    link_type: str
    description: Optional[str]
    date_start: Optional[str]
    date_end: Optional[str]
    strength: float
    is_verified: bool
    related_entity_id: int
    related_entity_name: str
    direction: str  # "from" ou "to"

    class Config:
        from_attributes = True


class EntityOut(BaseModel):
    id: int
    name: str
    slug: str
    entity_type: str
    subtype: Optional[str]
    description: Optional[str]
    photo_url: Optional[str]
    active_since: Optional[str]
    active_until: Optional[str]
    republic_period: Optional[str]
    region: Optional[str]
    suspicion_score: float
    power_index: float
    is_sensitive: bool
    is_active: bool
    is_public: bool
    sector_codes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class EntityCreate(BaseModel):
    name: str
    entity_type: EntityType
    subtype: Optional[EntitySubtype] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None
    active_since: Optional[str] = None
    active_until: Optional[str] = None
    republic_period: Optional[RepublicPeriod] = None
    region: Optional[str] = None
    suspicion_score: float = 0.0
    power_index: float = 0.0
    is_sensitive: bool = False
    is_public: bool = True
    sector_codes: Optional[str] = None


class EntityUpdate(BaseModel):
    name: Optional[str] = None
    subtype: Optional[EntitySubtype] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None
    active_since: Optional[str] = None
    active_until: Optional[str] = None
    republic_period: Optional[RepublicPeriod] = None
    region: Optional[str] = None
    suspicion_score: Optional[float] = None
    power_index: Optional[float] = None
    is_sensitive: Optional[bool] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    sector_codes: Optional[str] = None


class EntityLinkCreate(BaseModel):
    to_entity_id: int
    link_type: LinkType
    description: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    strength: float = 5.0


# --- Endpoints publics ---

@router.get("/", response_model=List[EntityOut])
async def list_entities(
    search: Optional[str] = None,
    entity_type: Optional[str] = None,
    sector: Optional[str] = None,
    is_sensitive: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    from app.services.cache import cache

    # Cache uniquement pour les visiteurs non connectés sans filtre (page publique principale)
    use_cache = not current_user and not any([search, entity_type, sector,
                                              is_sensitive is not None, skip])
    if use_cache:
        cached = await cache.get("entities:list")
        if cached:
            return cached

    query = db.query(Entity).filter(Entity.is_active == True)

    if not current_user:
        query = query.filter(Entity.is_public == True)

    if search:
        query = query.filter(Entity.name.ilike(f"%{search}%"))
    if entity_type:
        query = query.filter(Entity.entity_type == entity_type)
    if sector:
        query = query.filter(Entity.sector_codes.ilike(f"%{sector}%"))
    if is_sensitive is not None:
        query = query.filter(Entity.is_sensitive == is_sensitive)

    result = query.order_by(Entity.suspicion_score.desc()).offset(skip).limit(limit).all()
    if use_cache:
        await cache.set("entities:list", [r.__dict__ for r in result])
    return result


@router.get("/{slug}", response_model=dict)
def get_entity(slug: str, db: Session = Depends(get_db),
               current_user: Optional[User] = Depends(get_optional_user)):
    entity = db.query(Entity).filter(Entity.slug == slug).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entité introuvable")

    if not entity.is_public and not current_user:
        raise HTTPException(status_code=403, detail="Connexion requise")

    # Faits liés
    fact_actors = db.query(FactActor).filter(FactActor.entity_id == entity.id).all()
    fact_ids = [fa.fact_id for fa in fact_actors]
    facts = db.query(Fact).filter(
        Fact.id.in_(fact_ids),
        Fact.is_published == True
    ).order_by(Fact.event_date.desc()).limit(10).all()

    # Liens (réseau)
    links_out = []
    for link in entity.links_from:
        links_out.append({
            "id": link.id,
            "link_type": link.link_type,
            "description": link.description,
            "date_start": link.date_start,
            "strength": link.strength,
            "is_verified": link.is_verified,
            "direction": "to",
            "related_entity_id": link.to_entity_id,
            "related_entity_name": link.to_entity.name,
            "related_entity_type": link.to_entity.entity_type,
        })
    for link in entity.links_to:
        links_out.append({
            "id": link.id,
            "link_type": link.link_type,
            "description": link.description,
            "date_start": link.date_start,
            "strength": link.strength,
            "is_verified": link.is_verified,
            "direction": "from",
            "related_entity_id": link.from_entity_id,
            "related_entity_name": link.from_entity.name,
            "related_entity_type": link.from_entity.entity_type,
        })

    return {
        "entity": {
            "id": entity.id,
            "name": entity.name,
            "slug": entity.slug,
            "entity_type": entity.entity_type,
            "subtype": entity.subtype,
            "description": entity.description,
            "photo_url": entity.photo_url,
            "active_since": entity.active_since,
            "active_until": entity.active_until,
            "republic_period": entity.republic_period,
            "region": entity.region,
            "suspicion_score": entity.suspicion_score,
            "power_index": entity.power_index,
            "is_sensitive": entity.is_sensitive,
            "sector_codes": entity.sector_codes,
            "created_at": entity.created_at,
        },
        "facts": [
            {
                "id": f.id,
                "title": f.title,
                "slug": f.slug,
                "fact_type": f.fact_type,
                "event_date": f.event_date,
                "gravity_score": f.gravity_score,
                "suspicion_score": f.suspicion_score,
                "verification_status": f.verification_status,
                "sector_codes": f.sector_codes,
            }
            for f in facts
        ],
        "links": links_out,
        "facts_count": len(fact_ids),
    }


# --- Endpoints admin / modérateur ---

@router.post("/", response_model=EntityOut)
async def create_entity(
    data: EntityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    from app.services.cache import cache
    entity = Entity(**data.model_dump(), created_by=current_user.id)
    db.add(entity)
    db.flush()
    entity.slug = make_slug(entity.name, entity.id)
    db.commit()
    db.refresh(entity)
    await cache.invalidate("entities:list")
    return entity


@router.patch("/{entity_id}", response_model=EntityOut)
async def update_entity(
    entity_id: int,
    data: EntityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    from app.services.cache import cache
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entité introuvable")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(entity, field, value)
    db.commit()
    db.refresh(entity)
    await cache.invalidate("entities:list")
    return entity


@router.delete("/{entity_id}")
async def delete_entity(
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin))
):
    from app.services.cache import cache
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entité introuvable")
    entity.is_active = False
    db.commit()
    await cache.invalidate("entities:list")
    return {"message": "Entité désactivée"}


@router.post("/{entity_id}/links")
def add_entity_link(
    entity_id: int,
    data: EntityLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    from_entity = db.query(Entity).filter(Entity.id == entity_id).first()
    to_entity = db.query(Entity).filter(Entity.id == data.to_entity_id).first()
    if not from_entity or not to_entity:
        raise HTTPException(status_code=404, detail="Entité introuvable")

    link = EntityLink(
        from_entity_id=entity_id,
        **data.model_dump()
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"id": link.id, "message": "Lien créé"}
