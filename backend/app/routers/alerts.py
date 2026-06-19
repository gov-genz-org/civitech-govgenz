from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from app.models.user import User
from app.services.auth import get_current_user, require_moderator, is_privileged

router = APIRouter(prefix="/alerts", tags=["Alertes"])


SENSITIVE_TYPES = {AlertType.power_abuse, AlertType.corruption, AlertType.violence}


class AlertCreate(BaseModel):
    title: str
    description: str
    alert_type: AlertType
    severity: AlertSeverity = AlertSeverity.medium
    sector_main: str
    sectors_related: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    commune: Optional[str] = None
    fokontany: Optional[str] = None
    location_details: Optional[str] = None
    sources: Optional[str] = None
    images: Optional[str] = None       # JSON list d'URLs images
    proof_urls: Optional[str] = None   # JSON list d'URLs documents
    # Admin-only fields (ignorés pour les citoyens)
    is_sensitive: Optional[bool] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None


@router.post("/", status_code=201)
def create_alert(data: AlertCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auto_sensitive = data.alert_type in SENSITIVE_TYPES or data.severity == AlertSeverity.critical
    privileged = is_privileged(current_user)

    # Admins/modérateurs peuvent publier directement
    status  = AlertStatus(data.status) if privileged and data.status else AlertStatus.pending
    is_pub  = data.is_public if privileged and data.is_public is not None else False
    is_sens = data.is_sensitive if privileged and data.is_sensitive is not None else auto_sensitive

    alert = Alert(
        title=data.title,
        description=data.description,
        alert_type=data.alert_type,
        severity=data.severity,
        sector_main=data.sector_main,
        sectors_related=data.sectors_related,
        region=data.region or current_user.region,
        district=data.district or current_user.district,
        city=data.city or current_user.city,
        commune=data.commune,
        fokontany=data.fokontany,
        location_details=data.location_details,
        sources=data.sources,
        images=data.images,
        proof_urls=data.proof_urls,
        author_id=current_user.id,
        is_sensitive=is_sens,
        is_public=is_pub,
        status=status,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    if privileged and status == AlertStatus.published:
        return {"message": "Alerte publiée", "id": alert.id}
    return {"message": "Alerte soumise et en attente de validation", "id": alert.id}


@router.get("/my-alerts")
def my_alerts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alerts = db.query(Alert).filter(Alert.author_id == current_user.id).order_by(Alert.created_at.desc()).all()
    return alerts


@router.get("/", dependencies=[Depends(require_moderator)])
def list_all_alerts(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    return query.order_by(Alert.created_at.desc()).all()


@router.patch("/{alert_id}/review", dependencies=[Depends(require_moderator)])
async def review_alert(
    alert_id: int,
    new_status: AlertStatus,
    is_public: bool = False,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from datetime import datetime
    from app.services.cache import cache
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")

    if alert.is_sensitive and not is_privileged(current_user):
        raise HTTPException(status_code=403, detail="Alerte sensible — validation admin requise")

    alert.status = new_status
    alert.is_public = is_public
    alert.reviewed_by = current_user.id
    alert.reviewed_at = datetime.utcnow()
    if notes:
        alert.review_notes = notes

    db.commit()
    await cache.invalidate("public:alerts")
    await cache.invalidate("public:stats")
    return {"message": f"Alerte mise à jour: {new_status}"}


@router.delete("/{alert_id}", dependencies=[Depends(require_moderator)])
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer définitivement une alerte (modérateur+)"""
    from app.services.cache import cache
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    if alert.is_sensitive and not is_privileged(current_user):
        raise HTTPException(status_code=403, detail="Alerte sensible — suppression admin requise")
    db.delete(alert)
    db.commit()
    await cache.invalidate("public:alerts")
    await cache.invalidate("public:stats")
    return {"message": "Alerte supprimée"}
