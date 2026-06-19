from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import or_, and_
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import re

from app.database import get_db
from app.models.fact import (
    Fact, FactActor, FactSource, Thread, ThreadFact,
    FactType, VerificationStatus, ActorRole, SourceType
)
from app.models.entity import Entity
from app.services.auth import get_current_user, get_optional_user, require_role, is_staff
from app.models.user import User, UserRole

router = APIRouter(prefix="/facts", tags=["facts"])


def make_slug(title: str, id: int) -> str:
    slug = title.lower()
    for fr, en in [('à','a'),('á','a'),('â','a'),('é','e'),('è','e'),('ê','e'),
                   ('î','i'),('ï','i'),('ô','o'),('ù','u'),('û','u'),('ü','u'),('ç','c')]:
        slug = slug.replace(fr, en)
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    return f"{slug[:80]}-{id}"


# --- Schemas ---

class SourceIn(BaseModel):
    source_type: SourceType
    title: str
    url: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    reliability_score: float = 5.0


class FactActorIn(BaseModel):
    entity_id: int
    role: ActorRole
    note: Optional[str] = None


class FactCreate(BaseModel):
    title: str
    fact_type: FactType
    official_version: Optional[str] = None
    real_version: Optional[str] = None
    context: Optional[str] = None
    event_date: Optional[str] = None
    event_date_end: Optional[str] = None
    is_historical: bool = False
    republic_period: Optional[str] = None
    location: Optional[str] = None
    region_code: Optional[str] = None
    sector_codes: Optional[str] = None
    gravity_score: float = 0.0
    suspicion_score: float = 0.0
    opacity_score: float = 0.0
    is_sensitive: bool = False
    actors: List[FactActorIn] = []
    sources: List[SourceIn] = []


class FactUpdate(BaseModel):
    title: Optional[str] = None
    fact_type: Optional[FactType] = None
    official_version: Optional[str] = None
    real_version: Optional[str] = None
    context: Optional[str] = None
    event_date: Optional[str] = None
    event_date_end: Optional[str] = None
    is_historical: Optional[bool] = None
    republic_period: Optional[str] = None
    location: Optional[str] = None
    region_code: Optional[str] = None
    sector_codes: Optional[str] = None
    gravity_score: Optional[float] = None
    suspicion_score: Optional[float] = None
    opacity_score: Optional[float] = None
    is_sensitive: Optional[bool] = None


class VerifyFactIn(BaseModel):
    status: VerificationStatus
    note: Optional[str] = None


def serialize_fact(fact: Fact, include_actors: bool = True, include_sources: bool = True) -> dict:
    d = {
        "id": fact.id,
        "title": fact.title,
        "slug": fact.slug,
        "fact_type": fact.fact_type,
        "official_version": fact.official_version,
        "real_version": fact.real_version,
        "context": fact.context,
        "event_date": fact.event_date,
        "event_date_end": fact.event_date_end,
        "is_historical": fact.is_historical,
        "republic_period": fact.republic_period,
        "location": fact.location,
        "region_code": fact.region_code,
        "sector_codes": fact.sector_codes,
        "gravity_score": fact.gravity_score,
        "suspicion_score": fact.suspicion_score,
        "opacity_score": fact.opacity_score,
        "is_sensitive": fact.is_sensitive,
        "is_published": fact.is_published,
        "verification_status": fact.verification_status,
        "verified_at": fact.verified_at,
        "verification_note": fact.verification_note,
        "created_at": fact.created_at,
        "submitted_by": fact.submitted_by,
    }
    # Sources : seulement si demandées (évite le lazy-loading sur les listes)
    if include_sources:
        d["sources"] = [
            {
                "id": s.id,
                "source_type": s.source_type,
                "title": s.title,
                "url": s.url,
                "description": s.description,
                "date": s.date,
                "reliability_score": s.reliability_score,
                "is_verified": s.is_verified,
            }
            for s in fact.sources
        ]
    if include_actors:
        d["actors"] = [
            {
                "id": fa.id,
                "role": fa.role,
                "note": fa.note,
                "entity": {
                    "id": fa.entity.id,
                    "name": fa.entity.name,
                    "slug": fa.entity.slug,
                    "entity_type": fa.entity.entity_type,
                    "suspicion_score": fa.entity.suspicion_score,
                    "photo_url": fa.entity.photo_url,
                }
            }
            for fa in fact.fact_actors
        ]
    return d


