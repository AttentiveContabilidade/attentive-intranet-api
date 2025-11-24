from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os

from fastapi import FastAPI, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# --------------------------
# Routers
# --------------------------
from app.routers import escrituracao, usuarios, empresas, auth
from app.routers import logs as logs_router
from app.routers import departamentos
from app.routers import cursos
from app.routers import colaboradores   # ✅ NOVO módulo
from app.routers import comunicados     # ✅ NOVO: comunicados

# --------------------------
# Settings e Startup
# --------------------------
from app.core.config import settings
from app.startup import ensure_indexes  # cria índices no Mongo (ex.: cnpj único)

# Compat: tenta importar do módulo novo (mongodb) e cai para o antigo (mongo)
try:
    from app.db.mongodb import get_db, get_db_logs
except Exception:
    try:
        from app.db.mongo import get_db, get_db_logs
    except Exception as e:
        def get_db_logs(*args, **kwargs):
            raise RuntimeError(
                "get_db_logs não encontrado. Atualize app/db/mongodb.py OU app/db/mongo.py com get_db_logs()."
            ) from e

# Carrega variáveis do .env (MONGO_URI, etc.)
load_dotenv()


# ---------------------------------------------------------
# Lifespan: executa na inicialização/encerramento do app
# ---------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # on_startup
    await ensure_indexes()
    yield
    # on_shutdown (fechamento explícito do client, se necessário)


app = FastAPI(
    title="Attentive",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# CORS — necessário para cookie HttpOnly (major token)
# ---------------------------------------------------------
env_origins = os.getenv("ALLOW_ORIGINS")
if env_origins:
    origins = [o.strip() for o in env_origins.split(",") if o.strip()]
else:
    origins = settings.BACKEND_CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # não usar "*" com allow_credentials=True
    allow_credentials=True,      # necessário para cookie HttpOnly
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# API principal prefixada (/api/v1)
# ---------------------------------------------------------
api = APIRouter(prefix="/api/v1")

# Inclui todos os módulos
api.include_router(usuarios.router)
api.include_router(empresas.router)
api.include_router(escrituracao.router)
api.include_router(auth.router)            # /api/v1/auth/*
api.include_router(logs_router.router)     # /api/v1/logs/*
api.include_router(departamentos.router)   # /api/v1/departamentos/*
api.include_router(cursos.router)          # /api/v1/cursos/*
api.include_router(colaboradores.router)   # ✅ /api/v1/colaboradores/*
api.include_router(comunicados.router)     # ✅ /api/v1/comunicados/*

# ---------------------------------------------------------
# Sub-rotas de LOGS (aparecem no /docs)
# ---------------------------------------------------------
logs_api = APIRouter(tags=["logs"])

class LogIn(BaseModel):
    source: str = Field(..., examples=["api", "crawler"])
    action: str = Field(..., examples=["health_check", "run_start", "emitir_cnd"])
    ok: bool = True
    meta: dict | None = None

@logs_api.post("/test")
async def create_test_log(payload: LogIn):
    """Insere um log de teste no banco Attentive_logs (collection: logs)."""
    db_logs = await get_db_logs()
    doc = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **payload.model_dump(),
    }
    res = await db_logs["logs"].insert_one(doc)
    return {"inserted_id": str(res.inserted_id)}

@logs_api.get("/recent")
async def recent_logs(limit: int = 5):
    """Retorna os últimos logs do Attentive_logs.logs (ordem decrescente)."""
    db_logs = await get_db_logs()
    items = await db_logs["logs"].find().sort("_id", -1).limit(limit).to_list(length=limit)
    for it in items:
        it["_id"] = str(it["_id"])
    return items

# Monta o sub-router /logs sob /api/v1
api.include_router(logs_api, prefix="/logs")

# Acopla o router principal
app.include_router(api)


# ---------------------------------------------------------
# Healthcheck e exemplos básicos
# ---------------------------------------------------------
class ItemIn(BaseModel):
    name: str
    price: float
    in_stock: bool = True

@app.get("/health")
async def health(db=Depends(get_db)):
    await db.command("ping")
    return {"status": "ok", "origins": origins}

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

@app.post("/items")
def create_item(item: ItemIn):
    return {"ok": True, "data": item}
