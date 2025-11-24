from datetime import datetime
from typing import List, Optional, Dict, Any

from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
    Path,
    Header,
)
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.schemas.comunicados import ComunicadoCreate, ComunicadoPublic
from app.dependencies.db import get_db
from app.core.auth import decode_token

router = APIRouter(prefix="/comunicados", tags=["comunicados"])


# ---------- Utils ----------
def _to_object_id(value: Optional[str]) -> Optional[ObjectId]:
    if not value:
        return None
    if not ObjectId.is_valid(value):
        return None
    return ObjectId(value)


def _serialize(doc: Dict[str, Any]) -> ComunicadoPublic:
    conteudo_html = doc.get("conteudo_html") or doc.get("conteudo") or ""

    return ComunicadoPublic(
        id=str(doc["_id"]),
        titulo=doc.get("titulo", "Comunicado"),
        conteudo_html=conteudo_html,
        tipo=doc.get("tipo", "general"),
        imagem=doc.get("imagem") or doc.get("imagem_capa"),
        tags=doc.get("tags", []),
        autor_id=str(doc["autor_id"]) if doc.get("autor_id") else None,
        target_user_id=str(doc["target_user_id"]) if doc.get("target_user_id") else None,
        created_at=doc.get("created_at") or datetime.utcnow(),
        updated_at=doc.get("updated_at") or datetime.utcnow(),
        status=doc.get("status", "published"),
    )


