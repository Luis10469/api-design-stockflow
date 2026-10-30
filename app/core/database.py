from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.core.config import settings

# 4. Configuración para Neon (SSL obligatorio)
connect_args = {}
if "neon.tech" in str(settings.DATABASE_URL):
    connect_args = {"ssl": True}

# 2 y 3. Motor asíncrono con echo dinámico y pool_pre_ping=True
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.ECHO_SQL,
    pool_pre_ping=True,
    connect_args=connect_args,
    future=True,
)

# Fábrica de sesiones asíncronas
async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 1. Inicialización con import app.models para registrar metadatos de tablas
async def init_db() -> None:
    import app.models  # Evita el error 3: asegura que SQLModel conozca todas las tablas

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

# Dependencia para FastAPI
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
