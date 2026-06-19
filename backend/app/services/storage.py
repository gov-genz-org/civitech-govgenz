"""
Service de stockage Backblaze B2 (compatible S3)
Upload d'images, avatars et documents
"""
import uuid
import io
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
from PIL import Image as PILImage

from app.config import settings

# Types autorisés
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_DOC_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
ALLOWED_ALL = ALLOWED_IMAGE_TYPES | ALLOWED_DOC_TYPES

MAX_IMAGE_SIZE = 10 * 1024 * 1024   # 10 MB
MAX_DOC_SIZE   = 20 * 1024 * 1024   # 20 MB
AVATAR_MAX_DIM = 400                  # px — carré 400×400 max
IMAGE_MAX_DIM  = 1920                 # px — max dimension longue côté


def _get_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.B2_ENDPOINT_URL,
        aws_access_key_id=settings.B2_KEY_ID,
        aws_secret_access_key=settings.B2_APPLICATION_KEY,
        region_name="us-east-005",
    )


def _public_url(key: str) -> str:
    """
    Retourne une URL servie via le proxy /api/media/{key}.
    Le proxy génère une presigned URL B2 à la volée (bucket privé).
    """
    import urllib.parse
    encoded = urllib.parse.quote(key, safe='')
    return f"/api/media/{encoded}"


def _resize_image(data: bytes, max_dim: int, is_avatar: bool = False) -> bytes:
    """Redimensionne l'image si nécessaire, convertit en JPEG/WEBP."""
    img = PILImage.open(io.BytesIO(data))

    # Convertir en RGB (pas de transparence pour JPEG)
    if img.mode in ("RGBA", "P", "LA"):
        bg = PILImage.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    if is_avatar:
        # Crop carré centré puis resize
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top  = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
        img = img.resize((max_dim, max_dim), PILImage.LANCZOS)
    else:
        # Resize proportionnel si > max_dim
        w, h = img.size
        if max(w, h) > max_dim:
            ratio = max_dim / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), PILImage.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85, optimize=True)
    return out.getvalue()


async def upload_avatar(file: UploadFile, user_id: int) -> str:
    """Upload et redimensionne un avatar. Retourne l'URL publique."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "Format non supporté. Utilisez JPEG, PNG ou WEBP.")

    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(400, "Image trop lourde (max 10 Mo).")

    processed = _resize_image(data, AVATAR_MAX_DIM, is_avatar=True)
    key = f"avatars/{user_id}/{uuid.uuid4().hex}.jpg"

    client = _get_client()
    client.put_object(
        Bucket=settings.B2_BUCKET_NAME,
        Key=key,
        Body=processed,
        ContentType="image/jpeg",
    )
    return _public_url(key)


async def upload_image(file: UploadFile, folder: str = "images") -> str:
    """Upload une image (illustration). Retourne l'URL publique."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "Format non supporté. Utilisez JPEG, PNG ou WEBP.")

    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(400, "Image trop lourde (max 10 Mo).")

    processed = _resize_image(data, IMAGE_MAX_DIM)
    key = f"{folder}/{uuid.uuid4().hex}.jpg"

    client = _get_client()
    client.put_object(
        Bucket=settings.B2_BUCKET_NAME,
        Key=key,
        Body=processed,
        ContentType="image/jpeg",
    )
    return _public_url(key)


async def upload_document(file: UploadFile, folder: str = "documents") -> str:
    """Upload un document (PDF, Word, TXT). Retourne l'URL publique."""
    if file.content_type not in ALLOWED_ALL:
        raise HTTPException(400, "Format non supporté. Utilisez PDF, Word ou images.")

    data = await file.read()
    if len(data) > MAX_DOC_SIZE:
        raise HTTPException(400, "Fichier trop lourd (max 20 Mo).")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "bin"
    key = f"{folder}/{uuid.uuid4().hex}.{ext}"

    client = _get_client()
    client.put_object(
        Bucket=settings.B2_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=file.content_type,
    )
    return _public_url(key)


def delete_file(url: str):
    """Supprime un fichier par son URL (proxy ou ancienne URL publique). Best-effort."""
    import urllib.parse
    try:
        key = None
        if url.startswith("/api/media/"):
            key = urllib.parse.unquote(url[len("/api/media/"):])
        elif url.startswith(settings.B2_PUBLIC_URL + "/"):
            key = url[len(settings.B2_PUBLIC_URL) + 1:]
        if not key:
            return
        _get_client().delete_object(Bucket=settings.B2_BUCKET_NAME, Key=key)
    except Exception:
        pass  # Suppression best-effort
