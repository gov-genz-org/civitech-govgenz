"""
Routes Paramètres site — Civitech GoV Gen Z Madagascar
Lecture publique (clés non sensibles) / Écriture superadmin + admin
"""
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.site_settings import SiteSetting, DEFAULTS, PUBLIC_KEYS
from app.models.sector import Sector, SECTORS
from app.services.auth import get_current_user, require_admin

router = APIRouter(prefix="/settings", tags=["Paramètres"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seed_defaults(db: Session):
    """Crée les entrées manquantes avec les valeurs par défaut."""
    META = {
        # (label, group)
        "cookie_consent_required": ("Bannière cookie obligatoire", "cookies"),
        "platform_name":           ("Nom de la plateforme", "general"),
        "site_tagline":            ("Tagline (sous le logo)", "general"),
        "site_description":        ("Description de la plateforme", "general"),
        "homepage_hero_title":     ("Titre hero (accueil)", "homepage"),
        "homepage_hero_subtitle":  ("Sous-titre hero (accueil)", "homepage"),
        "homepage_cta_primary":    ("Bouton CTA principal", "homepage"),
        "homepage_cta_secondary":  ("Bouton CTA secondaire", "homepage"),
        "contact_email":           ("Email de contact", "general"),
        "social_facebook":         ("Lien Facebook", "social"),
        "social_twitter":          ("Lien Twitter/X", "social"),
        "social_instagram":        ("Lien Instagram", "social"),
        "social_tiktok":           ("Lien TikTok", "social"),
        "social_youtube":          ("Lien YouTube", "social"),
        "social_linkedin":         ("Lien LinkedIn", "social"),
        "website_main":            ("Site principal GoV Gen Z", "social"),
        "maintenance_mode":        ("Mode maintenance", "general"),
        "maintenance_message":     ("Message de maintenance", "general"),
    }
    for key, default_value in DEFAULTS.items():
        existing = db.query(SiteSetting).filter(SiteSetting.key == key).first()
        if not existing:
            label, group = META.get(key, (key, "general"))
            db.add(SiteSetting(key=key, value=default_value, label=label, group=group))
    db.commit()


def _to_dict(settings: list) -> dict:
    return {s.key: s.value for s in settings}


# ── Endpoints publics ─────────────────────────────────────────────────────────

@router.get("/public")
def get_public_settings(db: Session = Depends(get_db)):
    """Retourne uniquement les paramètres publics (pas de token requis)."""
    _seed_defaults(db)
    settings = db.query(SiteSetting).filter(SiteSetting.key.in_(PUBLIC_KEYS)).all()
    result = {s.key: s.value for s in settings}
    # Compléter avec les défauts si manquants
    for k in PUBLIC_KEYS:
        if k not in result:
            result[k] = DEFAULTS.get(k, "")
    return result


# ── Endpoints admin ───────────────────────────────────────────────────────────

@router.get("/", dependencies=[Depends(require_admin)])
def get_all_settings(db: Session = Depends(get_db)):
    """Retourne tous les paramètres (admin+)."""
    _seed_defaults(db)
    settings = db.query(SiteSetting).order_by(SiteSetting.group, SiteSetting.key).all()
    return [
        {
            "id": s.id,
            "key": s.key,
            "value": s.value,
            "label": s.label,
            "group": s.group,
            "updated_at": s.updated_at,
        }
        for s in settings
    ]


class SettingUpdate(BaseModel):
    key: str
    value: str


@router.patch("/", dependencies=[Depends(require_admin)])
def update_settings(
    updates: List[SettingUpdate],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Met à jour un ou plusieurs paramètres."""
    for u in updates:
        setting = db.query(SiteSetting).filter(SiteSetting.key == u.key).first()
        if setting:
            setting.value = u.value
            setting.updated_by = current_user.id
            setting.updated_at = datetime.utcnow()
        else:
            db.add(SiteSetting(
                key=u.key, value=u.value,
                label=u.key, group="general",
                updated_by=current_user.id,
            ))
    db.commit()
    return {"ok": True, "updated": len(updates)}


# ── Secteurs (admin) ──────────────────────────────────────────────────────────

class SectorUpdate(BaseModel):
    code: str
    label: str
    icon: Optional[str] = None
    description: Optional[str] = None


@router.get("/sectors")
def list_sectors(db: Session = Depends(get_db)):
    """Liste tous les secteurs (publique)."""
    sectors = db.query(Sector).order_by(Sector.code).all()
    if not sectors:
        # Seeder les secteurs par défaut si vide
        for code, label, icon in SECTORS:
            db.add(Sector(code=code, label=label, icon=icon))
        db.commit()
        sectors = db.query(Sector).order_by(Sector.code).all()
    return [{"id": s.id, "code": s.code, "label": s.label, "icon": s.icon, "description": s.description} for s in sectors]


@router.patch("/sectors/{sector_id}", dependencies=[Depends(require_admin)])
def update_sector(sector_id: int, data: SectorUpdate, db: Session = Depends(get_db)):
    """Modifier un secteur (admin+)."""
    sector = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector:
        raise HTTPException(status_code=404, detail="Secteur introuvable")
    sector.label       = data.label
    sector.icon        = data.icon or sector.icon
    sector.description = data.description or sector.description
    db.commit()
    return {"ok": True, "id": sector.id, "label": sector.label}


@router.post("/sectors", dependencies=[Depends(require_admin)])
def create_sector(data: SectorUpdate, db: Session = Depends(get_db)):
    """Créer un nouveau secteur."""
    if db.query(Sector).filter(Sector.code == data.code).first():
        raise HTTPException(status_code=400, detail="Code secteur déjà existant")
    s = Sector(code=data.code, label=data.label, icon=data.icon or "📌", description=data.description)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"ok": True, "id": s.id}
