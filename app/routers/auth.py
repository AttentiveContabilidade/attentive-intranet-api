from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Header
from pydantic import BaseModel, EmailStr
from bson import ObjectId

from app.db.mongo import get_db
from app.core.security import verify_password, get_current_user_id
from app.core.config import settings
from app.core.auth import create_token, decode_token
from app.schemas.usuario import UsuarioRead

router = APIRouter(prefix="/auth", tags=["auth"])

# =========================
# Models de entrada/saída
# =========================
class LoginIn(BaseModel):
    email: EmailStr
    senha: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioRead


# =========================
# Config do Cookie do Major
# =========================
COOKIE_NAME = "major_token"
COOKIE_MAX_AGE = settings.MAJOR_TOKEN_EXPIRE_HOURS * 60 * 60  # seg


def _set_major_cookie(resp: Response, token: str):
    """
    Define o cookie HttpOnly do major token (7h por padrão).
    Em produção, use secure=True e HTTPS.
    """
    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=int(COOKIE_MAX_AGE),
        samesite="none",
        secure=True,  # PRODUÇÃO: True (HTTPS)
        path="/",
    )


def _build_safe_user(user: dict) -> dict:
    # Remove campos sensíveis e normaliza _id -> string quando necessário
    safe = {k: v for k, v in user.items() if k not in ("senha", "senha_hash")}
    if "_id" in safe and isinstance(safe["_id"], ObjectId):
        safe["_id"] = str(safe["_id"])
    return safe


# =========================
# Endpoints
# =========================
@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, response: Response, db=Depends(get_db)):
    """
    Autentica usando email/senha.
    Retorna access (minor, 60min) em JSON e define major (7h) em cookie HttpOnly.
    """
    user = await db["usuarios"].find_one({"email": data.email})
    if not user or not verify_password(data.senha, user.get("senha_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    # subject = _id do usuário
    sub = str(user["_id"])

    # minor (access) -> Bearer
    access = create_token(sub=sub, token_type="access")

    # major (refresh) -> Cookie HttpOnly
    major = create_token(sub=sub, token_type="major")
    _set_major_cookie(response, major)

    safe_user = _build_safe_user(user)
    return {"access_token": access, "usuario": UsuarioRead(**safe_user)}


@router.post("/refresh", response_model=TokenOut)
async def refresh(request: Request, db=Depends(get_db)):
    """
    Usa o major do cookie HttpOnly para emitir um novo access (minor).
    O major NÃO é reemitido (janela máxima = 7h após login).
    """
    major = request.cookies.get(COOKIE_NAME)
    if not major:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Major token ausente",
        )

    try:
        payload = decode_token(major)
        if payload.get("type") != "major":
            raise ValueError("Token não é major")
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("User id ausente")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Major token inválido ou expirado",
        )

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID inválido no token",
        )

    user = await db["usuarios"].find_one({"_id": oid})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
        )

    new_access = create_token(sub=user_id, token_type="access")
    safe_user = _build_safe_user(user)
    return {"access_token": new_access, "usuario": UsuarioRead(**safe_user)}


@router.get("/me")
async def me(authorization: str = Header(None), db=Depends(get_db)):
    """
    Retorna os dados do usuário autenticado via token Bearer.
    Campos expostos: id, nome, departamento, avatar_url, descricao_html.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Token ausente")

    token = authorization.replace("Bearer ", "")
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=401, detail="ID inválido no token")

    user = await db["usuarios"].find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    return {
        "id": str(user["_id"]),
        "display_name": user.get("nome"),
        "departamento": user.get("departamento"),
        "avatar_url": user.get("avatar_url"),
        "descricao_html": user.get("descricao_html", ""),
    }


@router.post("/logout", status_code=204)
async def logout():
    """
    Apaga o cookie do major token (encerra a janela de sessão).
    """
    resp = Response(status_code=204)
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp
