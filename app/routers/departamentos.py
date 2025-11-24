# app/routers/departamentos.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from datetime import datetime, timezone

from app.schemas.departamento import (
    DepartamentoCreate,
    DepartamentoRead,
    DepartamentoUpdate,
    DepartamentoBulkItem,
)

# Usa o mesmo get_db do projeto
from app.dependencies.db import get_db

router = APIRouter(prefix="/departamentos", tags=["Departamentos"])


# ---------------------------
# Helpers
# ---------------------------
def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()

def _norm_slug(s: str | None) -> str | None:
    if s is None:
        return None
    return s.strip().lower()

def _stringify_ids(doc: dict | None) -> dict | None:
    """Converte ObjectIds para str ao devolver pro cliente."""
    if not doc:
        return doc
    if doc.get("_id"):
        doc["_id"] = str(doc["_id"])
    if doc.get("parent_id"):
        doc["parent_id"] = str(doc["parent_id"])
    return doc


# ---------------------------
# CRUD
# ---------------------------
@router.post("", response_model=DepartamentoRead)
async def criar_departamento(payload: DepartamentoCreate, db=Depends(get_db)):
    now = _now_iso()

    parent_doc = None
    parent_slug_norm = _norm_slug(payload.parent_slug)
    if parent_slug_norm:
        parent_doc = await db["departamentos"].find_one({"slug": parent_slug_norm})
        if not parent_doc:
            raise HTTPException(
                status_code=400,
                detail=f"parent_slug '{payload.parent_slug}' não encontrado."
            )

    slug_norm = _norm_slug(payload.slug)
    if not slug_norm:
        raise HTTPException(status_code=400, detail="slug é obrigatório.")

    exists = await db["departamentos"].find_one({"slug": slug_norm})
    if exists:
        raise HTTPException(status_code=409, detail=f"slug '{slug_norm}' já existe.")

    # path (nomes) e path_slugs (slugs) para consulta
    path_names = (parent_doc.get("path", []) if parent_doc else []) + [payload.nome]
    path_slugs = (parent_doc.get("path_slugs", []) if parent_doc else []) + [slug_norm]

    doc = {
        "nome": payload.nome,
        "slug": slug_norm,
        "parent_slug": parent_slug_norm,
        "parent_id": parent_doc["_id"] if parent_doc else None,
        "path": path_names,
        "path_slugs": path_slugs,
        "ordem": payload.ordem,
        "ativo": payload.ativo,
        "criado_em": now,
        "atualizado_em": now,
    }

    res = await db["departamentos"].insert_one(doc)
    created = await db["departamentos"].find_one({"_id": res.inserted_id})
    return DepartamentoRead(**_stringify_ids(created))


@router.get("", response_model=List[DepartamentoRead])
async def listar_departamentos(db=Depends(get_db)):
    cursor = db["departamentos"].find().sort("ordem", 1)
    items = [d async for d in cursor]
    items = [_stringify_ids(d) for d in items]
    return [DepartamentoRead(**d) for d in items]


@router.get("/{slug}", response_model=DepartamentoRead)
async def obter_departamento(slug: str, db=Depends(get_db)):
    doc = await db["departamentos"].find_one({"slug": _norm_slug(slug)})
    if not doc:
        raise HTTPException(status_code=404, detail="Departamento não encontrado.")
    return DepartamentoRead(**_stringify_ids(doc))


