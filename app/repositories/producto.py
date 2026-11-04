from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.producto import Producto, ProductoCreate, ProductoUpdate


class ProductoRepository:
    """Capa 3 - Acceso a Datos (Repositorio) para Producto."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # 1. READ (Uno por llave primaria)
    async def get_by_id(self, id_producto: int) -> Producto | None:
        """Busca un producto por su id. Retorna None si no existe."""
        return await self.session.get(Producto, id_producto)

    # 2. READ (Uno por SKU)
    async def get_by_sku(self, sku: str) -> Producto | None:
        """Busca un producto por su SKU. Retorna None si no existe."""
        statement = select(Producto).where(Producto.sku == sku)
        result = await self.session.execute(statement)
        return result.scalars().first()

    # 3. READ (Múltiples, con filtros opcionales y paginación)
    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        id_categoria: int | None = None,
        id_proveedor: int | None = None,
        bajo_stock: bool = False,
    ) -> list[Producto]:
        """Lista paginada de productos; solo aplica los filtros que lleguen."""
        statement = select(Producto)

        if id_categoria is not None:
            statement = statement.where(Producto.id_categoria == id_categoria)

        if id_proveedor is not None:
            statement = statement.where(Producto.id_proveedor == id_proveedor)

        # README: stock bajo cuando stock_actual <= stock_minimo
        if bajo_stock:
            statement = statement.where(
                Producto.stock_actual <= Producto.stock_minimo
            )

        statement = (
            statement.order_by(Producto.id_producto).offset(skip).limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    # 4. CREATE
    async def create(self, producto_in: ProductoCreate) -> Producto:
        """Inserta un nuevo producto. El stock_actual inicia en 0 por el modelo."""
        db_producto = Producto.model_validate(producto_in)
        self.session.add(db_producto)
        await self.session.commit()
        await self.session.refresh(db_producto)
        return db_producto

    # 5. UPDATE (nunca cambia stock_actual)
    async def update(
        self,
        db_producto: Producto,
        producto_in: ProductoUpdate,
    ) -> Producto:
        """Actualiza solo los campos enviados; el stock no se toca."""
        update_data = producto_in.model_dump(exclude_unset=True)
        update_data.pop("stock_actual", None)

        for field, value in update_data.items():
            setattr(db_producto, field, value)

        db_producto.updated_at = datetime.now(timezone.utc)
        self.session.add(db_producto)
        await self.session.commit()
        await self.session.refresh(db_producto)
        return db_producto

    # 6. DELETE
    async def delete(self, db_producto: Producto) -> None:
        """Elimina el producto recibido."""
        await self.session.delete(db_producto)
        await self.session.commit()
