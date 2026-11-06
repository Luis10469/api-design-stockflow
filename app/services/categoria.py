from fastapi import HTTPException

from app.repositories.categoria import CategoriaRepository
from app.repositories.producto import ProductoRepository

class CategoriaService:
    def __init__(
        self,
        categoria_repo: CategoriaRepository,
        producto_repo: ProductoRepository,
    ):
        self.categoria_repo = categoria_repo
        self.producto_repo = producto_repo

    async def get_by_id(self, categoria_id: int):
        categoria = await self.categoria_repo.get_by_id(categoria_id)
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoria no encontrada")
        return categoria

    async def list_paginated(self, skip: int = 0, limit: int = 10):
        return await self.categoria_repo.list_paginated(skip=skip, limit=limit)

    async def create(self, data: dict):
        nombre = data.get("nombre")
        if nombre:
            existente = await self.categoria_repo.get_by_nombre(nombre)
            if existente:
                raise HTTPException(status_code=409, detail="El nombre de la categoria ya existe")
        return await self.categoria_repo.create(data)

    async def update(self, categoria_id: int, data: dict):
        categoria = await self.categoria_repo.get_by_id(categoria_id)
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoria no encontrada")

        nombre = data.get("nombre")
        if nombre and nombre != categoria.nombre:
            existente = await self.categoria_repo.get_by_nombre(nombre)
            if existente:
                raise HTTPException(status_code=409, detail="El nombre de la categoria ya existe")

        return await self.categoria_repo.update(categoria_id, data)

    async def delete(self, categoria_id: int):
        categoria = await self.categoria_repo.get_by_id(categoria_id)
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoria no encontrada")

        productos = await self.producto_repo.get_multi(
            skip=0, limit=1, id_categoria=categoria_id
        )
        if productos:
            raise HTTPException(
                status_code=409,
                detail="No se puede borrar la categoria porque tiene productos",
            )

        await self.categoria_repo.delete(categoria_id)
        return True
