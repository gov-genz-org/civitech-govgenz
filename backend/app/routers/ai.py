"""
Routes Agent IA — Civitech GoV Gen Z Madagascar
Accès réservé aux admins uniquement.
"""
import io
import csv
import json
import httpx
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai_provider import AIProvider
from app.models.fact import Fact, FactType, VerificationStatus as FactVerif
from app.models.entity import Entity, EntityType
from app.services.auth import require_admin
from app.services.ai_service import (
    PROVIDER_CONFIGS, encrypt_key, mask_key,
    call_ai, get_active_provider,
    SYSTEM_TRANSPARENCY, INSIGHT_PROMPT, CSV_EXTRACTION_PROMPT
)

router = APIRouter(prefix="/ai", tags=["Agent IA"])


# ─── Schemas ──────────────────────────────────────────────────────────────
class ProviderCreate(BaseModel):
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    is_active: bool = False
    is_default: bool = False


class InsightRequest(BaseModel):
    provider_id: Optional[int] = None
    question: Optional[str] = None


# ─── Providers CRUD ───────────────────────────────────────────────────────
@router.get("/providers", dependencies=[Depends(require_admin)])
def list_providers(db: Session = Depends(get_db)):
    providers = db.query(AIProvider).all()
    result = []
    for p in providers:
        cfg = PROVIDER_CONFIGS.get(p.name, {})
        result.append({
            "id": p.id,
            "name": p.name,
            "label": p.label or cfg.get("label", p.name),
            "api_key_masked": mask_key(p.api_key_enc),
            "has_key": bool(p.api_key_enc),
            "base_url": p.base_url or cfg.get("base_url", ""),
            "model_name": p.model_name or cfg.get("default_model", ""),
            "is_active": p.is_active,
            "is_default": p.is_default,
        })

    # Ajouter les providers non encore configurés
    configured_names = {p.name for p in providers}
    for name, cfg in PROVIDER_CONFIGS.items():
        if name not in configured_names:
            result.append({
                "id": None,
                "name": name,
                "label": cfg["label"],
                "api_key_masked": "",
                "has_key": False,
                "base_url": cfg.get("base_url", ""),
                "model_name": cfg.get("default_model", ""),
                "is_active": False,
                "is_default": False,
            })

    return result


@router.put("/providers/{name}", dependencies=[Depends(require_admin)])
def upsert_provider(name: str, data: ProviderCreate, db: Session = Depends(get_db)):
    if name not in PROVIDER_CONFIGS:
        raise HTTPException(400, f"Provider inconnu : {name}")

    cfg = PROVIDER_CONFIGS[name]
    provider = db.query(AIProvider).filter(AIProvider.name == name).first()

    if not provider:
        provider = AIProvider(name=name, label=cfg["label"])
        db.add(provider)

    # Mise à jour des champs
    if data.api_key:
        provider.api_key_enc = encrypt_key(data.api_key)
    provider.base_url = data.base_url or cfg.get("base_url")
    provider.model_name = data.model_name or cfg.get("default_model")
    provider.is_active = data.is_active
    provider.label = cfg["label"]

    # Si on active ce provider comme défaut, désactiver les autres
    if data.is_default:
        db.query(AIProvider).filter(AIProvider.name != name).update({"is_default": False})
        provider.is_default = True
    else:
        provider.is_default = False

    db.commit()
    db.refresh(provider)
    return {"ok": True, "provider": name, "is_active": provider.is_active}


@router.delete("/providers/{name}", dependencies=[Depends(require_admin)])
def delete_provider_key(name: str, db: Session = Depends(get_db)):
    """Supprime la clé API d'un provider (désactive et efface la clé)."""
    provider = db.query(AIProvider).filter(AIProvider.name == name).first()
    if not provider:
        raise HTTPException(404, "Provider non trouvé")
    provider.api_key_enc = None
    provider.is_active = False
    provider.is_default = False
    db.commit()
    return {"ok": True}