@router.put("/{slug}", response_model=DepartamentoRead)
async def atualizar_departamento(slug: str, data: DepartamentoUpdate, db=Depends(get_db)):
    slug_norm = _norm_slug(slug)
    update = data.model_dump(exclude_unset=True)
    now = _now_iso()
    update["atualizado_em"] = now

    # normaliza slugs caso venham no update
    if "slug" in update and update["slug"] is not None:
        update["slug"] = _norm_slug(update["slug"])
    if "parent_slug" in update:
        update["parent_slug"] = _norm_slug(update["parent_slug"])

    # Recalcular path/path_slugs/parent_id se necessário
    if "parent_slug" in update or "nome" in update or "slug" in update:
        current = await db["departamentos"].find_one({"slug": slug_norm})
        if not current:
            raise HTTPException(status_code=404, detail="Departamento não encontrado.")

        new_nome = update.get("nome", current["nome"])
        new_slug = update.get("slug", current["slug"])
        new_parent_slug = update.get("parent_slug", current.get("parent_slug"))

        parent = None
        if new_parent_slug:
            parent = await db["departamentos"].find_one({"slug": new_parent_slug})
            if not parent:
                raise HTTPException(
                    status_code=400,
                    detail=f"parent_slug '{new_parent_slug}' não encontrado."
                )

        update["parent_id"] = parent["_id"] if parent else None
        update["path"] = (parent.get("path", []) if parent else []) + [new_nome]
        update["path_slugs"] = (parent.get("path_slugs", []) if parent else []) + [new_slug]

    res = await db["departamentos"].update_one(
        {"slug": slug_norm},
        {"$set": update},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Departamento não encontrado.")

    # se slug mudou, usa o novo para buscar
    final_slug = update.get("slug", slug_norm)
    doc = await db["departamentos"].find_one({"slug": final_slug})
    return DepartamentoRead(**_stringify_ids(doc))


@router.delete("/{slug}")
async def remover_departamento(slug: str, db=Depends(get_db)):
    res = await db["departamentos"].delete_one({"slug": _norm_slug(slug)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Departamento não encontrado.")
    return {"ok": True}


# ---------------------------
# BULK (upsert + hierarquia)
# ---------------------------
@router.post("/bulk")
async def bulk_upsert_departamentos(items: List[DepartamentoBulkItem], db=Depends(get_db)):
    """
    Upsert em lote respeitando hierarquia.
    - Usa slug (minúsculo) como chave única.
    - parent_slug deve existir ou vir antes no array.
    - Mantém path (nomes) e path_slugs (slugs) coerentes.
    - Tolerante a documentos antigos sem 'slug' (ignora no cache).
    """
    now = _now_iso()

    # Cache de existentes (só com slug válido)
    existing: Dict[str, dict] = {}
    cursor = db["departamentos"].find(
        {"slug": {"$exists": True, "$ne": None}},
        {"slug": 1, "nome": 1, "path": 1, "path_slugs": 1}
    )
    async for d in cursor:
        slug = d.get("slug")
        if not slug:
            continue
        existing[slug] = d

    async def ensure_node(item: DepartamentoBulkItem) -> dict:
        slug_norm = _norm_slug(item.slug)
        if not slug_norm:
            raise HTTPException(status_code=400, detail="slug é obrigatório em cada item.")
        parent_slug_norm = _norm_slug(item.parent_slug)

        parent = None
        if parent_slug_norm:
            parent = existing.get(parent_slug_norm)
            if not parent:
                raise HTTPException(
                    status_code=400,
                    detail=f"parent_slug '{parent_slug_norm}' não encontrado para '{slug_norm}'"
                )

        path_names = (parent.get("path", []) if parent else []) + [item.nome]
        path_slugs = (parent.get("path_slugs", []) if parent else []) + [slug_norm]

        update = {
            "nome": item.nome,
            "slug": slug_norm,
            "parent_slug": parent_slug_norm,
            "parent_id": parent["_id"] if parent else None,
            "path": path_names,
            "path_slugs": path_slugs,
            "ordem": item.ordem,
            "ativo": item.ativo,
            "atualizado_em": now,
        }

        await db["departamentos"].update_one(
            {"slug": slug_norm},
            {"$set": update, "$setOnInsert": {"criado_em": now}},
            upsert=True,
        )
        doc = await db["departamentos"].find_one({"slug": slug_norm})
        existing[slug_norm] = doc
        return doc

    # Raízes primeiro
    roots = [i for i in items if not i.parent_slug]
    for it in roots:
        await ensure_node(it)

    # Filhos – resolve em rounds enquanto os pais forem aparecendo
    children = [i for i in items if i.parent_slug]
    remaining = children[:]
    safety = 0
    while remaining and safety < 10000:
        safety += 1
        next_round = []
        for it in remaining:
            parent_slug_norm = _norm_slug(it.parent_slug)
            if parent_slug_norm and existing.get(parent_slug_norm):
                await ensure_node(it)
            else:
                next_round.append(it)
        if len(next_round) == len(remaining):
            pending = ", ".join([i.slug for i in next_round])
            raise HTTPException(status_code=400, detail=f"Pais não resolvidos para: {pending}")
        remaining = next_round

    return {"ok": True, "count": len(items)}
