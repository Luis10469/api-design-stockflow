from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.producto import Producto
from app.models.proveedor import Proveedor, ProveedorCreate, ProveedorUpdate


class ProveedorRepository:
    """Capa 3 - Acceso a Datos (Repositorio) para Proveedor."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # 1. READ (Uno por llave primaria)
    async def get_by_id(self, id_proveedor: int) -> Proveedor | None:
        """Busca un proveedor por su ID. Retorna None si no existe."""
        return await self.session.get(Proveedor, id_proveedor)

    # 2. READ (Uno por correo electrónico)
    async def get_by_correo(self, correo: str) -> Proveedor | None:
        """Busca un proveedor por su correo electrónico."""
        statement = select(Proveedor).where(Proveedor.correo == correo)
        result = await self.session.execute(statement)
        return result.scalars().first()

    # 3. READ (Uno por nombre)
    async def get_by_nombre(self, nombre: str) -> Proveedor | None:
        """Busca un proveedor por su nombre exacto."""
        statement = select(Proveedor).where(Proveedor.nombre == nombre)
        result = await self.session.execute(statement)
        return result.scalars().first()

    # 4. READ (Múltiples con filtros opcionales y paginación)
    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        origen: str | None = None,
        nombre: str | None = None,
    ) -> Sequence[Proveedor]:
        """Lista paginada de proveedores con filtros opcionales."""
        statement = select(Proveedor)

        if origen is not None:
            statement = statement.where(Proveedor.origen == origen)

        if nombre is not None:
            statement = statement.where(Proveedor.nombre.contains(nombre))

        statement = (
            statement.order_by(Proveedor.id_proveedor).offset(skip).limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    # 5. CREATE
    async def create(self, proveedor_in: ProveedorCreate | dict) -> Proveedor:
        """Crea y persiste un nuevo proveedor."""
        if isinstance(proveedor_in, dict):
            db_proveedor = Proveedor(**proveedor_in)
        else:
            db_proveedor = Proveedor.model_validate(proveedor_in)

        self.session.add(db_proveedor)
        await self.session.commit()
        await self.session.refresh(db_proveedor)
        return db_proveedor

    # 6. UPDATE
    async def update(
        self,
        db_proveedor: Proveedor | int,
        proveedor_in: ProveedorUpdate | dict,
    ) -> Proveedor | None:
        """Actualiza los campos de un proveedor existente."""
        if isinstance(db_proveedor, int):
            db_proveedor = await self.get_by_id(db_proveedor)
            if db_proveedor is None:
                return None

        if isinstance(proveedor_in, dict):
            update_data = {k: v for k, v in proveedor_in.items() if v is not None}
        else:
            update_data = proveedor_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_proveedor, field, value)

        db_proveedor.updated_at = datetime.now(timezone.utc)
        self.session.add(db_proveedor)
        await self.session.commit()
        await self.session.refresh(db_proveedor)
        return db_proveedor

    # 7. DELETE
    async def delete(self, db_proveedor: Proveedor | int) -> bool:
        """Elimina un proveedor de la base de datos."""
        if isinstance(db_proveedor, int):
            db_proveedor = await self.get_by_id(db_proveedor)
            if db_proveedor is None:
                return False

        await self.session.delete(db_proveedor)
        await self.session.commit()
        return True

    # 8. MÉTODOS DE RELACIÓN
    async def get_productos(
        self,
        id_proveedor: int,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Producto]:
        """Obtiene los productos suministrados por un proveedor (Endpoint GET /proveedores/:id/productos)."""
        statement = (
            select(Producto)
            .where(Producto.id_proveedor == id_proveedor)
            .order_by(Producto.id_producto)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def has_productos(self, id_proveedor: int) -> bool:
        """Verifica si el proveedor tiene productos asociados para evitar violar la regla de negocio al eliminar."""
        statement = (
            select(Producto.id_producto)
            .where(Producto.id_proveedor == id_proveedor)
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.first() is not None
