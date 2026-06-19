"""
Proxy media — génère une presigned URL B2 à la volée et redirige.
Permet de servir des fichiers depuis un bucket B2 privé.
"""
import urllib.parse
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
import boto3

from app.config import settings

router = APIRouter(prefix="/media", tags=["Media"])

PRESIGNED_TTL = 3600  # 1 heure — renouvelé automatiquement à chaque accès


def _s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.B2_ENDPOINT_URL,
        aws_access_key_id=settings.B2_KEY_ID,
        aws_secret_access_key=settings.B2_APPLICATION_KEY,
        region_name="us-east-005",
    )


@router.get("/{key:path}")
def serve_media(key: str):
    """
    Génère une presigned URL pour la clé B2 donnée et redirige.
    L'URL expire dans 1h mais le navigateur recharge si nécessaire.
    Cache-Control: 55min pour éviter les re-requêtes inutiles.
    """
    # Décoder l'URL si nécessaire
    decoded_key = urllib.parse.unquote(key)

    try:
        url = _s3().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.B2_BUCKET_NAME, "Key": decoded_key},
            ExpiresIn=PRESIGNED_TTL,
        )
        response = RedirectResponse(url=url, status_code=302)
        response.headers["Cache-Control"] = "private, max-age=3300"  # cache 55min
        return response
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(404, f"Fichier non trouvé : {decoded_key}")
