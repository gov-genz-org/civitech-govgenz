from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class AIProvider(Base):
    __tablename__ = "ai_providers"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(50), unique=True, nullable=False)   # openai / claude / deepseek / openrouter / ollama / huggingface
    label       = Column(String(100), nullable=False)               # Nom affiché
    api_key_enc = Column(Text, nullable=True)                       # Clé chiffrée (Fernet)
    base_url    = Column(String(255), nullable=True)                # Pour Ollama / OpenRouter
    model_name  = Column(String(100), nullable=True)               # Modèle par défaut
    is_active   = Column(Boolean, default=False)
    is_default  = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())
