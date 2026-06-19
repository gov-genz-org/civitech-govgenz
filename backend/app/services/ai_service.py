"""
Service IA multi-provider — Civitech GoV Gen Z Madagascar
Supporte : OpenAI, Anthropic Claude, DeepSeek, OpenRouter, Ollama, HuggingFace
"""
import os
import json
import httpx
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from app.models.ai_provider import AIProvider


# ─── Chiffrement des clés API ──────────────────────────────────────────────
def _get_fernet() -> Fernet:
    key = os.environ.get("AI_ENCRYPTION_KEY")
    if not key:
        # Génère une clé stable depuis la SECRET_KEY de l'app
        from app.config import settings
        import base64, hashlib
        raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(raw).decode()
    return Fernet(key.encode())


def encrypt_key(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_key(enc: str) -> str:
    return _get_fernet().decrypt(enc.encode()).decode()


def mask_key(enc: str | None) -> str:
    if not enc:
        return ""
    try:
        plain = decrypt_key(enc)
        return plain[:6] + "••••••••" + plain[-4:] if len(plain) > 10 else "••••••••••••"
    except Exception:
        return "••••••••••••"


# ─── Appel IA ─────────────────────────────────────────────────────────────
PROVIDER_CONFIGS = {
    "openai": {
        "label": "OpenAI (GPT-4o)",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "chat_path": "/chat/completions",
        "auth_header": "Bearer",
    },
    "claude": {
        "label": "Anthropic Claude",
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-haiku-20241022",
        "chat_path": "/messages",
        "auth_header": "x-api-key",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "chat_path": "/chat/completions",
        "auth_header": "Bearer",
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "mistralai/mixtral-8x7b-instruct",
        "chat_path": "/chat/completions",
        "auth_header": "Bearer",
    },
    "ollama": {
        "label": "Ollama (local)",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3",
        "chat_path": "/chat/completions",
        "auth_header": "Bearer",
    },
    "huggingface": {
        "label": "HuggingFace Inference",
        "base_url": "https://api-inference.huggingface.co/v1",
        "default_model": "mistralai/Mistral-7B-Instruct-v0.3",
        "chat_path": "/chat/completions",
        "auth_header": "Bearer",
    },
}


async def call_ai(provider: AIProvider, messages: list[dict], max_tokens: int = 2000) -> str:
    """Appelle le provider IA et retourne la réponse texte."""
    cfg = PROVIDER_CONFIGS.get(provider.name, {})
    base_url = provider.base_url or cfg.get("base_url", "")
    model = provider.model_name or cfg.get("default_model", "")
    api_key = decrypt_key(provider.api_key_enc) if provider.api_key_enc else ""
    chat_path = cfg.get("chat_path", "/chat/completions")
    auth_header = cfg.get("auth_header", "Bearer")

    headers = {"Content-Type": "application/json"}

    # Anthropic a une API légèrement différente
    if provider.name == "claude":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        # Séparer system du reste
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_messages = [m for m in messages if m["role"] != "system"]
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": user_messages,
        }
        if system_msg:
            payload["system"] = system_msg
    else:
        headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{base_url}{chat_path}", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # Extraire le texte selon le format
    if provider.name == "claude":
        return data["content"][0]["text"]
    else:
        return data["choices"][0]["message"]["content"]


def get_active_provider(db: Session) -> AIProvider | None:
    """Retourne le provider actif par défaut."""
    p = db.query(AIProvider).filter(AIProvider.is_active == True, AIProvider.is_default == True).first()
    if not p:
        p = db.query(AIProvider).filter(AIProvider.is_active == True).first()
    return p


# ─── Prompts spécialisés ──────────────────────────────────────────────────
SYSTEM_TRANSPARENCY = """Tu es un assistant expert en analyse de données de gouvernance et de transparence pour Madagascar.
Tu travailles pour la plateforme Civitech GoV Gen Z — un observatoire civique malgache.
Réponds toujours en français. Sois factuel, précis et structuré.
N'invente jamais de données — base-toi uniquement sur ce qui t'est fourni."""

INSIGHT_PROMPT = """Voici un résumé des données de l'observatoire citoyen de Madagascar :

{context}

Génère une analyse structurée en 3 parties :
1. **Tendances majeures** : quels patterns se dégagent ?
2. **Points d'alerte** : quels faits ou entités méritent une attention particulière ?
3. **Recommandations** : quelles investigations complémentaires suggères-tu ?

Sois concis (max 400 mots) et utilise des bullet points."""

CSV_EXTRACTION_PROMPT = """Tu reçois des données tabulaires extraites d'un fichier CSV/Excel.
Ton rôle est d'extraire des informations structurées pour alimenter la base de données de l'observatoire.

Données brutes (format CSV) :
{csv_data}

Extrais et retourne un JSON valide avec cette structure exacte :
{{
  "facts": [
    {{
      "title": "titre court et précis (max 80 chars)",
      "fact_type": "un parmi: deplacement|discours|promesse|decision|transaction|projet|arrestation|perquisition|propagande|plainte|scandale|accord|nomination|autre",
      "official_version": "version officielle si disponible",
      "real_version": "faits documentés / contexte réel",
      "context": "contexte additionnel",
      "event_date": "YYYY ou YYYY-MM ou YYYY-MM-DD",
      "location": "lieu",
      "region_code": "région malgache si identifiable",
      "sector_codes": "codes secteurs parmi: citizen,economy,education,environment,health,infrastructure,justice,media,mines,security,territories,water,food,labor",
      "gravity_score": 5.0,
      "suspicion_score": 5.0,
      "opacity_score": 5.0,
      "is_sensitive": false,
      "actors": ["nom entité 1", "nom entité 2"]
    }}
  ],
  "entities_to_create": [
    {{
      "name": "nom complet",
      "entity_type": "un parmi: person|institution|company|media|ngo|group|international",
      "description": "description courte",
      "region": "région malgache si applicable",
      "sector_codes": "codes secteurs"
    }}
  ],
  "summary": "résumé de ce que tu as trouvé dans ces données (2-3 phrases)"
}}

Retourne UNIQUEMENT le JSON, sans texte avant ou après."""
