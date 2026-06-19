from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.utils.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalide ou expirée",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if not user:
        raise credentials_exception

    # last_login : mise à jour non-bloquante (sans commit immédiat)
    # Le commit sera fait en fin de requête si la session est dirty
    user.last_login = datetime.utcnow()
    return user


def get_optional_user(token: str = Depends(oauth2_scheme_optional), db: Session = Depends(get_db)):
    """Retourne l'utilisateur connecté ou None si non authentifié"""
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return db.query(User).filter(User.id == int(user_id), User.is_active == True).first()


def require_role(*roles: UserRole):
    """
    Le superadmin passe toujours, quelle que soit la liste de rôles.
    Les autres rôles sont vérifiés normalement.
    """
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == UserRole.superadmin:
            return current_user   # superadmin a accès à tout
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé — permissions insuffisantes"
            )
        return current_user
    return checker


require_superadmin = require_role(UserRole.superadmin)
require_admin      = require_role(UserRole.admin)
require_moderator  = require_role(UserRole.moderator, UserRole.admin)
require_ambassador = require_role(UserRole.z_ambassador, UserRole.moderator, UserRole.admin)

# --- Helpers de vérification de rôle (utilisés dans les fonctions) ---
STAFF_ROLES = [UserRole.superadmin, UserRole.admin, UserRole.moderator]

def is_staff(user) -> bool:
    """True si l'utilisateur est superadmin, admin ou modérateur."""
    return user is not None and user.role in STAFF_ROLES

def is_privileged(user) -> bool:
    """True si l'utilisateur est superadmin ou admin."""
    return user is not None and user.role in [UserRole.superadmin, UserRole.admin]
