import secrets
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.models.user import User, UserRole
from app.models.magic_token import MagicToken
from app.utils.security import hash_password, verify_password, create_access_token
from app.services.auth import get_current_user
from app.services.email import send_magic_link_email
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str | None = None   # Optionnel — magic link only
    pseudo: str
    full_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    pseudo: str | None


@router.post("/register", status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    if db.query(User).filter(User.pseudo == data.pseudo).first():
        raise HTTPException(status_code=400, detail="Pseudo déjà utilisé")
    if data.password and len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Mot de passe trop court (min 8 caractères)")

    # Si pas de mot de passe fourni (magic link only), on génère un hash inutilisable
    pw_hash = hash_password(data.password) if data.password else hash_password(secrets.token_hex(32))

    user = User(
        email=data.email,
        hashed_password=pw_hash,
        pseudo=data.pseudo,
        full_name=data.full_name,
        role=UserRole.z_citizen,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Compte créé avec succès", "user_id": user.id}


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte suspendu")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    user.last_login = datetime.utcnow()
    db.commit()

    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        pseudo=user.pseudo,
    )


class MagicLinkRequest(BaseModel):
    email: EmailStr


@router.post("/magic-link")
def request_magic_link(data: MagicLinkRequest, db: Session = Depends(get_db)):
    """
    Demande un magic link. Toujours retourner 200 pour ne pas
    révéler si l'email existe ou non (sécurité anti-enumération).
    """
    user = db.query(User).filter(User.email == data.email).first()

    if user and user.is_active:
        # Invalider les anciens tokens non utilisés de cet utilisateur
        db.query(MagicToken).filter(
            MagicToken.user_id == user.id,
            MagicToken.used == False
        ).delete()

        # Créer un nouveau token (64 octets = 128 chars hex)
        token = secrets.token_hex(64)
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        magic = MagicToken(token=token, user_id=user.id, expires_at=expires_at)
        db.add(magic)
        db.commit()

        # Construire l'URL de vérification
        magic_url = f"{settings.FRONTEND_URL}/auth/verify?token={token}"

        # Envoyer l'email (fail-safe : on ne bloque pas si l'envoi échoue)
        send_magic_link_email(
            to_email=user.email,
            magic_url=magic_url,
            pseudo=user.pseudo
        )

    return {"message": "Si cet email est enregistré, tu recevras un lien de connexion dans quelques secondes."}


@router.get("/magic-link/verify")
def verify_magic_link(token: str, db: Session = Depends(get_db)):
    """Valide le magic link et retourne un JWT."""
    magic = db.query(MagicToken).filter(MagicToken.token == token).first()

    if not magic:
        raise HTTPException(status_code=400, detail="Lien invalide ou expiré")
    if magic.used:
        raise HTTPException(status_code=400, detail="Ce lien a déjà été utilisé")
    if datetime.utcnow() > magic.expires_at:
        raise HTTPException(status_code=400, detail="Ce lien a expiré (15 min)")

    user = db.query(User).filter(User.id == magic.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Compte introuvable ou suspendu")

    # Marquer le token comme utilisé
    magic.used = True
    user.last_login = datetime.utcnow()
    db.commit()

    jwt_token = create_access_token({"sub": str(user.id), "role": user.role})

    return TokenResponse(
        access_token=jwt_token,
        role=user.role,
        user_id=user.id,
        pseudo=user.pseudo,
    )


def _serialize_me(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "pseudo": u.pseudo,
        "role": u.role,
        "verification_status": u.verification_status,
        "trust_score": u.trust_score,
        "created_at": u.created_at,
        # Identité
        "full_name": u.full_name,
        "whatsapp": u.whatsapp,
        "avatar_url": u.avatar_url,
        # Localisation
        "country": u.country,
        "region": u.region,
        "city": u.city,
        "district": u.district,
        "commune": u.commune,
        "fokontany": u.fokontany,
        # Démographie
        "age_range": u.age_range,
        "profession": u.profession,
        "socio_category": u.socio_category,
        # Engagement citoyen
        "priorities": u.priorities,
        "contribution_offer": u.contribution_offer,
        "injustice_experienced": u.injustice_experienced,
        "wish_for_madagascar": u.wish_for_madagascar,
        # Réseaux
        "social_links": u.social_links,
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return _serialize_me(current_user)


class ProfileUpdate(BaseModel):
    pseudo: str | None = None
    full_name: str | None = None
    whatsapp: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    district: str | None = None
    commune: str | None = None
    fokontany: str | None = None
    age_range: str | None = None
    profession: str | None = None
    socio_category: str | None = None
    priorities: str | None = None
    contribution_offer: str | None = None
    injustice_experienced: str | None = None
    wish_for_madagascar: str | None = None
    social_links: str | None = None


@router.patch("/me")
def update_me(data: ProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mise à jour du profil de l'utilisateur connecté."""
    if data.pseudo and data.pseudo != current_user.pseudo:
        if db.query(User).filter(User.pseudo == data.pseudo, User.id != current_user.id).first():
            raise HTTPException(status_code=400, detail="Pseudo déjà utilisé")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return _serialize_me(current_user)
