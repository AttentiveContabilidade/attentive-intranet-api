# app/schemas/departamento.py
from typing import Optional, List
from pydantic import BaseModel
from app.schemas.common import MongoModel


class DepartamentoBase(BaseModel):
    nome: str
    slug: str                           # único e estável (ex.: "fiscal", "contabil")
    parent_slug: Optional[str] = None   # usado para montar hierarquia no bulk
    parent_id: Optional[str] = None     # ObjectId em string quando retornado
    path: Optional[List[str]] = None    # ["Attentive", "Fiscal", ...]
    ordem: int = 0
    ativo: bool = True


class DepartamentoCreate(DepartamentoBase):
    pass


class DepartamentoUpdate(BaseModel):
    nome: Optional[str] = None
    slug: Optional[str] = None
    parent_slug: Optional[str] = None
    parent_id: Optional[str] = None
    path: Optional[List[str]] = None
    ordem: Optional[int] = None
    ativo: Optional[bool] = None


class DepartamentoRead(MongoModel):
    nome: str
    slug: str
    parent_slug: Optional[str]
    parent_id: Optional[str]
    path: Optional[List[str]]
    ordem: int
    ativo: bool


# ---- Bulk ----
class DepartamentoBulkItem(BaseModel):
    nome: str
    slug: str                           # único
    parent_slug: Optional[str] = None   # referencia o slug do pai
    ordem: int = 0
    ativo: bool = True
