from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re
from typing import List

_only_digits = re.compile(r"\D+")

def _normalize_cnpj(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = _only_digits.sub("", value)
    if len(v) != 14:
        raise ValueError("CNPJ deve ter 14 dígitos")
    return v

class EscrituracaoBase(BaseModel):
    cod_empresa: Optional[str] = Field(default=None, description="Código interno da empresa")
    nome_razao_social: str = Field(..., description="Razão social")
    cnpj: str = Field(..., description="CNPJ da empresa")
    login: Optional[str] = Field(default=None, description="Login para o sistema externo")
    senha: Optional[str] = Field(default=None, description="Senha para o sistema externo (não retorna em responses)")

    @field_validator("cnpj")
    @classmethod
    def normalize_cnpj(cls, v: str) -> str:
        return _normalize_cnpj(v)  # valida e normaliza para só dígitos

class EscrituracaoCreate(EscrituracaoBase):
    """Payload de criação (via Swagger)."""
    pass

class EscrituracaoUpdate(BaseModel):
    """Payload de atualização parcial."""
    cod_empresa: Optional[str] = None
    nome_razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    login: Optional[str] = None
    senha: Optional[str] = None

    @field_validator("cnpj")
    @classmethod
    def normalize_cnpj_update(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_cnpj(v)

class EscrituracaoRead(BaseModel):
    """Resposta (não expõe senha)."""
    id: str
    cod_empresa: Optional[str] = None
    nome_razao_social: str
    cnpj: str
    login: Optional[str] = None



class EscrituracaoCreateBulk(BaseModel):
    """Payload para inserção em lote."""
    items: List[EscrituracaoCreate]
    skip_duplicates: bool = True  # ignora CNPJs já existentes (default)

class EscrituracaoBulkResult(BaseModel):
    """Resposta da inserção em lote."""
    inserted: int
    inserted_ids: List[str] = []
    skipped: List[str] = []   # CNPJs ignorados por duplicidade
    errors: List[str] = []    # mensagens de erro por item
