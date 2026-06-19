from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import re

from app.database import get_db
from app.models.fact import Thread, ThreadFact, Fact, VerificationStatus
from app.services.auth import get_current_user, get_optional_user, require_role, is_staff
from app.models.user import User, UserRole

router = APIRouter(prefix="/threads", tags=["threads"])


def make_slug(title: str, id: int) -> str:
    slug = title.lower()
    for fr, en in [('à','a'),('é','e'),('è','e'),('ê','e'),('î','i'),
                   ('ô','o'),('ù','u'),('û','u'),('ç','c')]:
        slug = slug.replace(fr, en)
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    return f"{slug[:80]}-{id}"


class ThreadCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    sector_codes: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_ongoing: bool = True


class ThreadUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    sector_codes: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_ongoing: Optional[bool] = None
    gravity_score: Optional[float] = None
    suspicion_score: Optional[float] = None
    is_published: Optional[bool] = None


class AddFactToThread(BaseModel):
    fact_id: int
    position: Optional[int] = None
    link_note: Optional[str] = None


def serialize_thread(thread: Thread, include_facts: bool = True) -> dict:
    d = {
        "id": thread.id,
        "title": thread.title,
        "slug": thread.slug,
        "description": thread.description,
        "category": thread.category,
        "sector_codes": thread.sector_codes,
        "start_date": thread.start_date,
        "end_date": thread.end_date,
        "is_ongoing": thread.is_ongoing,
        "gravity_score": thread.gravity_score,
        "suspicion_score": thread.suspicion_score,
        "is_published": thread.is_published,
        "verification_status": thread.verification_status,
        "created_at": thread.created_at,
        "facts_count": len(thread.thread_facts),
    }
    if include_facts:
        d["facts"] = [
            {
                "position": tf.position,
                "link_note": tf.link_note,
                "fact": {
                    "id": tf.fact.id,
                    "title": tf.fact.title,
                    "slug": tf.fact.slug,
                    "fact_type": tf.fact.fact_type,
                    "event_date": tf.fact.event_date,
                    "gravity_score": tf.fact.gravity_score,
                    "suspicion_score": tf.fact.suspicion_score,
                    "opacity_score": tf.fact.opacity_score,
                    "verification_status": tf.fact.verification_status,
                    "sector_codes": tf.fact.sector_codes,
                    "location": tf.fact.location,
                    "official_version": tf.fact.official_version,
                    "real_version": tf.fact.real_version,
                    "is_sensitive": tf.fact.is_sensitive,
                    "actors": [
                        {
                            "role": fa.role,
                            "entity_name": fa.entity.name,
                            "entity_slug": fa.entity.slug,
                            "entity_type": fa.entity.entity_type,
                        }
                        for fa in tf.fact.fact_actors
                    ],
                }
            }
            for tf in thread.thread_facts
        ]
    return d


# --- Endpoints publics ---

