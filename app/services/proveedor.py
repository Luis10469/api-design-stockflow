from fastapi import HTTPException

from app.models.proveedor import ProveedorCreate, ProveedorUpdate
from app.repositories.producto import ProductoRepository
from app.repositories.proveedor import ProveedorRepository


class ProveedorService:
    """Capa 2 - Lógica y Reglas de Negocio para Proveedor (Tarea T-25)."""

    def __init__(
        self,
        proveedor_repo: ProveedorRepository,
        producto_repo: ProductoRepository,
    ) -> None:
        self.proveedor_repo = proveedor_repo
        self.producto_repo = producto_repo

    # 1. READ (Uno por ID)
    async def get_by_id(self, id_proveedor: int):
        proveedor = await self.proveedor_repo.get_by_id(id_proveedor)
        if not proveedor:
            raise HTTPException(
                status_code=404, detail="Proveedor no encontrado"
            )
        return proveedor

    # 2. READ (Lista paginada con filtros)
    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 10,
        origen: str | None = None,
        nombre: str | None = None,
    ):
        return await self.proveedor_repo.get_multi(
            skip=skip,
            limit=limit,
            origen=origen,
            nombre=nombre,
        )

    # 3. CREATE (Regla de negocio: unicidad de correo)
    async def create(self, proveedor_in: ProveedorCreate):
        existente = await self.proveedor_repo.get_by_correo(proveedor_in.correo)
        if existente:
            raise HTTPException(
                status_code=409,
                detail="El correo del proveedor ya se encuentra registrado",
            )
        return await self.proveedor_repo.create(proveedor_in)

    # 4. UPDATE (Regla de negocio: existencia y no colisión de correo)
    async def update(self, id_proveedor: int, proveedor_in: ProveedorUpdate):
        proveedor = await self.proveedor_repo.get_by_id(id_proveedor)
        if not proveedor:
            raise HTTPException(
                status_code=404, detail="Proveedor no encontrado"
            )

        if proveedor_in.correo is not None:
            existente = await self.proveedor_repo.get_by_correo(
                proveedor_in.correo
            )
            if existente and existente.id_proveedor != id_proveedor:
                raise HTTPException(
                    status_code=409,
                    detail="El correo ya pertenece a otro proveedor registrado",
                )

        return await self.proveedor_repo.update(proveedor, proveedor_in)

    # 5. DELETE (Regla obligatoria T-25: No se borra si tiene productos)
    async def delete(self, id_proveedor: int):
        proveedor = await self.proveedor_repo.get_by_id(id_proveedor)
        if not proveedor:
            raise HTTPException(
                status_code=404, detail="Proveedor no encontrado"
            )

        # Regla de integridad referencial: no se puede borrar si abastece productos
        productos = await self.producto_repo.get_multi(
            skip=0, limit=1, id_proveedor=id_proveedor
        )
        if productos:
            raise HTTPException(
                status_code=409,
                detail="No se puede borrar el proveedor porque tiene productos asociados",
            )

        await self.proveedor_repo.delete(proveedor)
        return True

    # 6. PRODUCTOS DEL PROVEEDOR (GET /proveedores/:id/productos)
    async def get_productos(
        self, id_proveedor: int, skip: int = 0, limit: int = 10
    ):
        await self.get_by_id(id_proveedor)  # Lanza 404 si el proveedor no existe
        return await self.producto_repo.get_multi(
            skip=skip, limit=limit, id_proveedor=id_proveedor
        )
