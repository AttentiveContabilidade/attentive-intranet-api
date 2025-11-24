# app/dependencies/db.py
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Depends
import os

# Carrega a URI do MongoDB (definida no .env)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "Attentive")

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    """
    Retorna a instância global do cliente MongoDB.
    Cria uma se ainda não existir.
    """
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client


async def get_db():
    """
    Dependência do FastAPI para injetar o banco Mongo.
    Uso: `db = Depends(get_db)`
    """
    client = get_client()
    db = client[DB_NAME]
    return db
