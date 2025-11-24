from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate
from app.core.security import hash_password

async def list_usuarios(db: AsyncSession, page: int = 1, limit: int = 10):
    offset = (page - 1) * limit
    result = await db.execute(
        select(Usuario).order_by(Usuario.id).limit(limit).offset(offset)
    )
    items = [row for (row,) in result.all()]
    total = (await db.execute(select(func.count()).select_from(Usuario))).scalar_one()
    return {"items": items, "page": page, "limit": limit, "total": total}

async def get_usuario(db: AsyncSession, usuario_id: int) -> Usuario:
    obj = await db.get(Usuario, usuario_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return obj

async def _email_em_uso(db: AsyncSession, email: str, ignore_id: int | None = None) -> bool:
    q = select(Usuario).where(Usuario.email == email)
    if ignore_id is not None:
        from sqlalchemy import and_
        q = select(Usuario).where(and_(Usuario.email == email, Usuario.id != ignore_id))
    return (await db.execute(q)).scalar_one_or_none() is not None

async def create_usuario(db: AsyncSession, data: UsuarioCreate) -> Usuario:
    if await _email_em_uso(db, data.email):
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")
    obj = Usuario(
        nome=data.nome,
        sobrenome=data.sobrenome,
        departamento=data.departamento,
        email=data.email,
        senha=hash_password(data.senha) if data.senha else None,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def update_usuario(db: AsyncSession, usuario_id: int, data: UsuarioUpdate) -> Usuario:
    obj = await get_usuario(db, usuario_id)
    if data.email and await _email_em_uso(db, data.email, ignore_id=usuario_id):
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")

    if data.nome is not None: obj.nome = data.nome
    if data.sobrenome is not None: obj.sobrenome = data.sobrenome
    if data.departamento is not None: obj.departamento = data.departamento
    if data.email is not None: obj.email = data.email
    if data.senha: obj.senha = hash_password(data.senha)

    await db.commit()
    await db.refresh(obj)
    return obj

async def delete_usuario(db: AsyncSession, usuario_id: int) -> None:
    obj = await get_usuario(db, usuario_id)
    await db.delete(obj)
    await db.commit()
