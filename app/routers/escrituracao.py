from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.schemas.escrituracao import (
    EscrituracaoCreate, EscrituracaoRead, EscrituracaoUpdate,
    EscrituracaoCreateBulk, EscrituracaoBulkResult
)
from app.services import escrituracao_service as svc

router = APIRouter(prefix="/escrituracao", tags=["Escrituracao"])

@router.post("", response_model=EscrituracaoRead, status_code=201)
def create_escrituracao(body: EscrituracaoCreate):
    try:
        return svc.create(body)
    except Exception as e:
        # provavelmente violação de unique cnpj
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[EscrituracaoRead])
def list_escrituracao(skip: int = 0, limit: int = Query(50, le=200)):
    return svc.list_many(skip=skip, limit=limit)

@router.get("/{id}", response_model=EscrituracaoRead)
def get_escrituracao(id: str):
    item = svc.get_by_id(id)
    if not item:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return item

@router.get("/cnpj/{cnpj}", response_model=EscrituracaoRead)
def get_by_cnpj(cnpj: str):
    item = svc.get_by_cnpj(cnpj)
    if not item:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return item

@router.patch("/{id}", response_model=EscrituracaoRead)
def update_escrituracao(id: str, body: EscrituracaoUpdate):
    item = svc.update(id, body)
    if not item:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return item

@router.delete("/{id}", status_code=204)
def delete_escrituracao(id: str):
    ok = svc.delete(id)
    if not ok:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    

@router.post("/bulk", response_model=EscrituracaoBulkResult, summary="Create Bulk")
def create_escrituracao_bulk(body: EscrituracaoCreateBulk):
    return svc.create_bulk(body)
