from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.repositories import (
    CategoriaRepository,
    MovimientoStockRepository,
    ProductoRepository,
    ProveedorRepository,
)


def get_categoria_repository(
    session: AsyncSession = Depends(get_session),
) -> CategoriaRepository:
    return CategoriaRepository(session)


def get_proveedor_repository(
    session: AsyncSession = Depends(get_session),
) -> ProveedorRepository:
    return ProveedorRepository(session)


def get_producto_repository(
    session: AsyncSession = Depends(get_session),
) -> ProductoRepository:
    return ProductoRepository(session)


def get_movimiento_stock_repository(
    session: AsyncSession = Depends(get_session),
) -> MovimientoStockRepository:
    return MovimientoStockRepository(session)