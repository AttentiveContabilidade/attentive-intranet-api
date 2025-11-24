# app/core/auth.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

# ============================
#  Hash de Senha (mais robusto)
# ============================
# bcrypt_sha256 elimina o limite de 72 bytes e evita erros
# bcrypt continua aceitando hashes antigos já salvos
pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto"
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica senha contra hash.
    bcrypt_sha256 normaliza senhas internamente, evitando crash.
    """
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Retorna hash seguro usando bcrypt_sha256.
    """
    return pwd_context.hash(password)

# ============================
#  Token JWT
# ============================
TokenType = Literal["access", "major"]

def _exp(*, minutes: Optional[int] = None, hours: Optional[int] = None) -> int:
    now = datetime.now(timezone.utc)
    if minutes is not None:
        return int((now + timedelta(minutes=minutes)).timestamp())
    if hours is not None:
        return int((now + timedelta(hours=hours)).timestamp())
    return int((now + timedelta(minutes=15)).timestamp())

def create_token(*, sub: str, token_type: TokenType) -> str:
    if not sub:
        raise ValueError("sub is required")

    if token_type == "access":
        exp = _exp(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    elif token_type == "major":
        exp = _exp(hours=settings.MAJOR_TOKEN_EXPIRE_HOURS)
    else:
        raise ValueError("invalid token_type")

    payload = {
        "sub": sub,
        "type": token_type,
        "exp": exp,
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e:
        raise ValueError(str(e))
