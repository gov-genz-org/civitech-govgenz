"""
Endpoints d'upload — Civitech GoV Gen Z
- POST /upload/avatar       → photo de profil
- POST /upload/images       → images d'illustration (alerts, threads, faits)
- POST /upload/documents    → preuves / documents (PDF, Word)
"""
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services import storage

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload photo de profil — redimensionnée en carré 400×400."""
    url = await storage.upload_avatar(file, current_user.id)

    # Supprimer l'ancien avatar si existant
    if current_user.avatar_url:
        storage.delete_file(current_user.avatar_url)

    current_user.avatar_url = url
    db.commit()
    return {"url": url}


@router.post("/images")
async def upload_images(
    files: List[UploadFile] = File(...),
    folder: str = "content",
    current_user: User = Depends(get_current_user),
):
    """Upload jusqu'à 5 images d'illustration. Retourne la liste des URLs."""
    if len(files) > 5:
        raise HTTPException(400, "Maximum 5 images à la fois.")
    urls = []
    for f in files:
        url = await storage.upload_image(f, folder=folder)
        urls.append(url)
    return {"urls": urls}


@router.post("/documents")
async def upload_documents(
    files: List[UploadFile] = File(...),
    folder: str = "documents",
    current_user: User = Depends(get_current_user),
):
    """Upload jusqu'à 5 documents (PDF, Word, images). Pour les preuves citoyennes."""
    if len(files) > 5:
        raise HTTPException(400, "Maximum 5 fichiers à la fois.")
    urls = []
    for f in files:
        url = await storage.upload_document(f, folder=folder)
        urls.append({"name": f.filename, "url": url, "type": f.content_type})
    return {"files": urls}
