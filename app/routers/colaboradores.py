# app/routers/colaboradores.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from bson import ObjectId

from app.db.mongo import get_db

router = APIRouter(prefix="/colaboradores", tags=["colaboradores"])

def _norm(s: Optional[str]) -> Optional[str]:
    return s.strip().lower() if isinstance(s, str) else s

# ---------------------------------------
# LISTAR (com busca, filtro e paginação)
# ---------------------------------------
@router.get("/")
async def listar_colaboradores(
    db = Depends(get_db),
    q: Optional[str] = Query(None, description="Busca por nome/sobrenome/email"),
    departamento: Optional[str] = Query(None, description="Slug do departamento"),
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=200),
):
    filtro = {"ativo": True}

    if departamento:
        # aceitamos tanto 'tax' quanto 'TAX'
        filtro["$or"] = [
            {"departamento_slug": _norm(departamento)},
            {"departamento": departamento},  # fallback para bases antigas
        ]

    if q:
        rx = {"$regex": q, "$options": "i"}
        filtro["$or"] = [
            {"nome": rx},
            {"sobrenome": rx},
            {"display_name": rx},
            {"email": rx},
        ]

    proj = {
        "senha_hash": 0,
        "feedbacks": 0,
        # não precisamos devolver descrição/cursos na lista
        "descricao_html": 0,
        "cursos": 0,
    }

    skip = (page - 1) * limit
    cursor = db["usuarios"].find(filtro, proj).sort("nome", 1).skip(skip).limit(limit)

    out: List[dict] = []
    async for u in cursor:
        out.append({
            "id": str(u["_id"]),
            "nome": u.get("nome") or u.get("display_name"),
            "sobrenome": u.get("sobrenome"),
            "display_name": u.get("display_name") or u.get("nome"),
            "email": u.get("email"),
            "departamento": u.get("departamento"),
            "departamento_slug": u.get("departamento_slug") or _norm(u.get("departamento")),
            "avatar_url": u.get("avatar_url"),
        })

    total = await db["usuarios"].count_documents({"ativo": True, **({} if not departamento and not q else {})})
    return {
        "items": out,
        "page": page,
        "limit": limit,
        "has_more": (skip + len(out)) < total
    }

# ------------------------------------------------
# PERFIL PÚBLICO (/colaboradores/:id) + CURSOS
# ------------------------------------------------
@router.get("/{user_id}", summary="Perfil público de um colaborador")
async def perfil_publico_colaborador(user_id: str, db = Depends(get_db)):
    # tenta ObjectId; se não for válido, 404
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado.")

    u = await db["usuarios"].find_one(
        {"_id": oid},
        {"senha_hash": 0, "feedbacks": 0}
    )
    if not u:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado.")

    # normalizações p/ front
    dep_slug = u.get("departamento_slug") or _norm(u.get("departamento"))
    dep_nome = u.get("departamento_nome") or u.get("departamento") or (dep_slug or "").upper()

    # cursos do departamento (apenas ativos)
    cursos_cursor = db["cursos"].find(
        {"departamento_slug": dep_slug, "ativo": True},
        {"_id": 0, "slug": 1, "nome": 1, "pontos": 1, "carga_horaria": 1, "url": 1}
    ).sort("nome", 1)

    cursos = [c async for c in cursos_cursor]

    return {
        "id": str(u["_id"]),
        "nome": u.get("nome") or u.get("display_name"),
        "display_name": u.get("display_name") or u.get("nome"),
        "sobrenome": u.get("sobrenome"),
        "email": u.get("email"),
        "avatar_url": u.get("avatar_url"),
        "departamento": u.get("departamento"),
        "departamento_slug": dep_slug,
        "departamento_nome": dep_nome,
        "descricao_html": u.get("descricao_html") or u.get("descricao") or "",
        "cursos_departamento": cursos,   # ← a tela usa esta lista
    }