@router.get("/")
async def list_threads(
    search: Optional[str] = None,
    category: Optional[str] = None,
    sector: Optional[str] = None,
    is_ongoing: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    from app.services.cache import cache

    use_cache = not any([search, category, sector, is_ongoing is not None, skip])
    if use_cache:
        cached = await cache.get("threads:list")
        if cached:
            return cached

    query = db.query(Thread).filter(Thread.is_published == True)

    if search:
        query = query.filter(Thread.title.ilike(f"%{search}%"))
    if category:
        query = query.filter(Thread.category == category)
    if sector:
        query = query.filter(Thread.sector_codes.ilike(f"%{sector}%"))
    if is_ongoing is not None:
        query = query.filter(Thread.is_ongoing == is_ongoing)

    from sqlalchemy import func
    total = query.count()
    threads = query.order_by(Thread.gravity_score.desc()).offset(skip).limit(limit).all()

    if not threads:
        return {"total": total, "items": []}

    # facts_count via 1 agrégation au lieu de N lazy-loads
    t_ids = [t.id for t in threads]
    facts_counts = dict(
        db.query(ThreadFact.thread_id, func.count(ThreadFact.id))
        .filter(ThreadFact.thread_id.in_(t_ids))
        .group_by(ThreadFact.thread_id)
        .all()
    )

    items = []
    for t in threads:
        d = {
            "id": t.id, "title": t.title, "slug": t.slug,
            "description": t.description, "category": t.category,
            "sector_codes": t.sector_codes, "start_date": t.start_date,
            "end_date": t.end_date, "is_ongoing": t.is_ongoing,
            "gravity_score": t.gravity_score, "suspicion_score": t.suspicion_score,
            "is_published": t.is_published, "verification_status": t.verification_status,
            "created_at": t.created_at,
            "facts_count": facts_counts.get(t.id, 0),
        }
        items.append(d)

    result = {"total": total, "items": items}
    if use_cache:
        await cache.set("threads:list", result)
    return result


@router.get("/{slug}")
def get_thread(slug: str, db: Session = Depends(get_db),
               current_user: Optional[User] = Depends(get_optional_user)):
    thread = db.query(Thread).filter(Thread.slug == slug).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread introuvable")
    if not thread.is_published and not is_staff(current_user):
        raise HTTPException(status_code=403, detail="Non disponible")

    return serialize_thread(thread)


# --- Endpoints admin / modérateur ---

@router.post("/")
def create_thread(
    data: ThreadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    thread = Thread(
        **data.model_dump(),
        verification_status=VerificationStatus.unverified,
        created_by=current_user.id,
    )
    db.add(thread)
    db.flush()
    thread.slug = make_slug(thread.title, thread.id)
    db.commit()
    db.refresh(thread)
    return {"id": thread.id, "slug": thread.slug, "message": "Thread créé"}


@router.patch("/{thread_id}")
async def update_thread(
    thread_id: int,
    data: ThreadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    from app.services.cache import cache
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread introuvable")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(thread, field, value)

    # Recalculer les scores moyens depuis les faits liés
    if thread.thread_facts:
        published_facts = [tf.fact for tf in thread.thread_facts if tf.fact.is_published]
        if published_facts:
            thread.gravity_score = sum(f.gravity_score for f in published_facts) / len(published_facts)
            thread.suspicion_score = sum(f.suspicion_score for f in published_facts) / len(published_facts)

    db.commit()
    db.refresh(thread)
    await cache.invalidate("threads:list")
    return serialize_thread(thread, include_facts=False)


@router.post("/{thread_id}/facts")
def add_fact_to_thread(
    thread_id: int,
    data: AddFactToThread,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    fact = db.query(Fact).filter(Fact.id == data.fact_id).first()
    if not thread or not fact:
        raise HTTPException(status_code=404, detail="Thread ou fait introuvable")

    # Vérifier qu'il n'est pas déjà dans le thread
    existing = db.query(ThreadFact).filter(
        ThreadFact.thread_id == thread_id,
        ThreadFact.fact_id == data.fact_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ce fait est déjà dans ce thread")

    # Position auto si non fournie
    position = data.position
    if position is None:
        count = db.query(ThreadFact).filter(ThreadFact.thread_id == thread_id).count()
        position = count

    tf = ThreadFact(
        thread_id=thread_id,
        fact_id=data.fact_id,
        position=position,
        link_note=data.link_note
    )
    db.add(tf)

    # Recalcul des scores du thread
    all_tfs = db.query(ThreadFact).filter(ThreadFact.thread_id == thread_id).all()
    all_facts = [t.fact for t in all_tfs] + [fact]
    published = [f for f in all_facts if f.is_published]
    if published:
        thread.gravity_score = sum(f.gravity_score for f in published) / len(published)
        thread.suspicion_score = sum(f.suspicion_score for f in published) / len(published)

    db.commit()
    return {"message": "Fait ajouté au thread", "position": position}


@router.delete("/{thread_id}/facts/{fact_id}")
def remove_fact_from_thread(
    thread_id: int,
    fact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    tf = db.query(ThreadFact).filter(
        ThreadFact.thread_id == thread_id,
        ThreadFact.fact_id == fact_id
    ).first()
    if not tf:
        raise HTTPException(status_code=404, detail="Association introuvable")
    db.delete(tf)
    db.commit()
    return {"message": "Fait retiré du thread"}


@router.get("/pending/list")
def list_pending_threads(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    threads = db.query(Thread).filter(Thread.is_published == False).all()
    return [serialize_thread(t, include_facts=False) for t in threads]


@router.delete("/{thread_id}")
async def delete_thread(
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.moderator, UserRole.admin))
):
    """Supprimer définitivement un thread (modérateur+)"""
    from app.services.cache import cache
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread introuvable")
    db.query(ThreadFact).filter(ThreadFact.thread_id == thread_id).delete()
    db.delete(thread)
    db.commit()
    await cache.invalidate("threads:list")
    return {"message": "Thread supprimé"}
