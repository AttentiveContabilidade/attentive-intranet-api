# app/models/comunicados.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ComunicadoBase(BaseModel):
    tipo: str = Field(..., description="Tipo do comunicado. Ex.: 'new_hire', 'alerta', 'geral'")
    titulo: str = Field(..., description="Título exibido no card do comunicado")
    conteudo: str = Field(..., description="Conteúdo em texto ou markdown")
    imagem: Optional[str] = Field(None, description="Imagem base64 ou URL pública")
    visibilidade: str = Field("public", description="Visibilidade: public, private ou departamento")
    tags: List[str] = Field(default_factory=list, description="Lista de tags do comunicado")
    status: str = Field("published", description="Status do comunicado: draft ou published")

class ComunicadoCreate(ComunicadoBase):
    autor_id: Optional[str] = Field(None, description="ID do usuário que criou o comunicado")
    target_user_id: Optional[str] = Field(None, description="ID do colaborador relacionado (ex.: novo contratado)")

class ComunicadoDB(ComunicadoBase):
    id: str
    autor_id: Optional[str]
    target_user_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # ✅ Pydantic v2
