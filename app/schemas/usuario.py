# app/schemas/usuario.py
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.schemas.common import MongoModel


# ==========================================================
# Subschemas
# ==========================================================

class CursoItem(BaseModel):
    curso_id: str
    nome: Optional[str] = None
    concluido: bool = False
    concluido_em: Optional[str] = None  # formato ISO


class FeedbackItem(BaseModel):
    msg: str
    data: Optional[str] = None  # ISO string
    autor: Optional[str] = None


# ==========================================================
# Schemas principais
# ==========================================================

class UsuarioBase(BaseModel):
    nome: str
    sobrenome: str
    email: EmailStr
    departamento: Optional[str] = None

    # Perfil
    avatar_url: Optional[str] = None          # base64 ou URL pública
    descricao_html: Optional[str] = None      # texto com formatação (restrito a admins na resposta)
    bio_publica: Optional[str] = None         # texto público (exibe no perfil/board)

    # Gamificação / sociais
    pontos: int = 0
    feedbacks: List[FeedbackItem] = Field(default_factory=list)
    cursos_progresso: List[CursoItem] = Field(default_factory=list)

    ativo: bool = True
    roles: List[str] = Field(default_factory=lambda: ["colaborador"])


class UsuarioCreate(UsuarioBase):
    # senha NÃO é obrigatória (compatível com fluxo atual)
    senha: Optional[str] = None

    # 👇 Novos campos opcionais para onboarding/boas-vindas
    # Se vierem, o router de usuários:
    #   - copia welcome_notes -> bio_publica
    #   - cria um comunicado new_hire com (conteudo=welcome_notes, imagem=welcome_photo)
    welcome_notes: Optional[str] = None
    welcome_photo: Optional[str] = None


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    sobrenome: Optional[str] = None
    email: Optional[EmailStr] = None
    departamento: Optional[str] = None
    senha: Optional[str] = None

    avatar_url: Optional[str] = None
    descricao_html: Optional[str] = None
    bio_publica: Optional[str] = None

    pontos: Optional[int] = None
    feedbacks: Optional[List[FeedbackItem]] = None
    cursos_progresso: Optional[List[CursoItem]] = None
    ativo: Optional[bool] = None
    roles: Optional[List[str]] = None


class UsuarioRead(MongoModel):
    nome: str
    sobrenome: str
    email: EmailStr
    departamento: Optional[str] = None

    avatar_url: Optional[str] = None
    descricao_html: Optional[str] = None  # ⚠️ se for privado p/ não-admin, filtre no router
    bio_publica: Optional[str] = None

    pontos: int = 0
    feedbacks: List[FeedbackItem] = Field(default_factory=list)
    cursos_progresso: List[CursoItem] = Field(default_factory=list)
    ativo: bool = True
    roles: List[str] = Field(default_factory=lambda: ["colaborador"])
