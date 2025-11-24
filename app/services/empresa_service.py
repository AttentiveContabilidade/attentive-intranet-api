from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from fastapi import HTTPException, status
from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate

async def list_empresas(db: AsyncSession, page: int = 1, limit: int = 10):
    offset = (page - 1) * limit
    result = await db.execute(
        select(Empresa).order_by(Empresa.id).limit(limit).offset(offset)
    )
    items = [row for (row,) in result.all()]
    total = (await db.execute(select(func.count()).select_from(Empresa))).scalar_one()
    return {"items": items, "page": page, "limit": limit, "total": total}

async def get_empresa(db: AsyncSession, empresa_id: int) -> Empresa:
    obj = await db.get(Empresa, empresa_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    return obj

async def _cnpj_em_uso(db: AsyncSession, cnpj: str, ignore_id: int | None = None) -> bool:
    q = select(Empresa).where(Empresa.cnpj == cnpj)
    if ignore_id is not None:
        q = select(Empresa).where(and_(Empresa.cnpj == cnpj, Empresa.id != ignore_id))
    return (await db.execute(q)).scalar_one_or_none() is not None

async def create_empresa(db: AsyncSession, data: EmpresaCreate) -> Empresa:
    if await _cnpj_em_uso(db, data.cnpj):
        raise HTTPException(status_code=409, detail="CNPJ já cadastrado")
    obj = Empresa(
        cod_empresa=data.cod_empresa,
        nome_razao_social=data.nome_razao_social,
        cnpj=data.cnpj,
        inscricao_municipal=data.inscricao_municipal,
        inscricao_estadual=data.inscricao_estadual,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def update_empresa(db: AsyncSession, empresa_id: int, data: EmpresaUpdate) -> Empresa:
    obj = await get_empresa(db, empresa_id)

    if data.cnpj and await _cnpj_em_uso(db, data.cnpj, ignore_id=empresa_id):
        raise HTTPException(status_code=409, detail="CNPJ já cadastrado")

    if data.cod_empresa is not None: obj.cod_empresa = data.cod_empresa
    if data.nome_razao_social is not None: obj.nome_razao_social = data.nome_razao_social
    if data.cnpj is not None: obj.cnpj = data.cnpj
    if data.inscricao_municipal is not None: obj.inscricao_municipal = data.inscricao_municipal
    if data.inscricao_estadual is not None: obj.inscricao_estadual = data.inscricao_estadual

    await db.commit()
    await db.refresh(obj)
    return obj

async def delete_empresa(db: AsyncSession, empresa_id: int) -> None:
    obj = await get_empresa(db, empresa_id)
    await db.delete(obj)
    await db.commit()