# ─── Fetch modèles disponibles (OpenRouter) ──────────────────────────────
@router.get("/providers/{name}/models", dependencies=[Depends(require_admin)])
async def fetch_provider_models(name: str, db: Session = Depends(get_db)):
    """Récupère la liste des modèles disponibles pour un provider (OpenRouter uniquement)."""
    provider = db.query(AIProvider).filter(AIProvider.name == name).first()
    if not provider or not provider.api_key_enc:
        raise HTTPException(400, "Provider non configuré")

    from app.services.ai_service import decrypt_key
    api_key = decrypt_key(provider.api_key_enc)

    if name == "openrouter":
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                resp.raise_for_status()
                data = resp.json()
                models = [
                    {
                        "id": m["id"],
                        "name": m.get("name", m["id"]),
                        "context_length": m.get("context_length", 0),
                        "pricing_prompt": m.get("pricing", {}).get("prompt", "?"),
                    }
                    for m in data.get("data", [])
                    if m.get("id")
                ]
                # Trier par nom
                models.sort(key=lambda x: x["name"].lower())
                return {"ok": True, "models": models}
        except Exception as e:
            raise HTTPException(500, f"Erreur fetch modèles : {str(e)}")
    else:
        raise HTTPException(400, "Fetch de modèles disponible uniquement pour OpenRouter")


# ─── Test provider ────────────────────────────────────────────────────────
@router.post("/providers/{name}/test", dependencies=[Depends(require_admin)])
async def test_provider(name: str, db: Session = Depends(get_db)):
    provider = db.query(AIProvider).filter(AIProvider.name == name).first()
    if not provider or not provider.api_key_enc:
        raise HTTPException(400, "Provider non configuré")
    try:
        reply = await call_ai(provider, [
            {"role": "system", "content": "Tu es un assistant de test."},
            {"role": "user", "content": "Réponds juste 'OK — connexion établie' en français."}
        ], max_tokens=50)
        return {"ok": True, "reply": reply.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Insights sur données existantes ─────────────────────────────────────
@router.post("/insights", dependencies=[Depends(require_admin)])
async def generate_insights(req: InsightRequest, db: Session = Depends(get_db)):
    from app.models.alert import Alert, AlertStatus

    # Choisir le provider
    if req.provider_id:
        provider = db.query(AIProvider).filter(AIProvider.id == req.provider_id).first()
    else:
        provider = get_active_provider(db)

    if not provider or not provider.api_key_enc:
        raise HTTPException(400, "Aucun provider IA actif. Configurez au moins un provider dans les paramètres.")

    # Construire le contexte depuis la DB — avec slugs pour les liens
    facts = db.query(Fact).filter(Fact.is_published == True).limit(60).all()
    entities = db.query(Entity).filter(Entity.is_active == True).limit(40).all()
    alerts = db.query(Alert).filter(Alert.is_public == True).limit(30).all()

    facts_summary = "\n".join([
        f"- [FAIT:{f.slug}] [{f.fact_type}] {f.title} ({f.event_date or '?'}) | gravité:{f.gravity_score} | {f.region_code or 'national'} | secteurs:{f.sector_codes}"
        for f in facts
    ])
    entities_summary = "\n".join([
        f"- [ENTITE:{e.slug}] {e.name} ({e.entity_type}) | {e.region or 'national'} | secteurs:{e.sector_codes or '—'}"
        for e in entities
    ])
    alerts_summary = "\n".join([
        f"- [ALERTE:{a.id}] {a.title} | {a.severity} | {a.region or 'national'} | secteur:{a.sector_main}"
        for a in alerts
    ])

    context = f"""FAITS DOCUMENTÉS ({len(facts)}) :
{facts_summary}

ENTITÉS SUIVIES ({len(entities)}) :
{entities_summary}

ALERTES CITOYENNES ({len(alerts)}) :
{alerts_summary}"""

    INSIGHT_LINKED_PROMPT = """Voici les données de l'observatoire citoyen de Madagascar :

{context}

Génère une analyse structurée en 3 parties :
1. **Tendances majeures** : quels patterns se dégagent ?
2. **Points d'alerte** : quels faits ou entités méritent une attention particulière ?
3. **Recommandations** : quelles investigations complémentaires suggères-tu ?

RÈGLE IMPORTANTE : Lorsque tu mentionnes un fait, une entité ou une alerte présente dans les données, tu DOIS créer un lien markdown en utilisant exactement les identifiants fournis :
- Pour un fait : [Titre du fait](/faits/SLUG-DU-FAIT) — utilise le slug après [FAIT:]
- Pour une entité : [Nom de l'entité](/entites/SLUG-ENTITE) — utilise le slug après [ENTITE:]
- Pour une alerte : cite-la simplement sans lien

Sois concis (max 500 mots), utilise des bullet points et des titres markdown. Réponds en français."""

    question = req.question or ""
    if question:
        user_content = f"{INSIGHT_LINKED_PROMPT.format(context=context)}\n\nQuestion spécifique : {question}"
    else:
        user_content = INSIGHT_LINKED_PROMPT.format(context=context)

    try:
        reply = await call_ai(provider, [
            {"role": "system", "content": SYSTEM_TRANSPARENCY},
            {"role": "user", "content": user_content},
        ], max_tokens=2000)
        return {
            "ok": True,
            "insight": reply,
            "provider": provider.name,
            "facts_count": len(facts),
            "entities_count": len(entities),
            "alerts_count": len(alerts),
        }
    except Exception as e:
        raise HTTPException(500, f"Erreur IA : {str(e)}")


# ─── Ingestion CSV / Excel ────────────────────────────────────────────────
@router.post("/ingest/parse", dependencies=[Depends(require_admin)])
async def parse_file(
    file: UploadFile = File(...),
    provider_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Analyse un fichier CSV/Excel avec l'IA et retourne les faits/entités détectés."""
    import pandas as pd

    if not file.filename:
        raise HTTPException(400, "Fichier requis")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx", "xls"):
        raise HTTPException(400, "Format non supporté. Utilisez CSV, XLSX ou XLS.")

    content = await file.read()

    try:
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(content), nrows=200)
        else:
            df = pd.read_excel(io.BytesIO(content), nrows=200)
    except Exception as e:
        raise HTTPException(400, f"Impossible de lire le fichier : {str(e)}")

    # Convertir en CSV lisible pour l'IA (100 lignes max)
    csv_str = df.head(100).to_csv(index=False)
    if len(csv_str) > 8000:
        csv_str = csv_str[:8000] + "\n[... tronqué]"

    # Choisir le provider
    if provider_id:
        provider = db.query(AIProvider).filter(AIProvider.id == provider_id).first()
    else:
        provider = get_active_provider(db)

    if not provider or not provider.api_key_enc:
        raise HTTPException(400, "Aucun provider IA actif.")

    try:
        raw = await call_ai(provider, [
            {"role": "system", "content": SYSTEM_TRANSPARENCY},
            {"role": "user", "content": CSV_EXTRACTION_PROMPT.format(csv_data=csv_str)},
        ], max_tokens=3000)

        # Parser le JSON retourné
        # Nettoyer si l'IA a ajouté des backticks
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip().rstrip("```").strip()

        parsed = json.loads(raw)
        return {
            "ok": True,
            "provider": provider.name,
            "rows_analyzed": len(df),
            "filename": file.filename,
            **parsed
        }
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"L'IA n'a pas retourné un JSON valide : {str(e)}", "raw": raw[:500]}
    except Exception as e:
        raise HTTPException(500, f"Erreur IA : {str(e)}")


