from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.movimiento_stock import MovimientoStock, MovimientoStockCreate


class MovimientoStockRepository:
    """Capa 3 - Acceso a Datos (Repositorio) para MovimientoStock.

    Los movimientos son inmutables (README): este repositorio solo lee y crea.
    No tiene update ni delete; un error se corrige con un nuevo movimiento AJUSTE.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # 1. READ (Uno)
    async def get_by_id(self, id_movimiento: int) -> MovimientoStock | None:
        """Busca un movimiento por su clave primaria. Retorna None si no existe."""
        return await self.session.get(MovimientoStock, id_movimiento)

    # 2. READ (Múltiples, con filtros opcionales)
    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        id_producto: int | None = None,
        tipo: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> list[MovimientoStock]:
        """Lista paginada de movimientos; solo aplica los filtros que lleguen."""
        statement = select(MovimientoStock)

        # Filtro opcional: historial de un producto
        if id_producto is not None:
            statement = statement.where(MovimientoStock.id_producto == id_producto)

        # Filtro opcional: ENTRADA, SALIDA o AJUSTE
        if tipo is not None:
            statement = statement.where(MovimientoStock.tipo == tipo)

        # Filtro opcional: rango de fechas (incluye los extremos)
        if desde is not None:
            statement = statement.where(MovimientoStock.fecha >= desde)
        if hasta is not None:
            statement = statement.where(MovimientoStock.fecha <= hasta)

        statement = (
            statement.order_by(MovimientoStock.id_movimiento).offset(skip).limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    # 3. CREATE
    async def create(self, movimiento_in: MovimientoStockCreate) -> MovimientoStock:
        """Inserta un nuevo movimiento. La fecha la asigna el modelo al crearlo."""
        db_movimiento = MovimientoStock.model_validate(movimiento_in)
        self.session.add(db_movimiento)
        await self.session.commit()
        await self.session.refresh(db_movimiento)
        return db_movimiento
