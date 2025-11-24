from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Banco principal
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "Attentive"

    # Banco de logs
    MONGO_DB_LOGS: str = "Attentive_logs"
    MONGO_URI_LOGS: str | None = None  # Se None, reaproveita o MONGO_URI

    # Chaves
    CRED_KEY: str
    CRAWLER_API_KEY: str

    # Autenticação JWT
    JWT_SECRET: str = "change-me-in-env"  # defina no .env
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