@router.post("/ingest/import", dependencies=[Depends(require_admin)])
async def import_parsed(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Importe les faits/entités validés par l'admin après analyse IA."""
    from app.utils.security import slugify as _slugify
    from app.seed import slugify

    facts_data = payload.get("facts", [])
    entities_data = payload.get("entities_to_create", [])

    created_entities = []
    skipped_entities = []
    created_facts    = []
    skipped_facts    = []
    errors           = []

    # Créer les entités manquantes
    for ed in entities_data:
        name = ed.get("name", "").strip()
        if not name:
            continue
        try:
            existing = db.query(Entity).filter(Entity.name == name).first()
            if existing:
                skipped_entities.append({"name": name, "reason": "déjà existante"})
            else:
                e = Entity(
                    name=name,
                    entity_type=ed.get("entity_type", "person"),
                    description=ed.get("description", ""),
                    region=ed.get("region", ""),
                    sector_codes=ed.get("sector_codes", ""),
                    created_by=current_user.id,
                    is_active=True,
                )
                db.add(e)
                db.flush()
                e.slug = slugify(e.name, e.id)
                created_entities.append(name)
        except Exception as ex:
            errors.append({"type": "entity", "name": name, "error": str(ex)})

    db.commit()

    # Créer les faits (avec détection doublons sur le titre)
    for fd in facts_data:
        title = fd.get("title", "").strip()
        if not title:
            continue
        try:
            existing = db.query(Fact).filter(Fact.title == title).first()
            if existing:
                skipped_facts.append({"title": title, "reason": "titre déjà existant"})
            else:
                f = Fact(
                    title=title,
                    fact_type=fd.get("fact_type", "autre"),
                    official_version=fd.get("official_version", ""),
                    real_version=fd.get("real_version", ""),
                    context=fd.get("context", ""),
                    event_date=fd.get("event_date", ""),
                    location=fd.get("location", ""),
                    region_code=fd.get("region_code", "national"),
                    sector_codes=fd.get("sector_codes", ""),
                    gravity_score=float(fd.get("gravity_score", 5.0)),
                    suspicion_score=float(fd.get("suspicion_score", 5.0)),
                    opacity_score=float(fd.get("opacity_score", 5.0)),
                    is_sensitive=fd.get("is_sensitive", False),
                    is_published=False,
                    verification_status=FactVerif.unverified,
                    submitted_by=current_user.id,
                )
                db.add(f)
                db.flush()
                f.slug = slugify(f.title, f.id)
                created_facts.append(title)
        except Exception as ex:
            errors.append({"type": "fact", "title": title, "error": str(ex)})

    db.commit()

    return {
        "ok": True,
        "entities_created": len(created_entities),
        "entities_skipped": len(skipped_entities),
        "facts_created": len(created_facts),
        "facts_skipped": len(skipped_facts),
        "errors": errors,
        "details": {
            "entities_created": created_entities,
            "entities_skipped": skipped_entities,
            "facts_created": created_facts,
            "facts_skipped": skipped_facts,
        },
        "note": "Les faits créés sont en statut 'non publié' — validez-les dans l'observatoire.",
    }


# ─── Templates Excel ──────────────────────────────────────────────────────────

TEMPLATES = {
    "facts": {
        "filename": "template_faits.xlsx",
        "columns": ["title","fact_type","official_version","real_version","context",
                    "event_date","location","region_code","sector_codes",
                    "gravity_score","suspicion_score","opacity_score","is_sensitive"],
        "example": {
            "title": "Exemple : Détournement de fonds au ministère X",
            "fact_type": "corruption",
            "official_version": "Version officielle ou déclaration gouvernementale",
            "real_version": "Ce qui s'est réellement passé selon les sources",
            "context": "Contexte historique ou politique",
            "event_date": "2024-01-15",
            "location": "Antananarivo",
            "region_code": "analamanga",
            "sector_codes": "economy,justice",
            "gravity_score": 7.5,
            "suspicion_score": 8.0,
            "opacity_score": 6.0,
            "is_sensitive": False,
        }
    },
    "entities": {
        "filename": "template_entites.xlsx",
        "columns": ["name","entity_type","description","region","sector_codes","nationality","political_party","position"],
        "example": {
            "name": "Exemple : Jean Rakoto",
            "entity_type": "politician",
            "description": "Ministre de l'économie depuis 2023",
            "region": "Analamanga",
            "sector_codes": "economy,governance",
            "nationality": "Malgache",
            "political_party": "Parti XYZ",
            "position": "Ministre",
        }
    },
    "consultations": {
        "filename": "template_consultations.xlsx",
        "columns": ["title","description","scope","sector_main","is_public","ends_at"],
        "example": {
            "title": "Exemple : Consultation sur la réforme foncière",
            "description": "Description détaillée de la consultation",
            "scope": "national",
            "sector_main": "territories",
            "is_public": True,
            "ends_at": "2025-06-30",
        }
    },
    "alerts": {
        "filename": "template_alertes.xlsx",
        "columns": ["title","description","alert_type","severity","sector_main","region","city","sources"],
        "example": {
            "title": "Exemple : Déforestation illégale dans la région X",
            "description": "Description détaillée de l'alerte",
            "alert_type": "environmental_crime",
            "severity": "high",
            "sector_main": "environment",
            "region": "Sofia",
            "city": "Mandritsara",
            "sources": "https://source1.mg, https://source2.mg",
        }
    },
}


@router.get("/templates/{content_type}", dependencies=[Depends(require_admin)])
def download_template(content_type: str):
    """Télécharge un template Excel pour l'import d'un type de contenu."""
    import pandas as pd

    if content_type not in TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Type inconnu: {content_type}. Disponibles: {list(TEMPLATES.keys())}")

    tpl = TEMPLATES[content_type]
    df = pd.DataFrame([tpl["example"]], columns=tpl["columns"])

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Données")
        # Ajuster la largeur des colonnes
        ws = writer.sheets["Données"]
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col) + 4
            ws.column_dimensions[col[0].column_letter].width = min(max_len, 60)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{tpl["filename"]}"'}
    )


