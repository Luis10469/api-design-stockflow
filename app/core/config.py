from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global de la aplicación cargada desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "StockFlow API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DB_TYPE: Literal["sqlite", "postgres"] = "sqlite"

    SQLITE_URL: str = "sqlite+aiosqlite:///./fastapi_demo.db"
    POSTGRES_URL: str = ""

    ECHO_SQL: bool = False

    @property
    def DATABASE_URL(self) -> str:
        """Retorna la URL asíncrona adecuada según DB_TYPE adaptando la cadena de Neon."""
        if self.DB_TYPE == "postgres":
            if not self.POSTGRES_URL:
                # Sin esto, la app arrancaría con SQLite sin avisar y los datos se perderían
                raise ValueError("DB_TYPE es 'postgres' pero POSTGRES_URL está vacía")
            url = self.POSTGRES_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and not url.startswith(
                "postgresql+asyncpg://"
            ):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            # asyncpg no entiende sslmode ni channel_binding (Neon los trae en su cadena):
            # sslmode pasa a ssl y channel_binding se quita
            partes = urlsplit(url)
            parametros = dict(parse_qsl(partes.query))
            sslmode = parametros.pop("sslmode", None)
            parametros.pop("channel_binding", None)
            if sslmode:
                parametros["ssl"] = sslmode
            return urlunsplit(partes._replace(query=urlencode(parametros)))
        return self.SQLITE_URL


settings = Settings()