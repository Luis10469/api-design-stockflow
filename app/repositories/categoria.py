from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categoria import Categoria

class CategoriaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, categoria_id: int) -> Categoria | None:
        result = await self.db.execute(
            select(Categoria).where(Categoria.id_categoria == categoria_id)
        )
        return result.scalar_one_or_none()

    async def get_by_nombre(self, nombre: str) -> Categoria | None:
        result = await self.db.execute(
            select(Categoria).where(Categoria.nombre == nombre)
        )
        return result.scalar_one_or_none()

    async def list_paginated(self, skip: int = 0, limit: int = 10):
        result = await self.db.execute(select(Categoria).offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, data: dict) -> Categoria:
        categoria = Categoria(**data)
        self.db.add(categoria)
        await self.db.commit()
        await self.db.refresh(categoria)
        return categoria

    async def update(self, categoria_id: int, data: dict) -> Categoria | None:
        categoria = await self.get_by_id(categoria_id)
        if not categoria:
            return None
        for key, value in data.items():
            setattr(categoria, key, value)
        await self.db.commit()
        await self.db.refresh(categoria)
        return categoria

    async def delete(self, categoria_id: int) -> bool:
        categoria = await self.get_by_id(categoria_id)
        if not categoria:
            return False
        await self.db.delete(categoria)
        await self.db.commit()
        return True