# --- Endpoints publics ---

@router.get("/")
async def list_facts(
    search: Optional[str] = None,
    fact_type: Optional[str] = None,
    sector: Optional[str] = None,
    verification_status: Optional[str] = None,
    is_historical: Optional[bool] = None,
    entity_id: Optional[int] = None,
    min_gravity: Optional[float] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    from app.services.cache import cache

    # Cache uniquement pour les requêtes sans filtre (page d'accueil / premier chargement)
    use_cache = not any([search, fact_type, sector, verification_status,
                         is_historical is not None, entity_id, min_gravity, skip])
    if use_cache:
        cached = await cache.get("facts:list")
        if cached:
            return cached

    query = db.query(Fact).filter(Fact.is_published == True)

    if search:
        query = query.filter(
            or_(Fact.title.ilike(f"%{search}%"), Fact.official_version.ilike(f"%{search}%"))
        )
    if fact_type:
        query = query.filter(Fact.fact_type == fact_type)
    if sector:
        query = query.filter(Fact.sector_codes.ilike(f"%{sector}%"))
    if verification_status:
        query = query.filter(Fact.verification_status == verification_status)
    if is_historical is not None:
        query = query.filter(Fact.is_historical == is_historical)
    if min_gravity is not None:
        query = query.filter(Fact.gravity_score >= min_gravity)
    if entity_id:
        from sqlalchemy import exists
        query = query.filter(
            exists().where((FactActor.fact_id == Fact.id) & (FactActor.entity_id == entity_id))
        )

    total = query.count() if skip == 0 else None
    facts = query.order_by(Fact.event_date.desc()).offset(skip).limit(limit).all()

    result = {
        "total": total,
        "items": [serialize_fact(f, include_actors=False, include_sources=False) for f in facts],
    }
    if use_cache:
        await cache.set("facts:list", result)
    return result


@router.get("/pending")
def list_pending_facts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    """Faits soumis en attente de validation (moderator+)"""
    facts = (
        db.query(Fact)
        .filter(Fact.is_published == False)
        .order_by(Fact.created_at.desc())
        .all()
    )
    return [serialize_fact(f, include_actors=False, include_sources=False) for f in facts]


@router.get("/my/submitted")
def my_submitted_facts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Faits soumis par l'utilisateur connecté (ambassador, etc.)"""
    facts = (
        db.query(Fact)
        .filter(Fact.submitted_by == current_user.id)
        .order_by(Fact.created_at.desc())
        .all()
    )
    return [serialize_fact(f, include_actors=False, include_sources=False) for f in facts]


@router.get("/{slug}")
def get_fact(slug: str, db: Session = Depends(get_db),
             current_user: Optional[User] = Depends(get_optional_user)):
    fact = (
        db.query(Fact)
        .filter(Fact.slug == slug)
        .options(
            selectinload(Fact.sources),
            selectinload(Fact.fact_actors).joinedload(FactActor.entity),
        )
        .first()
    )
    if not fact:
        raise HTTPException(status_code=404, detail="Fait introuvable")
    if not fact.is_published and not is_staff(current_user):
        raise HTTPException(status_code=403, detail="Non disponible")

    # Threads liés
    thread_facts = db.query(ThreadFact).filter(ThreadFact.fact_id == fact.id).all()
    threads = []
    for tf in thread_facts:
        t = tf.thread
        if t.is_published or is_staff(current_user):
            threads.append({
                "id": t.id,
                "title": t.title,
                "slug": t.slug,
                "category": t.category,
                "gravity_score": t.gravity_score,
            })

    result = serialize_fact(fact)
    result["threads"] = threads
    return result


# --- Création / Soumission ---

require_ambassador_or_above = require_role(
    UserRole.z_ambassador, UserRole.moderator, UserRole.admin
)

@router.post("/")
def create_fact(
    data: FactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ambassador_or_above)
):
    # Z-Ambassador : soumission en pending (non publié)
    # Moderator / Admin : publié directement
    is_moderator = is_staff(current_user)

    fact = Fact(
        title=data.title,
        fact_type=data.fact_type,
        official_version=data.official_version,
        real_version=data.real_version,
        context=data.context,
        event_date=data.event_date,
        event_date_end=data.event_date_end,
        is_historical=data.is_historical,
        republic_period=data.republic_period,
        location=data.location,
        region_code=data.region_code,
        sector_codes=data.sector_codes,
        gravity_score=data.gravity_score,
        suspicion_score=data.suspicion_score,
        opacity_score=data.opacity_score,
        is_sensitive=data.is_sensitive,
        is_published=is_moderator,
        verification_status=VerificationStatus.unverified,
        submitted_by=current_user.id,
    )
    db.add(fact)
    db.flush()
    fact.slug = make_slug(fact.title, fact.id)

    # Acteurs
    for actor_in in data.actors:
        entity = db.query(Entity).filter(Entity.id == actor_in.entity_id).first()
        if entity:
            db.add(FactActor(fact_id=fact.id, entity_id=entity.id,
                             role=actor_in.role, note=actor_in.note))

    # Sources
    for src in data.sources:
        db.add(FactSource(fact_id=fact.id, **src.model_dump()))

    db.commit()
    db.refresh(fact)
    return {
        "id": fact.id,
        "slug": fact.slug,
        "is_published": fact.is_published,
        "message": "Fait publié" if is_moderator else "Fait soumis — en attente de validation"
    }


