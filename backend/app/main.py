from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import Base, engine, SessionLocal
from app.routers import auth, public, ambassadors, consultations, alerts, admin
from app.routers import entities, facts, threads
from app.routers import ai as ai_router
from app.routers import settings as settings_router
from app.routers import upload as upload_router
from app.routers import reactions as reactions_router
from app.routers import media as media_router

# Import models so SQLAlchemy registers them before create_all
import app.models.user       # noqa
import app.models.ambassador # noqa
import app.models.sector     # noqa
import app.models.consultation # noqa
import app.models.alert      # noqa
import app.models.audit      # noqa
import app.models.entity     # noqa
import app.models.fact       # noqa
import app.models.ai_provider # noqa
import app.models.magic_token # noqa
import app.models.site_settings # noqa
import app.models.reaction      # noqa

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Civitech API — GoV Gen Z Madagascar",
    description="Plateforme civitech analytique pour collecter, vérifier et analyser la voix des citoyens.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(public.router)
app.include_router(ambassadors.router)
app.include_router(consultations.router)
app.include_router(alerts.router)
app.include_router(admin.router)
app.include_router(entities.router)
app.include_router(facts.router)
app.include_router(threads.router)
app.include_router(ai_router.router)
app.include_router(settings_router.router)
app.include_router(upload_router.router)
app.include_router(reactions_router.router)
app.include_router(media_router.router)


@app.on_event("startup")
async def startup():
    # Cache Redis (fail-safe — app fonctionne même si Redis absent)
    from app.services.cache import cache
    await cache.connect()

    # Seed base de données
    db = SessionLocal()
    try:
        from app.seed import run_seed
        run_seed(db)
    except Exception as e:
        print(f"Seed warning: {e}")
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "app": "Civitech GoV Gen Z Madagascar"}


@app.get("/")
def root():
    return {
        "app": "Civitech API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
