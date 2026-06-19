"""
Service de cache Redis — Civitech
──────────────────────────────────
Principe :
  - Si Redis est disponible : lit/écrit dans le cache
  - Si Redis est absent/planté : l'app fonctionne normalement sans cache
    (fail-safe — Redis n'est jamais un point de blocage)

TTL par type de données :
  - Stats publiques    : 5 min  (changent peu)
  - Liste entités      : 5 min
  - Liste faits        : 3 min  (peuvent être publiés par admin)
  - Liste threads      : 3 min
  - Secteurs           : 60 min (très stables)

Invalidation :
  Appeler cache.invalidate("facts") après toute action admin
  qui modifie les faits (publish, update, delete).
"""

import json
import logging
from typing import Any, Optional
from functools import wraps

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# ── TTL par préfixe de clé (secondes) ────────────────────────
TTL_MAP = {
    "public:stats":         300,   # 5 min
    "public:alerts":        180,   # 3 min
    "public:consultations": 300,   # 5 min
    "entities:list":        300,   # 5 min
    "facts:list":           180,   # 3 min
    "threads:list":         180,   # 3 min
    "sectors:list":         3600,  # 1 heure
}
DEFAULT_TTL = 180  # 3 min par défaut


class CacheService:
    """Wrapper Redis fail-safe — si Redis est down, on passe silencieusement."""

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        self._available = False

    async def connect(self):
        """Initialise la connexion Redis. Appelé au démarrage de l'app."""
        redis_url = getattr(settings, "REDIS_URL", None)
        if not redis_url:
            logger.info("Cache: REDIS_URL non défini — cache désactivé")
            return

        try:
            self._client = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            await self._client.ping()
            self._available = True
            logger.info(f"Cache: Redis connecté ({redis_url})")
        except Exception as e:
            logger.warning(f"Cache: Redis indisponible ({e}) — mode sans cache")
            self._available = False

    async def get(self, key: str) -> Optional[Any]:
        """Retourne la valeur du cache, ou None si absent/expiré."""
        if not self._available or not self._client:
            return None
        try:
            data = await self._client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.debug(f"Cache GET error ({key}): {e}")
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Stocke une valeur dans le cache."""
        if not self._available or not self._client:
            return False
        try:
            # TTL automatique selon le préfixe de la clé
            if ttl is None:
                for prefix, t in TTL_MAP.items():
                    if key.startswith(prefix):
                        ttl = t
                        break
                else:
                    ttl = DEFAULT_TTL

            await self._client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.debug(f"Cache SET error ({key}): {e}")
            return False

    async def invalidate(self, pattern: str) -> int:
        """Supprime toutes les clés correspondant au pattern.
        Ex: invalidate('facts:*') supprime tout le cache des faits.
        """
        if not self._available or not self._client:
            return 0
        try:
            keys = await self._client.keys(f"{pattern}*")
            if keys:
                await self._client.delete(*keys)
                logger.info(f"Cache: {len(keys)} clés invalidées ({pattern})")
                return len(keys)
        except Exception as e:
            logger.debug(f"Cache INVALIDATE error ({pattern}): {e}")
        return 0

    async def flush(self) -> bool:
        """Vide tout le cache (à utiliser avec précaution)."""
        if not self._available or not self._client:
            return False
        try:
            await self._client.flushdb()
            logger.info("Cache: base vidée")
            return True
        except Exception as e:
            logger.debug(f"Cache FLUSH error: {e}")
            return False

    @property
    def is_available(self) -> bool:
        return self._available


# Instance globale — importée partout dans l'app
cache = CacheService()
