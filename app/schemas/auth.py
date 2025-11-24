# app/schemas/auth.py
from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(..., description="Usuário ou e-mail")
    password: str = Field(..., description="Senha em texto puro")


class TokenPair(BaseModel):
    access_token: str
    token_type: str = "bearer"
