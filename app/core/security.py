from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings  # mantém import (pode ser útil em extensões)
from app.core.auth import (
    get_password_hash as _get_password_hash,
    verify_password as _verify_password,
    create_token,
    decode_token,
)

# -----------------------------------------------------------------------------
# Senhas (bcrypt) — wrappers para manter assinatura antiga
# -----------------------------------------------------------------------------
def hash_password(raw: str) -> str:
    """Wrapper compatível: gera hash bcrypt."""
    return _get_password_hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    """Wrapper compatível: verifica hash bcrypt."""
    return _verify_password(raw, hashed)


# -----------------------------------------------------------------------------
# OAuth2 Bearer
# -----------------------------------------------------------------------------
# Para a doc do Swagger e a dependência de rotas protegidas
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
# Alias de compatibilidade (alguns módulos podem importar reuse_oauth)
reuse_oauth = oauth2_scheme


# -----------------------------------------------------------------------------
# JWT (compat + dependência)
# -----------------------------------------------------------------------------
def create_access_token(data: Dict[str, Any], expires_minutes: Optional[int] = None) -> str:
    """
    Wrapper compatível que gera um token de *access* (minor).
    - Usa create_token(sub=..., token_type='access') da camada central.
    - `expires_minutes` é ignorado aqui, pois a duração é controlada por settings.
    """
    sub = str(data.get("sub")) if data and "sub" in data else ""
    if not sub:
        raise ValueError("create_access_token requer 'sub' em data (ex.: {'sub': user_id})")
    return create_token(sub=sub, token_type="access")

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Wrapper compatível que decodifica o JWT. Não força o tipo 'access' aqui.
    Use get_current_user_id para exigir 'access'.
    """
    try:
        return decode_token(token)
    except Exception:
        return None


async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dependência para rotas protegidas.
    - Lê o Bearer token do header Authorization.
    - Decodifica e **exige** que seja do tipo 'access' (minor).
    - Retorna o 'sub' (id do usuário).
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            # Token não é o minor — não permitir
            raise ValueError("Not an access token")
        sub = payload.get("sub")
        if not sub:
            raise ValueError("Missing subject")
        return str(sub)
    except Exception:
        # WWW-Authenticate ajuda o front a entender que precisa de Bearer
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
