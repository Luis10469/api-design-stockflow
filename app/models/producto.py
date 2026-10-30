from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProductoBase(SQLModel):
    sku: str = Field(max_length=50, unique=True, index=True)
    nombre: str = Field(max_length=150)
    precio: float = Field(gt=0)
    costo: float = Field(ge=0)
    stock_minimo: int = Field(default=0, ge=0)
    id_categoria: int = Field(foreign_key="categoria.id_categoria")
    id_proveedor: int = Field(foreign_key="proveedor.id_proveedor")


class Producto(ProductoBase, table=True):
    id_producto: int | None = Field(default=None, primary_key=True)
    stock_actual: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    categoria: "Categoria" = Relationship(back_populates="productos")
    proveedor: "Proveedor" = Relationship(back_populates="productos")


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