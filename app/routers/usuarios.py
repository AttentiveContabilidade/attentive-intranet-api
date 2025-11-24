# app/routers/usuarios.py
import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel
from bson import ObjectId

from app.schemas.usuario import (
    UsuarioCreate,
    UsuarioRead,
    UsuarioUpdate,
    FeedbackItem,
    CursoItem,
)
from app.dependencies.db import get_db
from app.utils.ids import to_oid
from app.utils.security import hash_password


router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

POINTS_PER_COURSE = 10

# limite de segurança para o tamanho da string da imagem (base64)
# ~8 MB de texto já é mais do que suficiente para um avatar
MAX_AVATAR_BYTES = 8_000_000


# ======================================================
# Função para converter texto simples → HTML formatado
# ======================================================
def convert_welcome_notes_to_html(text: Optional[str]) -> str:
    if not text:
        return ""

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Se todas as linhas começam com bullet, vira <ul>
    if all(l.startswith(("•", "-", "*")) for l in lines):
        items = "".join(f"<li>{l[1:].strip()}</li>" for l in lines)
        return f"<ul>{items}</ul>"

    # Caso contrário, apenas troca \n por <br>
    return "<br>".join(lines)


# ======================================================
# Payloads auxiliares
# ======================================================
class AvatarUpdate(BaseModel):
    avatar_url: str


class DescricaoUpdate(BaseModel):
    descricao_html: str


class FeedbackCreate(BaseModel):
    msg: str
    autor: Optional[str] = None


class ToggleCursoPayload(BaseModel):
    nome: Optional[str] = None


