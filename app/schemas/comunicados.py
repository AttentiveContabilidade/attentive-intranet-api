from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


# ---------------------------------------------------------
# Lista oficial de tipos aceitos pelos comunicados
# ---------------------------------------------------------
TIPOS_COMUNICADO = [
    "general",
    "highlight",
    "mural",
    "congrats",
    "farewell",
    "new_hire",
]


# ---------------------------------------------------------
# Base para criação e atualização
# ---------------------------------------------------------
class ComunicadoBase(BaseModel):
    titulo: str = Field(..., min_length=1)

    # HTML rico vindo do Quill
    conteudo_html: Optional[str] = Field(
        None,
        description="Conteúdo HTML do comunicado (Quill)."
    )

    # compatibilidade com versões anteriores (texto simples)
    conteudo: Optional[str] = Field(
        None,
        description="Campo legado (conteúdo em texto simples)."
    )

    tipo: str = Field(
        "general",
        description=f"Tipo do comunicado. Valores possíveis: {', '.join(TIPOS_COMUNICADO)}"
    )

    # imagem principal / capa
    imagem: Optional[str] = Field(
        None,
        description="URL da imagem do comunicado ou foto de boas-vindas"
    )

    tags: List[str] = Field(default_factory=list)
    visibilidade: str = Field("public")
    status: str = Field("published")

    # -----------------------------
    # Normalização automática
    # -----------------------------
    @field_validator("tipo")
    def validar_tipo(cls, v):
        if v not in TIPOS_COMUNICADO:
            raise ValueError(f"Tipo inválido. Use um de: {', '.join(TIPOS_COMUNICADO)}")
        return v


# ---------------------------------------------------------
# Para criação (POST)
# ---------------------------------------------------------
class ComunicadoCreate(ComunicadoBase):
    pass


# ---------------------------------------------------------
# Para atualização (PUT/PATCH)
# ---------------------------------------------------------
class ComunicadoUpdate(BaseModel):
    titulo: Optional[str] = None
    conteudo_html: Optional[str] = None
    conteudo: Optional[str] = None
    tipo: Optional[str] = None
    imagem: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = Field(None, description="published, draft, hidden")


# ---------------------------------------------------------
# Modelo armazenado no banco
# ---------------------------------------------------------
class ComunicadoInDB(ComunicadoBase):
    id: str
    autor_id: Optional[str] = None
    target_user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------
# Modelo enviado ao front (expand)
# ---------------------------------------------------------
class ComunicadoPublic(BaseModel):
    id: str
    titulo: str
    conteudo_html: str
    tipo: str
    imagem: Optional[str]
    tags: List[str]
    autor_id: Optional[str]
    target_user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    status: str

    class Config:
        from_attributes = True
