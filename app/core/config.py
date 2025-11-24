# app/core/config.py
from typing import List, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    # Ambiente
    ENV: str = "dev"

    # --- Mongo (padrão do projeto) ---
    MONGO_URI: str = "mongodb://127.0.0.1:27017"
    MONGO_DB: str = "attentive"

    # Banco de LOGS (opcional; se não informar, usa o mesmo URI e <MONGO_DB>_logs)
    LOGS_MONGO_URI: Optional[str] = None
    LOGS_MONGO_DB: Optional[str] = None

    # --- SQL (opcional; deixe None se não usar Postgres/MySQL) ---
    DATABASE_URL: Optional[str] = None

    # --- Segurança / JWT ---
    SECRET_KEY: str = "change-me"     # PRODUÇÃO: defina no .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # minor token
    MAJOR_TOKEN_EXPIRE_HOURS: int = 7      # major token

    # --- CORS (origens permitidas) ---
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """
        Permite definir BACKEND_CORS_ORIGINS como CSV ou JSON no .env.
        - CSV:  BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
        - JSON: BACKEND_CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
        """
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                import json
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(i).strip() for i in parsed if str(i).strip()]
                except Exception:
                    pass
            return [i.strip() for i in s.split(",") if i.strip()]
        if isinstance(v, (list, tuple)):
            return [str(i).strip() for i in v if str(i).strip()]
        return list(cls.model_fields["BACKEND_CORS_ORIGINS"].default)

    # Helpers para logs (fallbacks)
    @property
    def mongo_logs_uri(self) -> str:
        return self.LOGS_MONGO_URI or self.MONGO_URI

    @property
    def mongo_logs_db(self) -> str:
        return self.LOGS_MONGO_DB or f"{self.MONGO_DB}_logs"


settings = Settings()
