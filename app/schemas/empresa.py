from typing import Optional
from pydantic import BaseModel, field_validator
from app.schemas.common import MongoModel
import re

_only_digits = re.compile(r"\D+")

# ----------------- Base (campos comuns) -----------------
class EmpresaBase(BaseModel):
    cod_empresa: Optional[str] = None
    nome_razao_social: str
    cnpj: str
    municipio: Optional[str] = None
    uf: Optional[str] = None
    inscricao_municipal: str
    inscricao_estadual: str
    login_muni: Optional[str] = None
    senha_muni: Optional[str] = None
    login_est: Optional[str] = None
    senha_est: Optional[str] = None

    @field_validator("cnpj")
    @classmethod
    def normalize_cnpj(cls, v: str) -> str:
        v = _only_digits.sub("", v or "")
        if len(v) != 14:
            raise ValueError("CNPJ deve ter 14 dígitos")
        return v

# Para POST /empresas (estrito, mantém obrigatórios)
class EmpresaCreate(EmpresaBase):
    pass

# Para PUT /empresas/{id} (parcial)
class EmpresaUpdate(BaseModel):
    cod_empresa: Optional[str] = None
    nome_razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    login_muni: Optional[str] = None
    senha_muni: Optional[str] = None
    login_est: Optional[str] = None
    senha_est: Optional[str] = None

    @field_validator("cnpj")
    @classmethod
    def normalize_cnpj_update(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = _only_digits.sub("", v or "")
        if len(v) != 14:
            raise ValueError("CNPJ deve ter 14 dígitos")
        return v

# Para respostas (não expõe senhas por padrão)
class EmpresaRead(MongoModel):
    cod_empresa: Optional[str] = None
    nome_razao_social: str
    cnpj: str
    municipio: Optional[str] = None
    uf: Optional[str] = None
    inscricao_municipal: str = None
    inscricao_estadual: str = None
    login_muni: Optional[str] = None
    login_est: Optional[str] = None

# Para POST /empresas/bulk (campos de inscrição opcionais)
class EmpresaCreateBulk(BaseModel):
    cod_empresa: Optional[str] = None
    nome_razao_social: str
    cnpj: str
    municipio: Optional[str] = None
    uf: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    login_muni: Optional[str] = None
    senha_muni: Optional[str] = None
    login_est: Optional[str] = None
    senha_est: Optional[str] = None

    @field_validator("cnpj")
    @classmethod
    def normalize_cnpj_bulk(cls, v: str) -> str:
        v = _only_digits.sub("", v or "")
        if len(v) != 14:
            raise ValueError("CNPJ deve ter 14 dígitos")
        return v
