"""Router de Categorías (Capa 5, tema 13).

Expone el CRUD de categorías y el endpoint anidado de sus productos. Toda la
lógica de negocio vive en ``CategoriaService``, que se inyecta con su alias de
``app.api.deps``.
"""

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CategoriaServiceDep, ProductoServiceDep
from app.models.categoria import CategoriaCreate, CategoriaPublic, CategoriaUpdate
from app.models.producto import ProductoPublic

router = APIRouter(prefix="/categorias", tags=["Categorias"])


@router.get("/", response_model=list[CategoriaPublic])
async def listar_categorias(
    service: CategoriaServiceDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Lista categorías con paginación."""
    return await service.list_paginated(skip=skip, limit=limit)


@router.get("/{id_categoria}", response_model=CategoriaPublic)
async def obtener_categoria(id_categoria: int, service: CategoriaServiceDep):
    """Devuelve una categoría por su id o responde 404."""
    return await service.get_by_id(id_categoria)


@router.get("/{id_categoria}/productos", response_model=list[ProductoPublic])
async def listar_productos_de_categoria(
    id_categoria: int,
    service: CategoriaServiceDep,
    producto_service: ProductoServiceDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Lista los productos de la categoría o responde 404 si la categoría no existe."""
    await service.get_by_id(id_categoria)
    return await producto_service.list_paginated(
        skip=skip,
        limit=limit,
        id_categoria=id_categoria,
    )


@router.post(
    "/",
    response_model=CategoriaPublic,
    status_code=status.HTTP_201_CREATED,
)
async def crear_categoria(
    categoria_in: CategoriaCreate,
    service: CategoriaServiceDep,
):
    """Crea una categoría; el servicio responde 409 si el nombre ya existe."""
    return await service.create(categoria_in)


@router.patch("/{id_categoria}", response_model=CategoriaPublic)
async def actualizar_categoria(
    id_categoria: int,
    categoria_in: CategoriaUpdate,
    service: CategoriaServiceDep,
):
    """Actualiza los datos enviados; responde 404 o 409 si el nombre ya existe."""
    return await service.update(id_categoria, categoria_in)


@router.delete("/{id_categoria}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_categoria(
    id_categoria: int,
    service: CategoriaServiceDep,
) -> Response:
    """Elimina una categoría sin productos; responde 404 o 409 si no se puede."""
    await service.delete(id_categoria)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
