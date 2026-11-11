"""Inyección de dependencias de la API (Capa 5, tema 12).

Une las capas: sesión (core) -> repositorios -> servicios. Los routers piden
el servicio con su alias (por ejemplo ``service: CategoriaServiceDep``) y
FastAPI arma todo por debajo. ``get_session`` se ejecuta una sola vez por
petición, así que todos los repositorios comparten la misma sesión, como lo
exige ``MovimientoStockService``.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.repositories import (
    CategoriaRepository,
    MovimientoStockRepository,
    ProductoRepository,
    ProveedorRepository,
)
from app.services import (
    CategoriaService,
    MovimientoStockService,
    ProductoService,
    ProveedorService,
)

# Nivel 1: sesión de base de datos (Capa 1, core)
SessionDep = Annotated[AsyncSession, Depends(get_session)]


# Nivel 2: fábricas de repositorios (Capa 3)
def get_categoria_repository(session: SessionDep) -> CategoriaRepository:
    return CategoriaRepository(session)


def get_proveedor_repository(session: SessionDep) -> ProveedorRepository:
    return ProveedorRepository(session)


def get_producto_repository(session: SessionDep) -> ProductoRepository:
    return ProductoRepository(session)


def get_movimiento_stock_repository(
    session: SessionDep,
) -> MovimientoStockRepository:
    return MovimientoStockRepository(session)


CategoriaRepoDep = Annotated[CategoriaRepository, Depends(get_categoria_repository)]
ProveedorRepoDep = Annotated[ProveedorRepository, Depends(get_proveedor_repository)]
ProductoRepoDep = Annotated[ProductoRepository, Depends(get_producto_repository)]
MovimientoStockRepoDep = Annotated[
    MovimientoStockRepository, Depends(get_movimiento_stock_repository)
]


# Nivel 3: fábricas de servicios (Capa 4)
def get_categoria_service(
    categoria_repo: CategoriaRepoDep,
    producto_repo: ProductoRepoDep,
) -> CategoriaService:
    return CategoriaService(
        categoria_repo=categoria_repo,
        producto_repo=producto_repo,
    )


def get_proveedor_service(
    proveedor_repo: ProveedorRepoDep,
    producto_repo: ProductoRepoDep,
) -> ProveedorService:
    return ProveedorService(
        proveedor_repo=proveedor_repo,
        producto_repo=producto_repo,
    )


def get_producto_service(
    producto_repo: ProductoRepoDep,
    categoria_repo: CategoriaRepoDep,
    proveedor_repo: ProveedorRepoDep,
    movimiento_repo: MovimientoStockRepoDep,
) -> ProductoService:
    return ProductoService(
        producto_repo=producto_repo,
        categoria_repo=categoria_repo,
        proveedor_repo=proveedor_repo,
        movimiento_repo=movimiento_repo,
    )


def get_movimiento_stock_service(
    movimiento_repo: MovimientoStockRepoDep,
    producto_repo: ProductoRepoDep,
) -> MovimientoStockService:
    return MovimientoStockService(
        movimiento_repo=movimiento_repo,
        producto_repo=producto_repo,
    )


CategoriaServiceDep = Annotated[CategoriaService, Depends(get_categoria_service)]
ProveedorServiceDep = Annotated[ProveedorService, Depends(get_proveedor_service)]
ProductoServiceDep = Annotated[ProductoService, Depends(get_producto_service)]
MovimientoStockServiceDep = Annotated[
    MovimientoStockService, Depends(get_movimiento_stock_service)
]
