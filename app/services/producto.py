from fastapi import HTTPException

from app.models.producto import ProductoCreate, ProductoUpdate
from app.repositories.categoria import CategoriaRepository
from app.repositories.movimiento_stock import MovimientoStockRepository
from app.repositories.producto import ProductoRepository
from app.repositories.proveedor import ProveedorRepository


class ProductoService:
    def __init__(
        self,
        producto_repo: ProductoRepository,
        categoria_repo: CategoriaRepository,
        proveedor_repo: ProveedorRepository,
        movimiento_repo: MovimientoStockRepository,
    ):
        self.producto_repo = producto_repo
        self.categoria_repo = categoria_repo
        self.proveedor_repo = proveedor_repo
        self.movimiento_repo = movimiento_repo

    async def get_by_id(self, id_producto: int):
        producto = await self.producto_repo.get_by_id(id_producto)
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return producto

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 10,
        id_categoria: int | None = None,
        id_proveedor: int | None = None,
        bajo_stock: bool = False,
    ):
        return await self.producto_repo.get_multi(
            skip=skip,
            limit=limit,
            id_categoria=id_categoria,
            id_proveedor=id_proveedor,
            bajo_stock=bajo_stock,
        )

    async def create(self, producto_in: ProductoCreate):
        if await self.producto_repo.get_by_sku(producto_in.sku):
            raise HTTPException(status_code=409, detail="El SKU ya existe")

        if not await self.categoria_repo.get_by_id(producto_in.id_categoria):
            raise HTTPException(status_code=404, detail="Categoria no encontrada")

        if not await self.proveedor_repo.get_by_id(producto_in.id_proveedor):
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")

        return await self.producto_repo.create(producto_in)

    async def update(self, id_producto: int, producto_in: ProductoUpdate):
        producto = await self.producto_repo.get_by_id(id_producto)
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        if producto_in.sku is not None:
            existente = await self.producto_repo.get_by_sku(producto_in.sku)
            if existente and existente.id_producto != id_producto:
                raise HTTPException(status_code=409, detail="El SKU ya existe")

        if producto_in.id_categoria is not None:
            if not await self.categoria_repo.get_by_id(producto_in.id_categoria):
                raise HTTPException(status_code=404, detail="Categoria no encontrada")

        if producto_in.id_proveedor is not None:
            if not await self.proveedor_repo.get_by_id(producto_in.id_proveedor):
                raise HTTPException(status_code=404, detail="Proveedor no encontrado")

        return await self.producto_repo.update(producto, producto_in)

    async def delete(self, id_producto: int):
        producto = await self.producto_repo.get_by_id(id_producto)
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        movimientos = await self.movimiento_repo.get_multi(
            skip=0, limit=1, id_producto=id_producto
        )
        if movimientos:
            raise HTTPException(
                status_code=409,
                detail="No se puede borrar el producto porque tiene movimientos",
            )

        await self.producto_repo.delete(producto)
        return True