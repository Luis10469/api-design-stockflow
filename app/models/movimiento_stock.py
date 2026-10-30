from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


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
