import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.ambassador import Ambassador, AmbassadorStatus, AmbassadorType
from app.models.user import User, UserRole
from app.services.auth import get_current_user, require_moderator

router = APIRouter(prefix="/ambassadors", tags=["Ambassadors"])


class AmbassadorApplyRequest(BaseModel):
    ambassador_type: AmbassadorType = AmbassadorType.individual
    public_name: str
    bio: Optional[str] = None
    zone_action: str
    sectors_interest: Optional[str] = None
    objectives: Optional[str] = None
    mobilization_capacity: int = 0
    motivation: str
    experience: Optional[str] = None
    charter_signed: bool = False


@router.post("/apply", status_code=201)
def apply(data: AmbassadorApplyRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not data.charter_signed:
        raise HTTPException(status_code=400, detail="Vous devez signer la charte Z-Ambassador")

    existing = db.query(Ambassador).filter(Ambassador.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Candidature déjà soumise")

    code = secrets.token_urlsafe(16)
    ambassador = Ambassador(
        user_id=current_user.id,
        ambassador_type=data.ambassador_type,
        public_name=data.public_name,
        bio=data.bio,
        zone_action=data.zone_action,
        sectors_interest=data.sectors_interest,
        objectives=data.objectives,
        mobilization_capacity=data.mobilization_capacity,
        motivation=data.motivation,
        experience=data.experience,
        charter_signed=True,
        charter_signed_at=datetime.utcnow(),
        verify_code=code,
        status=AmbassadorStatus.candidate,
    )
    db.add(ambassador)
    db.commit()
    db.refresh(ambassador)
    return {"message": "Candidature soumise avec succès", "ambassador_id": ambassador.id}


@router.get("/my-profile")
def my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ambassador = db.query(Ambassador).filter(Ambassador.user_id == current_user.id).first()
    if not ambassador:
        raise HTTPException(status_code=404, detail="Profil Z-Ambassador non trouvé")
    return ambassador


@router.get("/", dependencies=[Depends(require_moderator)])
def list_ambassadors(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Ambassador)
    if status:
        query = query.filter(Ambassador.status == status)
    ambassadors = query.order_by(Ambassador.created_at.desc()).all()

    result = []
    for a in ambassadors:
        user = db.query(User).filter(User.id == a.user_id).first()
        result.append({
            "id": a.id,
            "user_id": a.user_id,
            "status": a.status,
            "ambassador_type": a.ambassador_type,
            "public_name": a.public_name,
            "bio": a.bio,
            "zone_action": a.zone_action,
            "sectors_interest": a.sectors_interest,
            "objectives": a.objectives,
            "mobilization_capacity": a.mobilization_capacity,
            "motivation": a.motivation,
            "experience": a.experience,
            "verify_code": a.verify_code,
            "total_responses_collected": a.total_responses_collected,
            "valid_responses": a.valid_responses,
            "trust_score": a.trust_score,
            "review_notes": a.review_notes,
            "valid_from": a.valid_from,
            "created_at": a.created_at,
            # Données utilisateur enrichies
            "user_pseudo": user.pseudo if user else None,
            "user_full_name": user.full_name if user else None,
            "user_email": user.email if user else None,
            "user_avatar": user.avatar_url if user else None,
            "user_region": user.region if user else a.zone_action,
            "user_city": user.city if user else None,
        })
    return result


@router.patch("/{ambassador_id}/status", dependencies=[Depends(require_moderator)])
def update_status(
    ambassador_id: int,
    new_status: AmbassadorStatus,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ambassador = db.query(Ambassador).filter(Ambassador.id == ambassador_id).first()
    if not ambassador:
        raise HTTPException(status_code=404, detail="Ambassador non trouvé")

    ambassador.status = new_status
    ambassador.reviewed_by = current_user.id
    ambassador.reviewed_at = datetime.utcnow()
    if notes:
        ambassador.review_notes = notes
    if new_status == AmbassadorStatus.active:
        ambassador.valid_from = datetime.utcnow()
        user = db.query(User).filter(User.id == ambassador.user_id).first()
        if user:
            user.role = UserRole.z_ambassador

    db.commit()
    return {"message": f"Statut mis à jour: {new_status}"}
