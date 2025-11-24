# app/routers/empresas.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.db.mongo import get_db
from app.schemas.empresa import (
    EmpresaCreate,
    EmpresaUpdate,
    EmpresaRead,
    EmpresaCreateBulk,
)
from app.core.crypto import enc, dec
from app.core.settings import settings

# >>> declare o router ANTES de usar os decorators <<<
router = APIRouter(prefix="/empresas", tags=["empresas"])

# ----------------- helpers -----------------
def to_oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

def require_api_key(x_api_key: str = Header(..., convert_underscores=False)):
    if x_api_key != settings.CRAWLER_API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida")

# ----------------- listagem e leitura -----------------
@router.get("/", response_model=dict)
async def listar(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=200),
    db = Depends(get_db),
):
    coll = db["empresas"]
    total = await coll.count_documents({})
    skip = (page - 1) * limit
    cursor = coll.find({}, skip=skip, limit=limit).sort("_id", -1)
    items = [EmpresaRead(**doc) async for doc in cursor]
    pages = (total + limit - 1) // limit
    return {"items": items, "page": page, "limit": limit, "total": total, "pages": pages}

@router.get("/{empresa_id}", response_model=EmpresaRead)
async def obter(empresa_id: str, db = Depends(get_db)):
    oid = to_oid(empresa_id)
    doc = await db["empresas"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return EmpresaRead(**doc)

# ----------------- criação (single e bulk) -----------------
@router.post("/", response_model=EmpresaRead, status_code=status.HTTP_201_CREATED)
async def criar(payload: EmpresaCreate, db=Depends(get_db)):
    data = payload.model_dump(exclude_none=True)
    if "senha_muni" in data:
        data["senha_muni"] = enc(data["senha_muni"])
    if "senha_est" in data:
        data["senha_est"] = enc(data["senha_est"])
    try:
        res = await db["empresas"].insert_one(data)
    except DuplicateKeyError:
        raise HTTPException(400, detail="CNPJ já cadastrado")
    doc = await db["empresas"].find_one({"_id": res.inserted_id})
    return EmpresaRead(**doc)

@router.post("/bulk", response_model=dict, status_code=status.HTTP_201_CREATED)
async def criar_em_lote(payload: List[EmpresaCreateBulk], db=Depends(get_db)):
    """
    Recebe um ARRAY de empresas (importação em lote).
    Campos de inscrição são opcionais nesse schema.
    """
    coll = db["empresas"]
    created_items: List[EmpresaRead] = []
    duplicates = []
    errors = []

    for idx, item in enumerate(payload):
        data = item.model_dump(exclude_none=True)
        if "senha_muni" in data:
            data["senha_muni"] = enc(data["senha_muni"])
        if "senha_est" in data:
            data["senha_est"] = enc(data["senha_est"])
        try:
            res = await coll.insert_one(data)
            doc = await coll.find_one({"_id": res.inserted_id})
            created_items.append(EmpresaRead(**doc))
        except DuplicateKeyError:
            duplicates.append({"index": idx, "cnpj": data.get("cnpj")})
        except Exception as e:
            errors.append({"index": idx, "error": str(e)})

    return {
        "created": len(created_items),
        "duplicates": len(duplicates),
        "errors": len(errors),
        "items": created_items,
        "duplicates_detail": duplicates[:20],
        "errors_detail": errors[:20],
    }

# ----------------- atualização e remoção -----------------
@router.put("/{empresa_id}", response_model=EmpresaRead)
async def atualizar(empresa_id: str, payload: EmpresaUpdate, db=Depends(get_db)):
    oid = to_oid(empresa_id)
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "senha_muni" in data:
        data["senha_muni"] = enc(data["senha_muni"])
    if "senha_est" in data:
        data["senha_est"] = enc(data["senha_est"])
    await db["empresas"].update_one({"_id": oid}, {"$set": data})
    doc = await db["empresas"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return EmpresaRead(**doc)

@router.delete("/{empresa_id}", response_model=dict)
async def remover(empresa_id: str, db=Depends(get_db)):
    oid = to_oid(empresa_id)
    res = await db["empresas"].delete_one({"_id": oid})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return {"status": True, "message": "Empresa removida"}

# ----------------- credenciais para o crawler -----------------
@router.get("/{empresa_id}/credentials", dependencies=[Depends(require_api_key)], response_model=dict)
async def obter_credenciais(empresa_id: str, db=Depends(get_db)):
    oid = to_oid(empresa_id)
    doc = await db["empresas"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return {
        "login_muni": doc.get("login_muni"),
        "senha_muni": dec(doc.get("senha_muni")),
        "login_est":  doc.get("login_est"),
        "senha_est":  dec(doc.get("senha_est")),
    }
