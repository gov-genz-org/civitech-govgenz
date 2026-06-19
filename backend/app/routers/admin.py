from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from app.database import get_db
from app.models.user import User, UserRole, VerificationStatus
from app.models.ambassador import Ambassador, AmbassadorStatus
from app.models.consultation import Consultation, Response
from app.models.alert import Alert, AlertStatus
from app.models.audit import AuditLog
from app.services.auth import get_current_user, require_admin, require_moderator, require_ambassador, is_privileged

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hiérarchie : qui peut créer quel rôle
ROLE_HIERARCHY = {
    UserRole.superadmin:   [UserRole.admin, UserRole.moderator, UserRole.z_ambassador, UserRole.z_citizen],
    UserRole.admin:        [UserRole.moderator, UserRole.z_ambassador, UserRole.z_citizen],
    UserRole.moderator:    [UserRole.z_ambassador, UserRole.z_citizen],
    UserRole.z_ambassador: [UserRole.z_citizen],
    UserRole.z_citizen:    [],
}

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard", dependencies=[Depends(require_moderator)])
def admin_dashboard(db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    total_citizens = db.query(User).filter(User.role == UserRole.z_citizen).count()
    total_ambassadors = db.query(Ambassador).filter(Ambassador.status == AmbassadorStatus.active).count()
    pending_ambassadors = db.query(Ambassador).filter(Ambassador.status == AmbassadorStatus.candidate).count()
    pending_alerts = db.query(Alert).filter(Alert.status == AlertStatus.pending).count()
    critical_alerts = db.query(Alert).filter(Alert.severity == "critical").count()

    # Alertes par secteur
    alerts_by_sector = (
        db.query(Alert.sector_main, func.count(Alert.id).label("count"))
        .group_by(Alert.sector_main)
        .all()
    )

    # Alertes par région
    alerts_by_region = (
        db.query(Alert.region, func.count(Alert.id).label("count"))
        .filter(Alert.region.isnot(None))
        .group_by(Alert.region)
        .order_by(func.count(Alert.id).desc())
        .limit(10)
        .all()
    )

    return {
        "users": {
            "total": total_users,
            "citizens": total_citizens,
            "ambassadors": total_ambassadors,
            "pending_ambassadors": pending_ambassadors,
        },
        "alerts": {
            "pending": pending_alerts,
            "critical": critical_alerts,
            "by_sector": [{"sector": r[0], "count": r[1]} for r in alerts_by_sector],
            "by_region": [{"region": r[0], "count": r[1]} for r in alerts_by_region],
        },
    }


@router.get("/users", dependencies=[Depends(require_moderator)])
def list_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    include_inactive: bool = False,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(User)
    # Le superadmin est invisible pour les non-superadmins
    if current_user.role != UserRole.superadmin:
        query = query.filter(User.role != UserRole.superadmin)
    if role:
        query = query.filter(User.role == role)
    if not include_inactive:
        query = query.filter(User.is_active == True)
    if search:
        query = query.filter(
            (User.pseudo.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )
    return query.order_by(User.created_at.desc()).limit(limit).all()


@router.get("/users/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_moderator_or_above(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    base = {
        "id": user.id, "email": user.email, "pseudo": user.pseudo,
        "role": user.role, "is_active": user.is_active,
        "verification_status": user.verification_status,
        "trust_score": user.trust_score,
        "avatar_url": user.avatar_url,
        "full_name": user.full_name,
        "created_at": user.created_at, "last_login": user.last_login,
    }

    # Superadmin et admin voient TOUT
    if current_user.role in (UserRole.superadmin, UserRole.admin):
        base.update({
            "whatsapp": user.whatsapp,
            "country": user.country, "region": user.region,
            "city": user.city, "district": user.district,
            "commune": user.commune, "fokontany": user.fokontany,
            "profession": user.profession, "age_range": user.age_range,
            "socio_category": user.socio_category,
            "priorities": user.priorities,
            "contribution_offer": user.contribution_offer,
            "injustice_experienced": user.injustice_experienced,
            "wish_for_madagascar": user.wish_for_madagascar,
            "social_links": user.social_links,
            "invited_by": user.invited_by,
            "updated_at": user.updated_at,
        })

    return base


def _check_moderator_or_above(user: User):
    from app.models.user import UserRole
    if user.role not in (UserRole.moderator, UserRole.admin, UserRole.superadmin):
        raise HTTPException(status_code=403, detail="Accès refusé")


class UserUpdate(BaseModel):
    role: Optional[UserRole] = None
    verification_status: Optional[VerificationStatus] = None
    trust_score: Optional[float] = None
    is_active: Optional[bool] = None


@router.patch("/users/{user_id}", dependencies=[Depends(require_admin)])
def update_user(user_id: int, data: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    # Personne ne peut modifier le superadmin (sauf lui-même)
    if user.role == UserRole.superadmin and current_user.role != UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Ce compte est protégé.")

    # Seul le superadmin peut affecter le rôle superadmin
    if data.role == UserRole.superadmin and current_user.role != UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Attribution du rôle superadmin non autorisée.")

    if data.role is not None:
        user.role = data.role
    if data.verification_status is not None:
        user.verification_status = data.verification_status
    if data.trust_score is not None:
        user.trust_score = max(0.0, min(100.0, data.trust_score))
    if data.is_active is not None:
        user.is_active = data.is_active

    log = AuditLog(
        user_id=current_user.id,
        action="update_user",
        resource_type="user",
        resource_id=user_id,
        details=str(data.dict(exclude_none=True))
    )
    db.add(log)
    db.commit()
    return {"message": "Utilisateur mis à jour"}


@router.get("/audit-logs", dependencies=[Depends(require_admin)])
def audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    # 1 seule query avec LEFT JOIN au lieu de N+1
    from sqlalchemy import alias
    ActorUser = alias(User.__table__, name="actor")
    rows = (
        db.query(
            AuditLog,
            User.pseudo.label("actor_pseudo"),
            User.role.label("actor_role"),
        )
        .outerjoin(User, User.id == AuditLog.user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at,
            "actor_id": log.user_id,
            "actor_pseudo": pseudo,
            "actor_role": role,
        }
        for log, pseudo, role in rows
    ]


class UserCreate(BaseModel):
    email: str
    pseudo: str
    password: Optional[str] = None  # Optionnel — magic link only
    role: UserRole = UserRole.z_citizen
    full_name: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None


@router.post("/users", dependencies=[Depends(require_ambassador)])
def create_user(data: UserCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Création d'un utilisateur par un admin/modérateur/ambassador (selon hiérarchie)."""
    import secrets as _secrets
    allowed = ROLE_HIERARCHY.get(current_user.role, [])
    if data.role not in allowed:
        raise HTTPException(status_code=403, detail=f"Vous ne pouvez pas créer un compte de rôle '{data.role}'.")

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé.")
    if db.query(User).filter(User.pseudo == data.pseudo).first():
        raise HTTPException(status_code=400, detail="Pseudo déjà utilisé.")

    pw_hash = pwd_context.hash(data.password) if data.password else pwd_context.hash(_secrets.token_hex(32))

    new_user = User(
        email=data.email,
        pseudo=data.pseudo,
        hashed_password=pw_hash,
        role=data.role,
        full_name=data.full_name,
        region=data.region,
        city=data.city,
        invited_by=current_user.id,
        verification_status=VerificationStatus.verified,
        is_active=True,
    )
    db.add(new_user)
    db.flush()

    log = AuditLog(
        user_id=current_user.id,
        action="create_user",
        resource_type="user",
        resource_id=new_user.id,
        details=f"role={data.role} email={data.email} pseudo={data.pseudo}",
    )
    db.add(log)
    db.commit()
    return {"message": "Utilisateur créé", "id": new_user.id}


@router.delete("/users/{user_id}", dependencies=[Depends(require_moderator)])
def delete_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Désactivation d'un utilisateur (soft delete). Seul un admin peut supprimer un modérateur."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas vous supprimer vous-même.")

    # Le superadmin est indestructible
    if user.role == UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Ce compte est protégé.")

    # Un modérateur ne peut pas supprimer un modérateur ou admin
    # Un admin ne peut pas supprimer un autre admin (seul le superadmin peut)
    if current_user.role == UserRole.moderator and user.role in [UserRole.moderator, UserRole.admin]:
        raise HTTPException(status_code=403, detail="Droits insuffisants pour supprimer ce profil.")
    if current_user.role == UserRole.admin and user.role == UserRole.admin:
        raise HTTPException(status_code=403, detail="Un admin ne peut pas supprimer un autre admin.")

    user.is_active = False
    user.verification_status = VerificationStatus.suspended

    log = AuditLog(
        user_id=current_user.id,
        action="delete_user",
        resource_type="user",
        resource_id=user_id,
        details=f"suspended pseudo={user.pseudo} role={user.role}",
    )
    db.add(log)
    db.commit()
    return {"message": f"Compte de {user.pseudo} désactivé."}


@router.get("/users/{user_id}/referred")
def get_referred_users(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Citoyens et ambassadors référés par cet utilisateur."""
    # Un ambassador peut voir ses propres référés, un admin/modérateur peut voir n'importe qui
    if current_user.role not in [UserRole.superadmin, UserRole.admin, UserRole.moderator] and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Accès refusé.")
    users = db.query(User).filter(User.invited_by == user_id).order_by(User.created_at.desc()).all()
    return [{"id": u.id, "pseudo": u.pseudo, "role": u.role, "email": u.email,
             "verification_status": u.verification_status, "is_active": u.is_active,
             "created_at": u.created_at} for u in users]
