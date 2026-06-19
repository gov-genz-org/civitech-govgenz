from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── Base de données ───────────────────────────────────────────
    # Aucune valeur par défaut pour les credentials DB : l'app ne doit
    # pas démarrer si ces variables ne sont pas dans le .env
    DB_HOST: str
    DB_PORT: int = 3306
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # ── Sécurité JWT ──────────────────────────────────────────────
    # Générer : openssl rand -hex 32
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ── Application ───────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── Compte admin initial (créé au démarrage si inexistant) ────
    # Ne jamais utiliser la valeur par défaut en production
    ADMIN_EMAIL: str = "admin@civitech.genzgov.org"
    ADMIN_PASSWORD: str  # Requis — pas de fallback

    # ── Redis cache (optionnel — l'app fonctionne sans) ───────────
    REDIS_URL: str = ""

    # ── Backblaze B2 Storage ──────────────────────────────────────
    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_BUCKET_NAME: str = "civitech"
    B2_ENDPOINT_URL: str = "https://s3.us-east-005.backblazeb2.com"
    B2_PUBLIC_URL: str = "https://f005.backblazeb2.com/file/civitech"

    # ── Email SMTP (magic link) ───────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM_NAME: str = "Civitech — GoV Gen Z Madagascar"

    # ── Google Analytics (frontend build) ────────────────────────
    VITE_GA_MEASUREMENT_ID: str = ""

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
