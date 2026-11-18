"""Router de Productos (Capa 5, tema 13).

Expone el CRUD de productos y delega todas las reglas de negocio al
``ProductoService``, que se inyecta con su alias de ``app.api.deps``.
"""

from fastapi import APIRouter, Query, Response, status

from app.api.deps import ProductoServiceDep
from app.models.producto import ProductoCreate, ProductoPublic, ProductoUpdate

router = APIRouter(prefix="/productos", tags=["Productos"])


@router.get("", response_model=list[ProductoPublic])
async def listar_productos(
    service: ProductoServiceDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    id_categoria: int | None = None,
    id_proveedor: int | None = None,
    bajo_stock: bool = False,
):
    """Lista productos con paginación y filtros por categoría, proveedor y stock bajo."""
    return await service.list_paginated(
        skip=skip,
        limit=limit,
        id_categoria=id_categoria,
        id_proveedor=id_proveedor,
        bajo_stock=bajo_stock,
    )


@router.get("/{id_producto}", response_model=ProductoPublic)
async def obtener_producto(id_producto: int, service: ProductoServiceDep):
    """Devuelve un producto por su id o responde 404."""
    return await service.get_by_id(id_producto)


@router.post(
    "",
    response_model=ProductoPublic,
    status_code=status.HTTP_201_CREATED,
)
async def crear_producto(
    producto_in: ProductoCreate,
    service: ProductoServiceDep,
):
    """Crea un producto con stock_actual en 0; el servicio valida SKU y llaves foráneas."""
    return await service.create(producto_in)


@router.patch("/{id_producto}", response_model=ProductoPublic)
async def actualizar_producto(
    id_producto: int,
    producto_in: ProductoUpdate,
    service: ProductoServiceDep,
):
    """Actualiza los datos enviados, sin permitir el cambio directo de stock_actual."""
    return await service.update(id_producto, producto_in)


@router.delete("/{id_producto}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_producto(
    id_producto: int,
    service: ProductoServiceDep,
) -> Response:
    """Elimina un producto sin movimientos; el servicio responde 404 o 409 si no se puede."""
    await service.delete(id_producto)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
