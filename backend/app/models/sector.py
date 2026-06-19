from sqlalchemy import Column, Integer, String, Text
from app.database import Base

SECTORS = [
    ("legal", "Juridique & État de droit", "⚖️"),
    ("economy", "Économie & Finance", "📈"),
    ("food", "Alimentation & Agriculture", "🌾"),
    ("energy", "Énergie", "⚡"),
    ("water", "Eau & Assainissement", "💧"),
    ("education", "Éducation & Formation", "📚"),
    ("health", "Santé", "🏥"),
    ("infrastructure", "Infrastructures & Transport", "🏗️"),
    ("digital", "Numérique & Innovation", "💻"),
    ("territories", "Territoires & Urbanisme", "🗺️"),
    ("environment", "Environnement & Climat", "🌿"),
    ("mines", "Mines & Ressources naturelles", "⛏️"),
    ("security", "Sécurité & Justice", "🛡️"),
    ("citizen", "Citoyenneté & Démocratie", "🗳️"),
    ("tourism", "Tourisme & Culture", "🌺"),
]


class Sector(Base):
    __tablename__ = "sectors"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    label = Column(String(200), nullable=False)
    icon = Column(String(10))
    description = Column(Text)