# ---------- Dependência: usuário logado (opcional) ----------
async def get_current_user_optional(
    authorization: str = Header(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Optional[dict]:
    """
    Tenta identificar o usuário pelo Bearer token.
    Se não tiver token ou for inválido, retorna None.
    """

    if not authorization:
        return None

    token = authorization.replace("Bearer ", "")
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
    except Exception:
        return None

    try:
        oid = ObjectId(user_id)
    except Exception:
        return None

    user = await db["usuarios"].find_one({"_id": oid})
    if not user:
        return None

    return {
        "_id": str(user["_id"]),
        "nome": user.get("nome"),
        "sobrenome": user.get("sobrenome"),
        "avatar_url": user.get("avatar_url"),
        "departamento": user.get("departamento"),
    }


# ---------- Modelos auxiliares ----------
class UserMini(BaseModel):
    id: str
    nome: Optional[str] = None
    sobrenome: Optional[str] = None
    avatar_url: Optional[str] = None
    departamento: Optional[str] = None


class ComentarioOut(BaseModel):
    id: str
    texto: str
    autor_nome: str
    created_at: datetime


# 🔥 ATUALIZADO AQUI
class ComentarioCreate(BaseModel):
    texto: str
    autor_nome: Optional[str] = None
    autor_id: Optional[str] = None


class ComunicadoExpanded(ComunicadoPublic):
    autor: Optional[UserMini] = None
    target_user: Optional[UserMini] = None
    comentarios: List[ComentarioOut] = []


# ---------- Create ----------
@router.post(
    "",
    response_model=ComunicadoPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_comunicado(
    payload: ComunicadoCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    now = datetime.utcnow()
    payload_dict = payload.model_dump()

    raw_conteudo_html = payload_dict.get("conteudo_html")
    raw_conteudo = payload_dict.get("conteudo")

    if raw_conteudo_html:
        conteudo_final = raw_conteudo_html
    elif raw_conteudo:
        conteudo_final = raw_conteudo.replace("\n", "<br>")
    else:
        conteudo_final = ""

    autor_oid = _to_object_id(payload_dict.get("autor_id"))
    target_oid = _to_object_id(payload_dict.get("target_user_id"))

    doc: Dict[str, Any] = {
        "tipo": payload_dict.get("tipo", "general"),
        "titulo": payload_dict.get("titulo"),
        "conteudo_html": conteudo_final,
        "conteudo": raw_conteudo,
        "imagem": payload_dict.get("imagem") or payload_dict.get("imagem_capa"),
        "visibilidade": payload_dict.get("visibilidade", "public"),
        "tags": payload_dict.get("tags", []),
        "status": payload_dict.get("status", "published"),
        "autor_id": autor_oid,
        "target_user_id": target_oid,
        "created_at": now,
        "updated_at": now,
        "comentarios": [],
    }

    res = await db["comunicados"].insert_one(doc)
    saved = await db["comunicados"].find_one({"_id": res.inserted_id})
    return _serialize(saved)


# ---------- List (com expand) ----------
@router.get(
    "",
    response_model=List[ComunicadoExpanded],
)
async def list_comunicados(
    db: AsyncIOMotorDatabase = Depends(get_db),
    tipo: Optional[str] = Query(None),
    status_q: Optional[str] = Query("published", alias="status"),
    visibilidade: Optional[str] = Query(None),
    target_user_id: Optional[str] = Query(None),
    autor_id: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    expand: bool = Query(False),
):
    query: Dict[str, Any] = {}
    if tipo:
        query["tipo"] = tipo
    if status_q:
        query["status"] = status_q
    if visibilidade:
        query["visibilidade"] = visibilidade
    if target_user_id and ObjectId.is_valid(target_user_id):
        query["target_user_id"] = ObjectId(target_user_id)
    if autor_id and ObjectId.is_valid(autor_id):
        query["autor_id"] = ObjectId(autor_id)
    if q:
        regex = {"$regex": q, "$options": "i"}
        query["$or"] = [
            {"titulo": regex},
            {"conteudo": regex},
            {"conteudo_html": regex},
        ]

    # ---------- expand = False ----------
    if not expand:
        cursor = (
            db["comunicados"]
            .find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        out: List[ComunicadoExpanded] = []
        async for doc in cursor:
            base = _serialize(doc).model_dump()

            comentarios_raw = doc.get("comentarios", []) or []
            comentarios: List[ComentarioOut] = [
                ComentarioOut(
                    id=str(c.get("_id") or c.get("id") or ""),
                    texto=c.get("texto", ""),
                    autor_nome=c.get("autor_nome", "Colaborador"),
                    created_at=c.get("created_at") or datetime.utcnow(),
                )
                for c in comentarios_raw
            ]

            base["comentarios"] = comentarios
            out.append(ComunicadoExpanded(**base))
        return out

    # ---------- expand = True (lookup autor/target) ----------
    pipeline: List[Dict[str, Any]] = [
        {"$match": query},
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "usuarios",
                "localField": "autor_id",
                "foreignField": "_id",
                "as": "autor_arr",
                "pipeline": [
                    {
                        "$project": {
                            "_id": 1,
                            "nome": 1,
                            "sobrenome": 1,
                            "avatar_url": 1,
                            "departamento": 1,
                        }
                    }
                ],
            }
        },
        {"$addFields": {"autor": {"$first": "$autor_arr"}}},
        {"$unset": "autor_arr"},
        {
            "$lookup": {
                "from": "usuarios",
                "localField": "target_user_id",
                "foreignField": "_id",
                "as": "target_arr",
                "pipeline": [
                    {
                        "$project": {
                            "_id": 1,
                            "nome": 1,
                            "sobrenome": 1,
                            "avatar_url": 1,
                            "departamento": 1,
                        }
                    }
                ],
            }
        },
        {"$addFields": {"target_user": {"$first": "$target_arr"}}},
        {"$unset": "target_arr"},
    ]

    docs = await db["comunicados"].aggregate(pipeline).to_list(length=limit)

    out: List[ComunicadoExpanded] = []
    for d in docs:
        base = _serialize(d).model_dump()

        if d.get("autor"):
            base["autor"] = UserMini(
                id=str(d["autor"]["_id"]),
                nome=d["autor"].get("nome"),
                sobrenome=d["autor"].get("sobrenome"),
                avatar_url=d["autor"].get("avatar_url"),
                departamento=d["autor"].get("departamento"),
            )
        if d.get("target_user"):
            base["target_user"] = UserMini(
                id=str(d["target_user"]["_id"]),
                nome=d["target_user"].get("nome"),
                sobrenome=d["target_user"].get("sobrenome"),
                avatar_url=d["target_user"].get("avatar_url"),
                departamento=d["target_user"].get("departamento"),
            )

        comentarios_raw = d.get("comentarios", []) or []
        comentarios: List[ComentarioOut] = [
            ComentarioOut(
                id=str(c.get("_id") or c.get("id") or ""),
                texto=c.get("texto", ""),
                autor_nome=c.get("autor_nome", "Colaborador"),
                created_at=c.get("created_at") or datetime.utcnow(),
            )
            for c in comentarios_raw
        ]
        base["comentarios"] = comentarios

        out.append(ComunicadoExpanded(**base))

    return out


# ---------- GET by ID ----------
@router.get(
    "/{comunicado_id}",
    response_model=ComunicadoExpanded,
)
async def get_comunicado(
    comunicado_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    expand: bool = Query(False),
):
    if not ObjectId.is_valid(comunicado_id):
        raise HTTPException(status_code=400, detail="ID inválido")

    doc = await db["comunicados"].find_one({"_id": ObjectId(comunicado_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Comunicado não encontrado")

    base = _serialize(doc).model_dump()

    comentarios_raw = doc.get("comentarios", []) or []
    comentarios: List[ComentarioOut] = [
        ComentarioOut(
            id=str(c.get("_id") or c.get("id") or ""),
            texto=c.get("texto", ""),
            autor_nome=c.get("autor_nome", "Colaborador"),
            created_at=c.get("created_at") or datetime.utcnow(),
        )
        for c in comentarios_raw
    ]
    base["comentarios"] = comentarios

    return ComunicadoExpanded(**base)


# ---------- Patch status ----------
@router.patch(
    "/{comunicado_id}/status",
    response_model=ComunicadoPublic,
)
async def update_status(
    comunicado_id: str,
    new_status: str = Query(..., pattern="^(draft|published)$"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if not ObjectId.is_valid(comunicado_id):
        raise HTTPException(status_code=400, detail="ID inválido")

    now = datetime.utcnow()
    res = await db["comunicados"].find_one_and_update(
        {"_id": ObjectId(comunicado_id)},
        {"$set": {"status": new_status, "updated_at": now}},
        return_document=True,
    )

    if not res:
        raise HTTPException(status_code=404, detail="Comunicado não encontrado")

    return _serialize(res)


# ---------- COMENTÁRIOS (CORRIGIDO) ----------
@router.post(
    "/{comunicado_id}/comentarios",
    response_model=ComentarioOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_comentario(
    comunicado_id: str,
    payload: ComentarioCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    if not ObjectId.is_valid(comunicado_id):
        raise HTTPException(status_code=400, detail="ID inválido")

    texto = (payload.texto or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Texto do comentário vazio")

    comentario_id = ObjectId()
    now = datetime.utcnow()

    # ---------- autor_nome ----------
    autor_nome_payload = (payload.autor_nome or "").strip()
    if autor_nome_payload and autor_nome_payload.lower() != "colaborador":
        autor_nome = autor_nome_payload
    elif current_user:
        autor_nome = (
            f'{current_user.get("nome", "")} {current_user.get("sobrenome", "")}'
        ).strip() or "Colaborador"
    else:
        autor_nome = "Colaborador"

    # ---------- autor_id ----------
    autor_id = None

    if payload.autor_id and ObjectId.is_valid(payload.autor_id):
        autor_id = ObjectId(payload.autor_id)
    elif current_user and current_user.get("_id") and ObjectId.is_valid(current_user["_id"]):
        autor_id = ObjectId(current_user["_id"])

    comentario_doc = {
        "_id": comentario_id,
        "texto": texto,
        "autor_id": autor_id,
        "autor_nome": autor_nome,
        "created_at": now,
    }

    res = await db["comunicados"].update_one(
        {"_id": ObjectId(comunicado_id)},
        {"$push": {"comentarios": comentario_doc}},
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Comunicado não encontrado")

    return ComentarioOut(
        id=str(comentario_id),
        texto=texto,
        autor_nome=autor_nome,
        created_at=now,
    )
