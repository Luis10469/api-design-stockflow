from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.core.config import settings

# Conexión especial para Neon (requiere SSL)
connect_args = {}
if "neon.tech" in str(settings.DATABASE_URL):
    connect_args = {"ssl": True}

# Motor asíncrono configurado según la guía
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.ECHO_SQL,
    pool_pre_ping=True,
    connect_args=connect_args,
    future=True,
)

# Fábrica de sesiones asíncronas (sin autocommit innecesario)
async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Inicialización de la base de datos
async def init_db() -> None:
    # Error 3: importar modelos para que SQLModel reconozca las tablas
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

# Dependencia para inyectar la sesión en FastAPI
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
