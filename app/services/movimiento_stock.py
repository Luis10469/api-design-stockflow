from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.models.movimiento_stock import MovimientoStock, MovimientoStockCreate
from app.models.producto import Producto
from app.repositories.movimiento_stock import MovimientoStockRepository
from app.repositories.producto import ProductoRepository

TIPOS_VALIDOS = ("ENTRADA", "SALIDA", "AJUSTE")


class MovimientoStockService:
    """Capa 4 - Lógica de Negocio para MovimientoStock.

    Reglas del README:
    - El producto del movimiento tiene que existir (404).
    - ENTRADA suma, SALIDA resta y AJUSTE corrige el stock_actual del producto.
    - Una SALIDA no puede dejar el stock en negativo (409).
    - El movimiento y el cambio de stock se guardan en la misma transacción.
    - Los movimientos son inmutables: este servicio no tiene update ni delete.
    """

    def __init__(
        self,
        movimiento_repo: MovimientoStockRepository,
        producto_repo: ProductoRepository,
    ) -> None:
        # Los dos repositorios deben compartir la sesión: así el commit del
        # movimiento guarda también el nuevo stock, en una sola transacción.
        if movimiento_repo.session is not producto_repo.session:
            raise ValueError(
                "MovimientoStockService necesita que los dos repositorios usen la misma sesión"
            )
        self.movimiento_repo = movimiento_repo
        self.producto_repo = producto_repo

    async def _get_producto(self, id_producto: int) -> Producto:
        """Busca el producto del movimiento o lanza 404 si no existe."""
        producto = await self.producto_repo.get_by_id(id_producto)
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado",
            )
        return producto

    async def get_by_id(self, id_movimiento: int) -> MovimientoStock:
        """Busca un movimiento por id o lanza 404 si no existe."""
        movimiento = await self.movimiento_repo.get_by_id(id_movimiento)
        if not movimiento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movimiento no encontrado",
            )
        return movimiento

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        id_producto: int | None = None,
        tipo: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> list[MovimientoStock]:
        """Lista paginada con filtros. Si llega un producto, tiene que existir (404)."""
        if id_producto is not None:
            await self._get_producto(id_producto)
        if tipo is not None:
            tipo = tipo.upper()
        return await self.movimiento_repo.get_multi(
            skip=skip,
            limit=limit,
            id_producto=id_producto,
            tipo=tipo,
            desde=desde,
            hasta=hasta,
        )

    async def create(self, movimiento_in: MovimientoStockCreate) -> MovimientoStock:
        """Registra el movimiento y actualiza el stock del producto en la misma transacción."""
        tipo = movimiento_in.tipo.upper()
        if tipo not in TIPOS_VALIDOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El tipo debe ser ENTRADA, SALIDA o AJUSTE",
            )

        producto = await self._get_producto(movimiento_in.id_producto)

        if tipo == "ENTRADA":
            nuevo_stock = producto.stock_actual + movimiento_in.cantidad
        elif tipo == "SALIDA":
            nuevo_stock = producto.stock_actual - movimiento_in.cantidad
            if nuevo_stock < 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Stock insuficiente: hay {producto.stock_actual} "
                        f"y se intentan sacar {movimiento_in.cantidad}"
                    ),
                )
        else:
            # AJUSTE: la cantidad es el stock real contado; reemplaza al actual
            nuevo_stock = movimiento_in.cantidad

        # El producto queda modificado en la sesión; el commit que hace el
        # repositorio al crear el movimiento guarda los dos cambios juntos.
        producto.stock_actual = nuevo_stock
        producto.updated_at = datetime.now(timezone.utc)
        try:
            return await self.movimiento_repo.create(
                movimiento_in.model_copy(update={"tipo": tipo})
            )
        except Exception:
            # Si falla el guardado, no queda ni el movimiento ni el stock nuevo
            await self.movimiento_repo.session.rollback()
            raise
