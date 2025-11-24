# app/schemas/curso.py
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl
from app.schemas.common import MongoModel

class CursoBase(BaseModel):
    nome: str = Field(..., examples=["Planejamento Tributário na Prática"])
    slug: str = Field(..., examples=["planejamento-tributario"])
    departamento_slug: str = Field(..., examples=["tax"])  # referência a departamentos.slug

    carga_horaria: Optional[float] = Field(None, examples=[8.0])
    pontos: int = Field(10, ge=0, examples=[10])
    ativo: bool = True

    # 🔗 Novos campos de URLs
    url: Optional[HttpUrl] = Field(None, examples=["https://plataforma.com/curso/planejamento-tributario"])
    url_plataforma: Optional[HttpUrl] = Field(None, examples=["https://plataforma.com"])
    thumbnail_url: Optional[HttpUrl] = Field(None, examples=["https://cdn.plataforma.com/thumbs/curso123.jpg"])
    doc_url: Optional[HttpUrl] = Field(None, examples=["https://plataforma.com/curso/planejamento-tributario/syllabus"])

class CursoCreate(CursoBase):
    pass

class CursoUpdate(BaseModel):
    nome: Optional[str] = None
    slug: Optional[str] = None
    departamento_slug: Optional[str] = None
    carga_horaria: Optional[float] = None
    pontos: Optional[int] = Field(None, ge=0)
    ativo: Optional[bool] = None

    # 🔗 URLs (todas opcionais)
    url: Optional[HttpUrl] = None
    url_plataforma: Optional[HttpUrl] = None
    thumbnail_url: Optional[HttpUrl] = None
    doc_url: Optional[HttpUrl] = None

class CursoRead(MongoModel, CursoBase):
    pass

class CursoBulkItem(CursoBase):
    # Mesmo shape do create para facilitar /bulk
    pass
