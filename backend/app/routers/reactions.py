"""
Réactions (👍/👎) sur faits, alertes et threads
- GET  /reactions/{content_type}/{content_id}  → compteurs + réaction de l'utilisateur
- POST /reactions/{content_type}/{content_id}  → réagir ou changer/annuler
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.reaction import Reaction
from app.services.auth import get_current_user, get_optional_user
from app.models.user import User

router = APIRouter(prefix="/reactions", tags=["Réactions"])

VALID_TYPES = {"fact", "alert", "thread"}


class ReactionIn(BaseModel):
    reaction: str   # "up" | "down"


@router.get("/{content_type}/{content_id}")
def get_reactions(
    content_type: str,
    content_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if content_type not in VALID_TYPES:
        raise HTTPException(400, "Type invalide")

    rows = db.query(Reaction).filter(
        Reaction.content_type == content_type,
        Reaction.content_id == content_id,
    ).all()

    up   = sum(1 for r in rows if r.reaction == "up")
    down = sum(1 for r in rows if r.reaction == "down")

    user_reaction = None
    if current_user:
        mine = next((r for r in rows if r.user_id == current_user.id), None)
        user_reaction = mine.reaction if mine else None

    return {"up": up, "down": down, "user_reaction": user_reaction, "total": len(rows)}


@router.post("/{content_type}/{content_id}")
def react(
    content_type: str,
    content_id: int,
    data: ReactionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if content_type not in VALID_TYPES:
        raise HTTPException(400, "Type invalide")
    if data.reaction not in ("up", "down"):
        raise HTTPException(400, "Réaction invalide")

    existing = db.query(Reaction).filter(
        Reaction.user_id == current_user.id,
        Reaction.content_type == content_type,
        Reaction.content_id == content_id,
    ).first()

    if existing:
        if existing.reaction == data.reaction:
            # Annuler la réaction (toggle off)
            db.delete(existing)
            db.commit()
            return {"action": "removed", "reaction": None}
        else:
            # Changer de réaction
            existing.reaction = data.reaction
            db.commit()
            return {"action": "changed", "reaction": data.reaction}
    else:
        db.add(Reaction(
            user_id=current_user.id,
            content_type=content_type,
            content_id=content_id,
            reaction=data.reaction,
        ))
        db.commit()
        return {"action": "added", "reaction": data.reaction}
