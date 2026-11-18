from fastapi import APIRouter, status

# 1. Inyección de dependencias (Capa api/deps)
from app.api.deps import ProveedorServiceDep

# 2. DTOs de entrada y salida (Capa models)
from app.models.producto import ProductoPublic
from app.models.proveedor import (
    ProveedorCreate,
    ProveedorPublic,
    ProveedorUpdate,
)

# 3. Router de Proveedores
router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


@router.post(
    "/",
    response_model=ProveedorPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar proveedor",
    description=(
        "Registra un nuevo proveedor en el sistema. "
        "Responde 409 Conflict si el correo ya se encuentra registrado."
    ),
)
async def create_proveedor(
    proveedor_in: ProveedorCreate,
    service: ProveedorServiceDep,
) -> ProveedorPublic:
    return await service.create(proveedor_in)


@router.get(
    "/",
    response_model=list[ProveedorPublic],
    summary="Listar proveedores",
    description=(
        "Lista paginada de proveedores, con filtros opcionales por origen y nombre."
    ),
)
async def list_proveedores(
    service: ProveedorServiceDep,
    skip: int = 0,
    limit: int = 10,
    origen: str | None = None,
    nombre: str | None = None,
) -> list[ProveedorPublic]:
    return await service.list_paginated(
        skip=skip,
        limit=limit,
        origen=origen,
        nombre=nombre,
    )


@router.get(
    "/{id_proveedor}",
    response_model=ProveedorPublic,
    summary="Obtener proveedor por ID",
    description="Busca un proveedor por ID o devuelve 404 si no existe.",
)
async def get_proveedor(
    id_proveedor: int,
    service: ProveedorServiceDep,
) -> ProveedorPublic:
    return await service.get_by_id(id_proveedor)


@router.patch(
    "/{id_proveedor}",
    response_model=ProveedorPublic,
    summary="Actualizar proveedor",
    description=(
        "Actualiza los datos de un proveedor de forma parcial. "
        "Responde 404 si no existe y 409 Conflict si el nuevo correo ya pertenece a otro proveedor."
    ),
)
async def update_proveedor(
    id_proveedor: int,
    proveedor_in: ProveedorUpdate,
    service: ProveedorServiceDep,
) -> ProveedorPublic:
    return await service.update(id_proveedor, proveedor_in)


@router.delete(
    "/{id_proveedor}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar proveedor",
    description=(
        "Elimina un proveedor si no tiene productos asociados. "
        "Responde 404 si no existe y 409 Conflict si tiene productos asociados."
    ),
)
async def delete_proveedor(
    id_proveedor: int,
    service: ProveedorServiceDep,
) -> None:
    await service.delete(id_proveedor)


@router.get(
    "/{id_proveedor}/productos",
    response_model=list[ProductoPublic],
    summary="Listar productos del proveedor",
    description=(
        "Lista paginada de productos abastecidos por un proveedor específico. "
        "Responde 404 si el proveedor no existe."
    ),
)
async def get_productos_proveedor(
    id_proveedor: int,
    service: ProveedorServiceDep,
    skip: int = 0,
    limit: int = 10,
) -> list[ProductoPublic]:
    return await service.get_productos(id_proveedor, skip=skip, limit=limit)