# ======================================================
# CRIAÇÃO DE USUÁRIO
# ======================================================
@router.post("", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
async def criar_usuario(data: UsuarioCreate, db=Depends(get_db)):

    # Verificar se email está em uso
    existing = await db["usuarios"].find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")

    doc = data.model_dump()

    # Campos opcionais de onboarding
    welcome_notes = doc.pop("welcome_notes", None)
    welcome_photo = doc.pop("welcome_photo", None)

    # Se o RH não mandar manualmente uma foto → usa avatar
    avatar_url = doc.get("avatar_url")

    # 🔒 Checagem de tamanho da imagem (avatar/welcome_photo)
    if avatar_url and isinstance(avatar_url, str):
        # len() já é um bom proxy do tamanho do base64
        if len(avatar_url) > MAX_AVATAR_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(
                    "Imagem do avatar muito grande. "
                    "Por favor, envie uma foto menor (reduza resolução ou tamanho do arquivo)."
                ),
            )

    if not welcome_photo:
        welcome_photo = avatar_url

    # bio_publica recebe o mesmo texto das notas de boas-vindas
    if welcome_notes:
        doc["bio_publica"] = welcome_notes

    # Preparar senha
    senha = doc.pop("senha", None)
    if senha:
        doc["senha_hash"] = hash_password(senha)

    now_iso = datetime.now(tz=timezone.utc).isoformat()
    doc["criado_em"] = now_iso
    doc["atualizado_em"] = now_iso

    # Inserir novo usuário
    res = await db["usuarios"].insert_one(doc)

    # ======================================================
    # COMUNICADO AUTOMÁTICO DE BOAS-VINDAS
    # ======================================================
    try:
        system_author_id = os.getenv("ATTENTIVE_SYSTEM_USER_ID")

        autor_oid = (
            ObjectId(system_author_id)
            if system_author_id and ObjectId.is_valid(system_author_id)
            else None
        )

        comunicado_doc = {
            "tipo": "new_hire",
            "titulo": f"Bem-vindo(a), {doc.get('nome', 'novo(a) colaborador(a)')}!",

            # HTML já formatado para o front
            "conteudo_html": convert_welcome_notes_to_html(welcome_notes),

            "imagem": welcome_photo,
            "visibilidade": "public",
            "tags": ["new_hire", "boas_vindas"],
            "status": "published",

            "autor_id": autor_oid,
            "target_user_id": res.inserted_id,

            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        await db["comunicados"].insert_one(comunicado_doc)

    except Exception as e:
        print("[usuarios] Falha ao criar comunicado new_hire:", e)

    # Retorna o usuário criado
    created = await db["usuarios"].find_one(
        {"_id": res.inserted_id},
        {"senha": 0, "senha_hash": 0}
    )
    return UsuarioRead(**created)


# ======================================================
# LISTAR / PEGAR USUÁRIOS
# ======================================================
@router.get("", response_model=List[UsuarioRead])
async def listar_usuarios(skip: int = 0, limit: int = 50, db=Depends(get_db)):
    cursor = (
        db["usuarios"]
        .find({}, {"senha": 0, "senha_hash": 0})
        .skip(skip)
        .limit(limit)
        .sort("_id", -1)
    )
    docs = [UsuarioRead(**d) async for d in cursor]
    return docs


@router.get("/{usuario_id}", response_model=UsuarioRead)
async def obter_usuario(usuario_id: str, db=Depends(get_db)):
    oid = to_oid(usuario_id)
    doc = await db["usuarios"].find_one(
        {"_id": oid}, {"senha": 0, "senha_hash": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return UsuarioRead(**doc)


# ======================================================
# ATUALIZAÇÃO DE USUÁRIOS
# ======================================================
@router.put("/{usuario_id}", response_model=UsuarioRead)
async def atualizar_usuario(usuario_id: str, data: UsuarioUpdate, db=Depends(get_db)):
    oid = to_oid(usuario_id)
    update = data.model_dump(exclude_unset=True)

    if "senha" in update and update["senha"]:
        update["senha_hash"] = hash_password(update.pop("senha"))

    update["atualizado_em"] = datetime.now(tz=timezone.utc).isoformat()

    res = await db["usuarios"].update_one({"_id": oid}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    doc = await db["usuarios"].find_one(
        {"_id": oid}, {"senha": 0, "senha_hash": 0}
    )
    return UsuarioRead(**doc)


# ======================================================
# DELETAR
# ======================================================
@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_usuario(usuario_id: str, db=Depends(get_db)):
    oid = to_oid(usuario_id)
    res = await db["usuarios"].delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return None


# ======================================================
# PERFIL — avatar, descrição, feedbacks, cursos
# ======================================================
@router.post("/{usuario_id}/avatar", response_model=UsuarioRead)
async def atualizar_avatar(usuario_id: str, payload: AvatarUpdate, db=Depends(get_db)):
    oid = to_oid(usuario_id)

    # Mesmo limite de tamanho quando atualizar avatar
    if payload.avatar_url and len(payload.avatar_url) > MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                "Imagem do avatar muito grande. "
                "Por favor, envie uma foto menor (reduza resolução ou tamanho do arquivo)."
            ),
        )

    update = {
        "avatar_url": payload.avatar_url,
        "atualizado_em": datetime.now(tz=timezone.utc).isoformat()
    }
    res = await db["usuarios"].update_one({"_id": oid}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    doc = await db["usuarios"].find_one(
        {"_id": oid}, {"senha": 0, "senha_hash": 0}
    )
    return UsuarioRead(**doc)


@router.post("/{usuario_id}/descricao", response_model=UsuarioRead)
async def atualizar_descricao(usuario_id: str, payload: DescricaoUpdate, db=Depends(get_db)):
    oid = to_oid(usuario_id)
    update = {
        "descricao_html": payload.descricao_html,
        "atualizado_em": datetime.now(tz=timezone.utc).isoformat()
    }
    res = await db["usuarios"].update_one({"_id": oid}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    doc = await db["usuarios"].find_one(
        {"_id": oid}, {"senha": 0, "senha_hash": 0}
    )
    return UsuarioRead(**doc)


@router.post("/{usuario_id}/feedbacks", response_model=UsuarioRead)
async def adicionar_feedback(usuario_id: str, payload: FeedbackCreate, db=Depends(get_db)):
    oid = to_oid(usuario_id)
    feedback = FeedbackItem(
        msg=payload.msg,
        autor=payload.autor,
        data=datetime.now(tz=timezone.utc).isoformat()
    ).model_dump()

    res = await db["usuarios"].update_one(
        {"_id": oid},
        {
            "$push": {"feedbacks": {"$each": [feedback], "$position": 0}},
            "$set": {"atualizado_em": datetime.now(tz=timezone.utc).isoformat()}
        },
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    doc = await db["usuarios"].find_one(
        {"_id": oid}, {"senha": 0, "senha_hash": 0}
    )
    return UsuarioRead(**doc)


@router.post("/{usuario_id}/cursos/{curso_id}/toggle", response_model=UsuarioRead)
async def toggle_curso(usuario_id: str, curso_id: str, payload: ToggleCursoPayload = Body(default=None), db=Depends(get_db)):
    oid = to_oid(usuario_id)
    user = await db["usuarios"].find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    cursos_prog = user.get("cursos_progresso", []) or []
    idx = next((i for i, c in enumerate(cursos_prog) if c.get("curso_id") == curso_id), None)
    now_iso = datetime.now(tz=timezone.utc).isoformat()

    if idx is None:
        new_item = CursoItem(
            curso_id=curso_id,
            nome=payload.nome if payload and payload.nome else None,
            concluido=True,
            concluido_em=now_iso,
        ).model_dump()
        cursos_prog.append(new_item)
    else:
        current = cursos_prog[idx]
        new_state = not bool(current.get("concluido"))
        current["concluido"] = new_state
        current["concluido_em"] = now_iso if new_state else None
        if payload and payload.nome:
            current["nome"] = payload.nome
        cursos_prog[idx] = current

    concluidos = sum(1 for c in cursos_prog if c.get("concluido"))
    pontos = concluidos * POINTS_PER_COURSE

    update = {
        "cursos_progresso": cursos_prog,
        "pontos": pontos,
        "atualizado_em": now_iso,
    }

    await db["usuarios"].update_one({"_id": oid}, {"$set": update})

    doc = await db["usuarios"].find_one(
        {"_id": oid}, {"senha": 0, "senha_hash": 0}
    )
    return UsuarioRead(**doc)
