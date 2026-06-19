from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    # pool_pre_ping=True coûte 1 RTT (170ms) sur chaque checkout depuis BDD distante.
    # On désactive et on recycle rapidement pour éviter les connexions mortes.
    pool_pre_ping=False,
    pool_recycle=600,            # Recycler toutes les 10min (MySQL wait_timeout > 8h par défaut)
    pool_size=15,                # Connexions persistantes dans le pool
    max_overflow=10,             # Pics de charge
    pool_timeout=30,             # Attente max pour obtenir une connexion du pool
    connect_args={
        "connect_timeout": 10,
        "read_timeout": 30,
        "write_timeout": 30,
    },
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
