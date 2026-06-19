from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User, UserRole
from app.models.ambassador import Ambassador, AmbassadorStatus
from app.models.consultation import Consultation, ConsultationStatus
from app.models.alert import Alert, AlertStatus
from app.models.sector import Sector
from app.services.cache import cache

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/stats")
async def get_public_stats(db: Session = Depends(get_db)):
    # Cache 5 minutes — stats changent peu
    cached = await cache.get("public:stats")
    if cached:
        return cached

    result = {
        "citizens":             db.query(User).filter(User.role == UserRole.z_citizen, User.is_active == True).count(),
        "ambassadors":          db.query(Ambassador).filter(Ambassador.status == AmbassadorStatus.active).count(),
        "active_consultations": db.query(Consultation).filter(Consultation.status == ConsultationStatus.active).count(),
        "published_alerts":     db.query(Alert).filter(Alert.status == AlertStatus.published, Alert.is_public == True).count(),
    }
    await cache.set("public:stats", result)
    return result


@router.get("/consultations")
async def list_public_consultations(db: Session = Depends(get_db)):
    cached = await cache.get("public:consultations")
    if cached:
        return cached

    consultations = db.query(Consultation).filter(
        Consultation.status == ConsultationStatus.active,
        Consultation.is_public == True
    ).order_by(Consultation.created_at.desc()).limit(20).all()

    result = [
        {
            "id": c.id, "title": c.title, "description": c.description,
            "scope": c.scope, "sector_main": c.sector_main,
            "starts_at": c.starts_at, "ends_at": c.ends_at,
        }
        for c in consultations
    ]
    await cache.set("public:consultations", result)
    return result


@router.get("/alerts")
async def list_public_alerts(db: Session = Depends(get_db)):
    cached = await cache.get("public:alerts")
    if cached:
        return cached

    alerts = db.query(Alert).filter(
        Alert.status == AlertStatus.published,
        Alert.is_public == True
    ).order_by(Alert.created_at.desc()).limit(20).all()

    result = [
        {
            "id": a.id, "title": a.title, "description": a.description,
            "alert_type": a.alert_type, "severity": a.severity,
            "sector_main": a.sector_main, "region": a.region,
            "city": a.city, "created_at": a.created_at,
            "images": a.images,
        }
        for a in alerts
    ]
    await cache.set("public:alerts", result)
    return result


@router.get("/sectors")
async def list_sectors(db: Session = Depends(get_db)):
    cached = await cache.get("sectors:list")
    if cached:
        return cached

    result = [{"id": s.id, "code": s.code, "label": s.label} for s in db.query(Sector).all()]
    await cache.set("sectors:list", result)
    return result


@router.get("/verify-ambassador/{code}")
def verify_ambassador(code: str, db: Session = Depends(get_db)):
    ambassador = db.query(Ambassador).filter(
        Ambassador.verify_code == code,
        Ambassador.status == AmbassadorStatus.active
    ).first()

    if not ambassador:
        return {
            "verified": False,
            "message": "Aucun Z-Ambassador actif trouvé avec ce code."
        }

    user = db.query(User).filter(User.id == ambassador.user_id).first()

    return {
        "verified": True,
        "public_name": ambassador.public_name,
        "ambassador_type": ambassador.ambassador_type,
        "zone_action": ambassador.zone_action,
        "valid_from": ambassador.valid_from,
        "valid_until": ambassador.valid_until,
        "message": "✓ Ce Z-Ambassador est officiellement autorisé par GoV Gen Z Madagascar."
    }
