from motor.motor_asyncio import AsyncIOMotorClient
from app.core.settings import settings

_client: AsyncIOMotorClient | None = None
_client_logs: AsyncIOMotorClient | None = None


async def get_client() -> AsyncIOMotorClient:
    """Retorna o cliente MongoDB principal."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URI)
    return _client


async def get_db():
    """Retorna o banco de dados principal (Attentive)."""
    client = await get_client()
    return client[settings.MONGO_DB]


async def get_client_logs() -> AsyncIOMotorClient:
    """
    Retorna o cliente para logs.
    Se MONGO_URI_LOGS estiver definido, cria um client separado.
    Caso contrário, reutiliza o mesmo client principal.
    """
    global _client_logs
    if settings.MONGO_URI_LOGS:
        if _client_logs is None:
            _client_logs = AsyncIOMotorClient(settings.MONGO_URI_LOGS)
        return _client_logs
    return await get_client()


async def get_db_logs():
    """Retorna o banco de dados de logs (Attentive_logs)."""
    client = await get_client_logs()
    return client[settings.MONGO_DB_LOGS]
