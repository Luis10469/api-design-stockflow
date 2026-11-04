from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.producto import Producto


# 1. Base Común
class MovimientoStockBase(SQLModel):
    id_producto: int = Field(foreign_key="productos.id_producto")
    tipo: str = Field(description="ENTRADA, SALIDA o AJUSTE")
    cantidad: int = Field(gt=0)
    motivo: str


# 2. Tabla de Base de Datos
class MovimientoStock(MovimientoStockBase, table=True):
    __tablename__ = "movimientos_stock"

    id_movimiento: int | None = Field(default=None, primary_key=True)
    # La fecha la asigna el servidor al registrar el movimiento
    fecha: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Lado "muchos": cada movimiento afecta a un solo producto
    producto: Optional["Producto"] = Relationship(back_populates="movimientos")


# 3. DTO de Entrada (POST)
class MovimientoStockCreate(MovimientoStockBase):
    pass


# Sin DTO de Edición: los movimientos son inmutables, no se editan (README)


# 4. DTO de Respuesta (GET)
class MovimientoStockPublic(MovimientoStockBase):
    id_movimiento: int
    fecha: datetime