# ─── Export CSV/Excel ──────────────────────────────────────────────────────────

@router.get("/export/{content_type}", dependencies=[Depends(require_admin)])
def export_content(
    content_type: str,
    status: Optional[str] = None,
    published: Optional[str] = None,   # "true" | "false" | None
    sector: Optional[str] = None,
    fmt: str = "csv",                  # "csv" | "xlsx"
    db: Session = Depends(get_db),
):
    """Export CSV ou Excel d'un type de contenu avec filtres optionnels."""
    import pandas as pd
    from datetime import datetime as dt

    is_pub = None
    if published == "true":  is_pub = True
    elif published == "false": is_pub = False

    rows = []

    if content_type == "facts":
        from app.models.fact import Fact as FactModel
        q = db.query(FactModel)
        if is_pub is not None: q = q.filter(FactModel.is_published == is_pub)
        if status:  q = q.filter(FactModel.verification_status == status)
        if sector:  q = q.filter(FactModel.sector_codes.ilike(f"%{sector}%"))
        for f in q.order_by(FactModel.created_at.desc()).all():
            rows.append({
                "id": f.id, "titre": f.title, "type": f.fact_type,
                "version_officielle": f.official_version, "version_reelle": f.real_version,
                "contexte": f.context, "date_evenement": f.event_date,
                "lieu": f.location, "region": f.region_code, "secteurs": f.sector_codes,
                "score_gravite": f.gravity_score, "score_suspicion": f.suspicion_score,
                "score_opacite": f.opacity_score, "sensible": f.is_sensitive,
                "publie": f.is_published, "verification": f.verification_status,
                "cree_le": f.created_at, "slug": f.slug,
            })
        filename = "faits"

    elif content_type == "entities":
        from app.models.entity import Entity as EntityModel
        q = db.query(EntityModel)
        if is_pub is not None: q = q.filter(EntityModel.is_active == is_pub)
        if sector:  q = q.filter(EntityModel.sector_codes.ilike(f"%{sector}%"))
        for e in q.order_by(EntityModel.name).all():
            rows.append({
                "id": e.id, "nom": e.name, "type": e.entity_type,
                "description": e.description, "region": e.region,
                "secteurs": e.sector_codes, "nationalite": e.nationality,
                "parti_politique": e.political_party, "poste": e.current_position,
                "score_suspicion": e.suspicion_score, "actif": e.is_active,
                "cree_le": e.created_at, "slug": e.slug,
            })
        filename = "entites"

    elif content_type == "consultations":
        from app.models.consultation import Consultation
        q = db.query(Consultation)
        if status:  q = q.filter(Consultation.status == status)
        if sector:  q = q.filter(Consultation.sector_main == sector)
        if is_pub is not None: q = q.filter(Consultation.is_public == is_pub)
        for c in q.order_by(Consultation.created_at.desc()).all():
            rows.append({
                "id": c.id, "titre": c.title, "description": c.description,
                "statut": c.status, "portee": c.scope, "secteur": c.sector_main,
                "publique": c.is_public, "debut": c.starts_at, "fin": c.ends_at,
                "cree_le": c.created_at,
            })
        filename = "consultations"

    elif content_type == "alerts":
        from app.models.alert import Alert
        q = db.query(Alert)
        if status:  q = q.filter(Alert.status == status)
        if sector:  q = q.filter(Alert.sector_main == sector)
        if is_pub is not None: q = q.filter(Alert.is_public == is_pub)
        for a in q.order_by(Alert.created_at.desc()).all():
            rows.append({
                "id": a.id, "titre": a.title, "description": a.description,
                "type": a.alert_type, "gravite": a.severity, "statut": a.status,
                "secteur": a.sector_main, "region": a.region, "ville": a.city,
                "public": a.is_public, "sensible": a.is_sensitive,
                "cree_le": a.created_at,
            })
        filename = "alertes"

    else:
        raise HTTPException(status_code=404, detail=f"Type inconnu: {content_type}")

    df = pd.DataFrame(rows)
    date_str = dt.utcnow().strftime("%Y%m%d")

    if fmt == "xlsx":
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Export")
            ws = writer.sheets["Export"]
            for col in ws.columns:
                max_len = max((len(str(cell.value or "")) for cell in col), default=10) + 4
                ws.column_dimensions[col[0].column_letter].width = min(max_len, 50)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="civitech_{filename}_{date_str}.xlsx"'}
        )
    else:
        buf = io.StringIO()
        df.to_csv(buf, index=False, encoding="utf-8")
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="civitech_{filename}_{date_str}.csv"'}
        )
