from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.core.config import settings

# 1. Motor asíncrono con la URL configurada en settings
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=False,
    future=True,
)

# 2. Fábrica de sesiones asíncronas
async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 3. Inicialización de tablas
async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

# 4. Inyector de dependencias para los endpoints de FastAPI
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
