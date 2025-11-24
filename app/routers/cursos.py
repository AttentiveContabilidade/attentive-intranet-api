# app/routers/cursos.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone
from bson import ObjectId

from app.schemas.curso import (
    CursoCreate, CursoUpdate, CursoRead, CursoBulkItem
)
from app.dependencies.db import get_db
from app.core.security import get_current_user_id

router = APIRouter(prefix="/cursos", tags=["Cursos"])

def _now():
    return datetime.now(timezone.utc).isoformat()

def _norm(s: Optional[str]) -> Optional[str]:
    return s.strip().lower() if s is not None else None

def _url(v: Optional[str]) -> Optional[str]:
    # Pydantic HttpUrl vira objeto; convertemos pra str antes de salvar
    return str(v) if v is not None else None


@router.post("", response_model=CursoRead)
async def criar_curso(payload: CursoCreate, db=Depends(get_db)):
    slug = _norm(payload.slug)
    dep = _norm(payload.departamento_slug)
    if not slug or not dep:
        raise HTTPException(400, "slug e departamento_slug são obrigatórios.")

    # valida departamento
    parent = await db["departamentos"].find_one({"slug": dep})
    if not parent:
        raise HTTPException(400, f"departamento_slug '{dep}' não encontrado.")

    exists = await db["cursos"].find_one({"slug": slug})
    if exists:
        raise HTTPException(409, f"slug '{slug}' já existe.")

    doc = {
        "nome": payload.nome,
        "slug": slug,
        "departamento_slug": dep,
        "carga_horaria": float(payload.carga_horaria) if payload.carga_horaria is not None else None,
        "pontos": payload.pontos,
        "ativo": payload.ativo,

        # 🔗 URLs convertidas para string
        "url": _url(payload.url),
        "url_plataforma": _url(payload.url_plataforma),
        "thumbnail_url": _url(payload.thumbnail_url),
        "doc_url": _url(payload.doc_url),

        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    res = await db["cursos"].insert_one(doc)
    created = await db["cursos"].find_one({"_id": res.inserted_id})
    created["_id"] = str(created["_id"])
    return CursoRead(**created)


@router.get("", response_model=List[CursoRead])
async def listar_cursos(
    departamento: Optional[str] = Query(None, alias="departamento_slug"),
    apenas_ativos: bool = True,
    db=Depends(get_db),
):
    q = {}
    if departamento:
        q["departamento_slug"] = _norm(departamento)
    if apenas_ativos:
        q["ativo"] = True

    cursor = db["cursos"].find(q).sort("nome", 1)
    items = [c async for c in cursor]
    for c in items:
        c["_id"] = str(c["_id"])
    return [CursoRead(**c) for c in items]


@router.get("/me")
async def cursos_do_meu_departamento(
    db=Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Retorna os cursos do departamento do usuário autenticado (via minor token).
    Response:
    {
      "departamento": "<slug>",
      "cursos": [CursoRead, ...]
    }
    """
    # carrega usuário para descobrir o departamento
    try:
        oid = ObjectId(current_user_id)
    except Exception:
        raise HTTPException(status_code=401, detail="ID inválido no token")

    user = await db["usuarios"].find_one({"_id": oid}, {"departamento": 1})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    dep = _norm(user.get("departamento"))
    if not dep:
        # sem departamento => retorna vazio (não é erro)
        return {"departamento": None, "cursos": []}

    # busca cursos ativos do departamento
    cursor = db["cursos"].find({"departamento_slug": dep, "ativo": True}).sort("nome", 1)
    cursos_docs = [c async for c in cursor]
    for c in cursos_docs:
        c["_id"] = str(c["_id"])

    cursos = [CursoRead(**c) for c in cursos_docs]
    return {"departamento": dep, "cursos": cursos}


@router.get("/{slug}", response_model=CursoRead)
async def obter_curso(slug: str, db=Depends(get_db)):
    c = await db["cursos"].find_one({"slug": _norm(slug)})
    if not c:
        raise HTTPException(404, "Curso não encontrado.")
    c["_id"] = str(c["_id"])
    return CursoRead(**c)


@router.put("/{slug}", response_model=CursoRead)
async def atualizar_curso(slug: str, data: CursoUpdate, db=Depends(get_db)):
    update = data.model_dump(exclude_unset=True)

    # normalizações textuais
    if "slug" in update and update["slug"] is not None:
        update["slug"] = _norm(update["slug"])
    if "departamento_slug" in update and update["departamento_slug"] is not None:
        update["departamento_slug"] = _norm(update["departamento_slug"])
        # valida departamento
        dep_ok = await db["departamentos"].find_one({"slug": update["departamento_slug"]})
        if not dep_ok:
            raise HTTPException(400, f"departamento_slug '{update['departamento_slug']}' não encontrado.")

    # tipos numéricos
    if "carga_horaria" in update and update["carga_horaria"] is not None:
        update["carga_horaria"] = float(update["carga_horaria"])

    # 🔗 converter URLs para string
    for k in ("url", "url_plataforma", "thumbnail_url", "doc_url"):
        if k in update and update[k] is not None:
            update[k] = _url(update[k])

    update["atualizado_em"] = _now()

    res = await db["cursos"].update_one({"slug": _norm(slug)}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(404, "Curso não encontrado.")

    cur = await db["cursos"].find_one({"slug": update.get("slug", _norm(slug))})
    cur["_id"] = str(cur["_id"])
    return CursoRead(**cur)


@router.delete("/{slug}")
async def remover_curso(slug: str, db=Depends(get_db)):
    res = await db["cursos"].delete_one({"slug": _norm(slug)})
    if res.deleted_count == 0:
        raise HTTPException(404, "Curso não encontrado.")
    return {"ok": True}


@router.post("/bulk")
async def bulk_upsert(items: List[CursoBulkItem], db=Depends(get_db)):
    """
    Insere/atualiza cursos em lote. Slug único.
    """
    now = _now()
    # cache deps válidos p/ reduzir round-trips
    deps = {d["slug"] async for d in db["departamentos"].find({}, {"slug": 1})}

    for it in items:
        slug = _norm(it.slug)
        dep = _norm(it.departamento_slug)
        if not slug or not dep:
            raise HTTPException(400, "slug e departamento_slug são obrigatórios em cada item.")
        if dep not in deps:
            raise HTTPException(400, f"departamento_slug '{dep}' não encontrado (curso: '{slug}').")

        update = {
            "nome": it.nome,
            "slug": slug,
            "departamento_slug": dep,
            "carga_horaria": float(it.carga_horaria) if it.carga_horaria is not None else None,
            "pontos": it.pontos,
            "ativo": it.ativo,

            # 🔗 URLs convertidas para string
            "url": _url(it.url),
            "url_plataforma": _url(it.url_plataforma),
            "thumbnail_url": _url(it.thumbnail_url),
            "doc_url": _url(it.doc_url),

            "atualizado_em": now,
        }
        await db["cursos"].update_one(
            {"slug": slug},
            {"$set": update, "$setOnInsert": {"criado_em": now}},
            upsert=True
        )

    return {"ok": True, "count": len(items)}
