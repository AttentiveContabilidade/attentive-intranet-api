# app/core/crypto.py
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from app.core.settings import settings  # <- lê do .env via pydantic-settings

_key = settings.CRED_KEY  # string base64 urlsafe
if not _key:
    raise RuntimeError("CRED_KEY não definido no .env")

fernet = Fernet(_key.encode() if isinstance(_key, str) else _key)

def enc(v: Optional[str]) -> Optional[str]:
    return fernet.encrypt(v.encode()).decode() if v else None

def dec(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    try:
        return fernet.decrypt(v.encode()).decode()
    except InvalidToken:
        # se estiver em texto puro legado ou a chave mudou, retorna como veio
        return v
