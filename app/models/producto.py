from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.movimiento_stock import MovimientoStock


class ProductoBase(SQLModel):
    sku: str = Field(max_length=50, unique=True, index=True)
    nombre: str = Field(max_length=150, index=True)
    precio: float = Field(gt=0)
    costo: float = Field(ge=0)
    stock_minimo: int = Field(default=0, ge=0)
    id_categoria: int = Field(foreign_key="categorias.id_categoria")
    id_proveedor: int = Field(foreign_key="proveedores.id_proveedor")


class Producto(ProductoBase, table=True):
    __tablename__ = "productos"

    id_producto: int | None = Field(default=None, primary_key=True)
    stock_actual: int = Field(default=0, ge=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Lado "1": un producto registra muchos movimientos
    movimientos: list["MovimientoStock"] = Relationship(back_populates="producto")


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(SQLModel):
    sku: str | None = Field(default=None, max_length=50)
    nombre: str | None = Field(default=None, max_length=150)
    precio: float | None = Field(default=None, gt=0)
    costo: float | None = Field(default=None, ge=0)
    stock_minimo: int | None = Field(default=None, ge=0)
    id_categoria: int | None = None
    id_proveedor: int | None = None


class ProductoPublic(ProductoBase):
    id_producto: int
    stock_actual: int
    created_at: datetime
    updated_at: datetime
