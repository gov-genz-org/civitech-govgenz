from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.consultation import (
    Consultation, Question, Response,
    ConsultationStatus, ConsultationScope, QuestionType, CollectionMethod, ResponseStatus
)
from app.models.user import User
from app.services.auth import get_current_user, require_moderator, require_admin

router = APIRouter(prefix="/consultations", tags=["Consultations"])


class QuestionCreate(BaseModel):
    question_type: QuestionType
    text: str
    options: Optional[list] = None
    is_required: bool = True
    allow_proof: bool = False


class ConsultationCreate(BaseModel):
    title: str
    description: Optional[str] = None
    scope: ConsultationScope = ConsultationScope.national
    sector_main: str
    sectors_related: Optional[str] = None
    target_regions: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_public: bool = True
    questions: List[QuestionCreate] = []


class AnswerSubmit(BaseModel):
    question_id: int
    answer: Optional[str] = None
    answer_options: Optional[list] = None
    collection_method: CollectionMethod = CollectionMethod.self_online
    region: Optional[str] = None
    city: Optional[str] = None


@router.get("/")
def list_consultations(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Consultation).filter(Consultation.is_public == True)
    if status:
        query = query.filter(Consultation.status == status)
    else:
        query = query.filter(Consultation.status == ConsultationStatus.active)
    return query.order_by(Consultation.created_at.desc()).all()


@router.get("/{consultation_id}")
def get_consultation(consultation_id: int, db: Session = Depends(get_db)):
    c = db.query(Consultation).filter(Consultation.id == consultation_id, Consultation.is_public == True).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")
    questions = db.query(Question).filter(Question.consultation_id == consultation_id).order_by(Question.order_index).all()
    return {"consultation": c, "questions": questions}