@router.patch("/{fact_id}")
async def update_fact(
    fact_id: int,
    data: FactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    from app.services.cache import cache
    fact = db.query(Fact).filter(Fact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fait introuvable")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(fact, field, value)

    db.commit()
    db.refresh(fact)
    await cache.invalidate("facts:list")
    return serialize_fact(fact)


@router.patch("/{fact_id}/verify")
async def verify_fact(
    fact_id: int,
    data: VerifyFactIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    """Changer le statut de vérification d'un fait"""
    from app.services.cache import cache
    fact = db.query(Fact).filter(Fact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fait introuvable")

    fact.verification_status = data.status
    fact.verification_note = data.note
    fact.verified_by = current_user.id
    fact.verified_at = datetime.utcnow()

    # Publier automatiquement si vérifié
    if data.status == VerificationStatus.verified:
        fact.is_published = True

    db.commit()

    # Invalider le cache des faits et stats publiques
    await cache.invalidate("facts:list")
    await cache.invalidate("public:stats")

    return {
        "id": fact.id,
        "verification_status": fact.verification_status,
        "is_published": fact.is_published,
        "message": f"Statut mis à jour : {data.status}"
    }


@router.post("/{fact_id}/sources")
def add_source(
    fact_id: int,
    data: SourceIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fact = db.query(Fact).filter(Fact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fait introuvable")

    source = FactSource(fact_id=fact_id, **data.model_dump())
    db.add(source)
    db.commit()
    return {"message": "Source ajoutée"}


@router.post("/{fact_id}/actors")
def add_actor(
    fact_id: int,
    data: FactActorIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    fact = db.query(Fact).filter(Fact.id == fact_id).first()
    entity = db.query(Entity).filter(Entity.id == data.entity_id).first()
    if not fact or not entity:
        raise HTTPException(status_code=404, detail="Fait ou entité introuvable")

    actor = FactActor(fact_id=fact_id, entity_id=data.entity_id,
                      role=data.role, note=data.note)
    db.add(actor)
    db.commit()
    return {"message": "Acteur ajouté"}


@router.delete("/{fact_id}")
async def delete_fact(
    fact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    """Supprimer définitivement un fait (modérateur+)"""
    from app.services.cache import cache
    fact = db.query(Fact).filter(Fact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fait introuvable")
    db.query(FactActor).filter(FactActor.fact_id == fact_id).delete()
    db.query(FactSource).filter(FactSource.fact_id == fact_id).delete()
    db.query(ThreadFact).filter(ThreadFact.fact_id == fact_id).delete()
    db.delete(fact)
    db.commit()
    await cache.invalidate("facts:list")
    await cache.invalidate("public:stats")
    return {"message": "Fait supprimé"}