@router.post("/", status_code=201, dependencies=[Depends(require_moderator)])
def create_consultation(data: ConsultationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    consultation = Consultation(
        title=data.title,
        description=data.description,
        scope=data.scope,
        sector_main=data.sector_main,
        sectors_related=data.sectors_related,
        target_regions=data.target_regions,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        is_public=data.is_public,
        created_by=current_user.id,
        status=ConsultationStatus.draft,
    )
    db.add(consultation)
    db.flush()

    for i, q in enumerate(data.questions):
        question = Question(
            consultation_id=consultation.id,
            order_index=i,
            question_type=q.question_type,
            text=q.text,
            options=q.options,
            is_required=q.is_required,
            allow_proof=q.allow_proof,
        )
        db.add(question)

    db.commit()
    return {"message": "Consultation créée", "id": consultation.id}


@router.post("/{consultation_id}/respond")
def submit_response(
    consultation_id: int,
    answers: List[AnswerSubmit],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    c = db.query(Consultation).filter(Consultation.id == consultation_id, Consultation.status == ConsultationStatus.active).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consultation non disponible")

    for answer in answers:
        response = Response(
            consultation_id=consultation_id,
            question_id=answer.question_id,
            citizen_id=current_user.id,
            answer=answer.answer,
            answer_options=answer.answer_options,
            collection_method=answer.collection_method,
            region=answer.region or current_user.region,
            city=answer.city or current_user.city,
            status=ResponseStatus.confirmed,
        )
        db.add(response)

    db.commit()
    return {"message": "Réponses enregistrées avec succès"}


@router.patch("/{consultation_id}/status", dependencies=[Depends(require_moderator)])
async def update_status(consultation_id: int, new_status: ConsultationStatus, db: Session = Depends(get_db)):
    from app.services.cache import cache
    c = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")
    c.status = new_status
    db.commit()
    await cache.invalidate("public:consultations")
    return {"message": f"Statut mis à jour: {new_status}"}


@router.get("/admin/all", dependencies=[Depends(require_moderator)])
def list_all_consultations(status: Optional[str] = None, db: Session = Depends(get_db)):
    """Liste toutes les consultations (admin) avec stats agrégées — 3 queries au lieu de N*3."""
    from sqlalchemy import func, distinct

    query = db.query(Consultation)
    if status and status != "all":
        query = query.filter(Consultation.status == status)
    consultations = query.order_by(Consultation.created_at.desc()).all()

    if not consultations:
        return []

    c_ids = [c.id for c in consultations]

    # Aggregation questions : 1 query
    q_counts = dict(
        db.query(Question.consultation_id, func.count(Question.id))
        .filter(Question.consultation_id.in_(c_ids))
        .group_by(Question.consultation_id)
        .all()
    )

    # Aggregation réponses + participants uniques : 1 query
    resp_stats = {
        row[0]: {"responses": row[1], "respondents": row[2]}
        for row in db.query(
            Response.consultation_id,
            func.count(Response.id),
            func.count(distinct(Response.citizen_id)),
        )
        .filter(Response.consultation_id.in_(c_ids))
        .group_by(Response.consultation_id)
        .all()
    }

    return [
        {
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "status": c.status,
            "scope": c.scope,
            "sector_main": c.sector_main,
            "is_public": c.is_public,
            "starts_at": c.starts_at,
            "ends_at": c.ends_at,
            "created_at": c.created_at,
            "questions_count": q_counts.get(c.id, 0),
            "responses_count": resp_stats.get(c.id, {}).get("responses", 0),
            "respondents_count": resp_stats.get(c.id, {}).get("respondents", 0),
        }
        for c in consultations
    ]


@router.get("/{consultation_id}/results", dependencies=[Depends(require_moderator)])
def get_results(consultation_id: int, db: Session = Depends(get_db)):
    """Résultats agrégés par question pour une consultation."""
    c = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")
    questions = db.query(Question).filter(Question.consultation_id == consultation_id).order_by(Question.order_index).all()

    results = []
    for q in questions:
        responses = db.query(Response).filter(Response.question_id == q.id).all()
        total = len(responses)

        if q.question_type in ("single_choice", "yes_no"):
            counts = {}
            for r in responses:
                key = r.answer or "(vide)"
                counts[key] = counts.get(key, 0) + 1
            breakdown = [{"label": k, "count": v, "pct": round(v / total * 100) if total else 0} for k, v in sorted(counts.items(), key=lambda x: -x[1])]
        elif q.question_type == "multiple_choice":
            counts = {}
            for r in responses:
                for opt in (r.answer_options or []):
                    counts[opt] = counts.get(opt, 0) + 1
            breakdown = [{"label": k, "count": v, "pct": round(v / total * 100) if total else 0} for k, v in sorted(counts.items(), key=lambda x: -x[1])]
        elif q.question_type in ("priority_scale", "satisfaction_scale"):
            vals = [int(r.answer) for r in responses if r.answer and r.answer.isdigit()]
            avg = round(sum(vals) / len(vals), 1) if vals else None
            dist = {}
            for v in vals:
                dist[str(v)] = dist.get(str(v), 0) + 1
            breakdown = {"average": avg, "distribution": [{"value": k, "count": v} for k, v in sorted(dist.items())]}
        else:
            # text: just return count + last 5 answers as samples
            samples = [r.answer for r in responses[-5:] if r.answer]
            breakdown = {"samples": samples}

        results.append({
            "question_id": q.id,
            "question_text": q.text,
            "question_type": q.question_type,
            "total_responses": total,
            "breakdown": breakdown,
        })

    unique_respondents = db.query(Response.citizen_id).filter(
        Response.consultation_id == consultation_id
    ).distinct().count()

    return {
        "consultation": {"id": c.id, "title": c.title, "status": c.status},
        "total_respondents": unique_respondents,
        "questions": results,
    }


class ConsultationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[ConsultationScope] = None
    sector_main: Optional[str] = None
    sectors_related: Optional[str] = None
    target_regions: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_public: Optional[bool] = None


@router.patch("/{consultation_id}", dependencies=[Depends(require_moderator)])
def update_consultation(
    consultation_id: int,
    data: ConsultationUpdate,
    db: Session = Depends(get_db)
):
    """Modifier une consultation existante (modérateur+)"""
    c = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return {"message": "Consultation mise à jour", "id": c.id}


@router.delete("/{consultation_id}", dependencies=[Depends(require_moderator)])
def delete_consultation(
    consultation_id: int,
    db: Session = Depends(get_db)
):
    """Supprimer définitivement une consultation et toutes ses réponses (modérateur+)"""
    c = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")
    db.query(Response).filter(Response.consultation_id == consultation_id).delete()
    db.query(Question).filter(Question.consultation_id == consultation_id).delete()
    db.delete(c)
    db.commit()
    return {"message": "Consultation supprimée"}


# ── CRUD Questions ────────────────────────────────────────────────

class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    question_type: Optional[QuestionType] = None
    options: Optional[list] = None
    is_required: Optional[bool] = None
    allow_proof: Optional[bool] = None
    order_index: Optional[int] = None


@router.get("/{consultation_id}/questions", dependencies=[Depends(require_moderator)])
def list_questions(consultation_id: int, db: Session = Depends(get_db)):
    """Liste toutes les questions d'une consultation (admin)."""
    c = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")
    questions = (
        db.query(Question)
        .filter(Question.consultation_id == consultation_id)
        .order_by(Question.order_index)
        .all()
    )
    return [
        {
            "id": q.id,
            "consultation_id": q.consultation_id,
            "order_index": q.order_index,
            "question_type": q.question_type,
            "text": q.text,
            "options": q.options,
            "is_required": q.is_required,
            "allow_proof": q.allow_proof,
        }
        for q in questions
    ]


@router.post("/{consultation_id}/questions", dependencies=[Depends(require_moderator)])
def add_question(consultation_id: int, data: QuestionCreate, db: Session = Depends(get_db)):
    """Ajouter une question à une consultation existante."""
    c = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")
    count = db.query(Question).filter(Question.consultation_id == consultation_id).count()
    q = Question(
        consultation_id=consultation_id,
        order_index=count,
        question_type=data.question_type,
        text=data.text,
        options=data.options,
        is_required=data.is_required,
        allow_proof=data.allow_proof,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return {"id": q.id, "message": "Question ajoutée"}


@router.patch("/{consultation_id}/questions/{question_id}", dependencies=[Depends(require_moderator)])
def update_question(
    consultation_id: int,
    question_id: int,
    data: QuestionUpdate,
    db: Session = Depends(get_db)
):
    """Modifier une question (texte, type, options, ordre)."""
    q = db.query(Question).filter(
        Question.id == question_id,
        Question.consultation_id == consultation_id
    ).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question non trouvée")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(q, field, value)
    db.commit()
    db.refresh(q)
    return {"id": q.id, "message": "Question mise à jour"}


@router.delete("/{consultation_id}/questions/{question_id}", dependencies=[Depends(require_moderator)])
def delete_question(
    consultation_id: int,
    question_id: int,
    db: Session = Depends(get_db)
):
    """Supprimer une question et ses réponses associées."""
    q = db.query(Question).filter(
        Question.id == question_id,
        Question.consultation_id == consultation_id
    ).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question non trouvée")
    db.query(Response).filter(Response.question_id == question_id).delete()
    db.delete(q)
    db.commit()
    # Réindexer les questions restantes
    remaining = (
        db.query(Question)
        .filter(Question.consultation_id == consultation_id)
        .order_by(Question.order_index)
        .all()
    )
    for i, rq in enumerate(remaining):
        rq.order_index = i
    db.commit()
    return {"message": "Question supprimée"}


# ── Export réponses (admin+) ──────────────────────────────────────

@router.get("/{consultation_id}/export", dependencies=[Depends(require_admin)])
def export_responses(consultation_id: int, db: Session = Depends(get_db)):
    """Export Excel 2 onglets : résultats agrégés + réponses individuelles anonymisées."""
    import io
    import pandas as pd
    from datetime import datetime as dt
    from sqlalchemy import func, distinct

    c = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")

    questions = db.query(Question).filter(Question.consultation_id == consultation_id).order_by(Question.order_index).all()
    responses = db.query(Response).filter(Response.consultation_id == consultation_id).all()

    # ── Onglet 1 : résultats agrégés ─────────────────────────────
    agg_rows = []
    for q in questions:
        q_responses = [r for r in responses if r.question_id == q.id]
        total = len(q_responses)
        if q.question_type in ("single_choice", "yes_no"):
            counts = {}
            for r in q_responses:
                k = r.answer or "(vide)"
                counts[k] = counts.get(k, 0) + 1
            for label, cnt in sorted(counts.items(), key=lambda x: -x[1]):
                agg_rows.append({
                    "Question": q.text,
                    "Type": q.question_type,
                    "Réponse": label,
                    "Nombre": cnt,
                    "Pourcentage": f"{round(cnt/total*100)}%" if total else "0%",
                    "Total réponses": total,
                })
        elif q.question_type == "multiple_choice":
            counts = {}
            for r in q_responses:
                for opt in (r.answer_options or []):
                    counts[opt] = counts.get(opt, 0) + 1
            for label, cnt in sorted(counts.items(), key=lambda x: -x[1]):
                agg_rows.append({
                    "Question": q.text,
                    "Type": q.question_type,
                    "Réponse": label,
                    "Nombre": cnt,
                    "Pourcentage": f"{round(cnt/total*100)}%" if total else "0%",
                    "Total réponses": total,
                })
        elif q.question_type in ("priority_scale", "satisfaction_scale"):
            vals = [int(r.answer) for r in q_responses if r.answer and r.answer.isdigit()]
            avg = round(sum(vals)/len(vals), 2) if vals else None
            agg_rows.append({
                "Question": q.text,
                "Type": q.question_type,
                "Réponse": f"Moyenne: {avg}/10",
                "Nombre": len(vals),
                "Pourcentage": "",
                "Total réponses": total,
            })
        else:
            samples = [r.answer for r in q_responses if r.answer]
            agg_rows.append({
                "Question": q.text,
                "Type": q.question_type,
                "Réponse": f"{len(samples)} réponse(s) texte",
                "Nombre": len(samples),
                "Pourcentage": "",
                "Total réponses": total,
            })

    # ── Onglet 2 : réponses individuelles anonymisées ────────────
    q_index = {q.id: q.text for q in questions}
    indiv_rows = []
    for r in sorted(responses, key=lambda x: x.created_at or dt.min):
        indiv_rows.append({
            "Question": q_index.get(r.question_id, f"Q#{r.question_id}"),
            "Réponse": r.answer or (", ".join(r.answer_options) if r.answer_options else ""),
            "Région": r.region or "",
            "Ville": r.city or "",
            "Méthode de collecte": r.collection_method or "",
            "Date": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
        })

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_agg = pd.DataFrame(agg_rows) if agg_rows else pd.DataFrame(columns=["Question","Type","Réponse","Nombre","Pourcentage","Total réponses"])
        df_indiv = pd.DataFrame(indiv_rows) if indiv_rows else pd.DataFrame(columns=["Question","Réponse","Région","Ville","Méthode de collecte","Date"])
        df_agg.to_excel(writer, index=False, sheet_name="Résultats agrégés")
        df_indiv.to_excel(writer, index=False, sheet_name="Réponses individuelles")
        for sheet_name, df in [("Résultats agrégés", df_agg), ("Réponses individuelles", df_indiv)]:
            ws = writer.sheets[sheet_name]
            for col in ws.columns:
                max_len = max((len(str(cell.value or "")) for cell in col), default=10) + 4
                ws.column_dimensions[col[0].column_letter].width = min(max_len, 60)
    buf.seek(0)
    date_str = dt.utcnow().strftime("%Y%m%d")
    safe_title = "".join(c for c in c.title[:30] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="civitech_consultation_{safe_title}_{date_str}.xlsx"'}
    )


# ── Participants (admin+) ─────────────────────────────────────────

@router.get("/{consultation_id}/respondents", dependencies=[Depends(require_admin)])
def list_respondents(consultation_id: int, db: Session = Depends(get_db)):
    """Liste des participants à une consultation avec leurs réponses (admin+)."""
    from sqlalchemy import func, distinct
    c = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")

    questions = db.query(Question).filter(Question.consultation_id == consultation_id).order_by(Question.order_index).all()
    q_index = {q.id: {"text": q.text, "type": q.question_type} for q in questions}

    # Grouper les réponses par citoyen
    citizen_ids = db.query(distinct(Response.citizen_id)).filter(Response.consultation_id == consultation_id).all()
    citizen_ids = [cid[0] for cid in citizen_ids]

    result = []
    for cid in citizen_ids:
        user = db.query(User).filter(User.id == cid).first()
        responses = db.query(Response).filter(
            Response.consultation_id == consultation_id,
            Response.citizen_id == cid
        ).all()
        answered_at = max((r.created_at for r in responses if r.created_at), default=None)
        result.append({
            "citizen_id": cid,
            "display_name": (user.full_name or user.email.split('@')[0]) if user else f"Citoyen #{cid}",
            "region": user.region if user else None,
            "role": user.role if user else None,
            "answered_at": answered_at,
            "answers": [
                {
                    "question": q_index.get(r.question_id, {}).get("text", f"Q#{r.question_id}"),
                    "question_type": q_index.get(r.question_id, {}).get("type"),
                    "answer": r.answer,
                    "answer_options": r.answer_options,
                    "region": r.region,
                    "collection_method": r.collection_method,
                }
                for r in sorted(responses, key=lambda x: x.question_id)
            ]
        })

    return {
        "consultation_id": consultation_id,
        "title": c.title,
        "total_respondents": len(result),
        "respondents": sorted(result, key=lambda x: x["answered_at"] or datetime.min, reverse=True),
    }


# ── Insights IA (admin+) ──────────────────────────────────────────

class InsightPublishRequest(BaseModel):
    publish: bool = False


@router.post("/{consultation_id}/insights", dependencies=[Depends(require_admin)])
async def generate_consultation_insight(
    consultation_id: int,
    req: InsightPublishRequest,
    db: Session = Depends(get_db)
):
    """Génère un insight IA sur les résultats d'une consultation (admin+). Publiable publiquement."""
    from app.services.ai_service import call_ai, get_active_provider
    from app.models.ai import AIProvider

    c = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")

    provider = get_active_provider(db)
    if not provider or not provider.api_key_enc:
        raise HTTPException(400, "Aucun provider IA actif. Configurez un provider dans les paramètres.")

    # Construire le contexte : questions + résultats agrégés
    questions = db.query(Question).filter(Question.consultation_id == consultation_id).order_by(Question.order_index).all()
    responses = db.query(Response).filter(Response.consultation_id == consultation_id).all()
    total_respondents = len(set(r.citizen_id for r in responses))

    lines = []
    for q in questions:
        q_resp = [r for r in responses if r.question_id == q.id]
        total = len(q_resp)
        lines.append(f"\nQ: {q.text} (type: {q.question_type}, {total} réponses)")
        if q.question_type in ("single_choice", "yes_no"):
            counts = {}
            for r in q_resp:
                k = r.answer or "(vide)"
                counts[k] = counts.get(k, 0) + 1
            for label, cnt in sorted(counts.items(), key=lambda x: -x[1]):
                pct = round(cnt/total*100) if total else 0
                lines.append(f"  → {label}: {cnt} ({pct}%)")
        elif q.question_type == "multiple_choice":
            counts = {}
            for r in q_resp:
                for opt in (r.answer_options or []):
                    counts[opt] = counts.get(opt, 0) + 1
            for label, cnt in sorted(counts.items(), key=lambda x: -x[1]):
                lines.append(f"  → {label}: {cnt}")
        elif q.question_type in ("priority_scale", "satisfaction_scale"):
            vals = [int(r.answer) for r in q_resp if r.answer and r.answer.isdigit()]
            avg = round(sum(vals)/len(vals), 1) if vals else "N/A"
            lines.append(f"  → Moyenne: {avg}/10")
        else:
            samples = [r.answer for r in q_resp if r.answer][:5]
            for s in samples:
                lines.append(f'  → "{s}"')

    data_summary = "\n".join(lines)

    prompt = f"""Tu es un analyste civique expert en participation citoyenne pour Madagascar.

Consultation : "{c.title}"
Secteur principal : {c.sector_main}
Portée : {c.scope}
Participants : {total_respondents}
Statut : {c.status}

Résultats :
{data_summary}

Rédige une synthèse d'analyse claire, structurée et neutre en français.
La synthèse doit inclure :
1. Un résumé des grandes tendances
2. Les points de consensus et de divergence
3. 2-3 recommandations concrètes à destination des décideurs
4. Un paragraphe sur la représentativité (régions, méthodes de collecte si pertinent)

Ton public : citoyens et décideurs malgaches. Reste factuel, accessible, sans jargon excessif.
Format : texte structuré avec sections numérotées, maximum 400 mots."""

    try:
        insight_text = await call_ai(provider, [
            {"role": "system", "content": "Tu es un analyste expert en participation citoyenne et gouvernance à Madagascar."},
            {"role": "user", "content": prompt}
        ], max_tokens=600)
    except Exception as e:
        raise HTTPException(500, f"Erreur IA : {str(e)}")

    c.published_insight = insight_text.strip()
    c.insight_generated_at = datetime.utcnow()
    c.insight_published = req.publish
    db.commit()

    return {
        "insight": c.published_insight,
        "generated_at": c.insight_generated_at,
        "published": c.insight_published,
    }


@router.patch("/{consultation_id}/insights/publish", dependencies=[Depends(require_admin)])
def toggle_insight_publish(
    consultation_id: int,
    req: InsightPublishRequest,
    db: Session = Depends(get_db)
):
    """Publie ou dépublie l'insight IA d'une consultation."""
    c = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")
    if not c.published_insight:
        raise HTTPException(400, "Aucun insight généré pour cette consultation.")
    c.insight_published = req.publish
    db.commit()
    return {"published": c.insight_published, "message": "Insight " + ("publié" if req.publish else "dépublié")}
