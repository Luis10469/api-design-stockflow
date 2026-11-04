from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship

class CategoriaBase(SQLModel):
    nombre: str = Field(max_length=100, unique=True, index=True)
    descripcion: Optional[str] = Field(default=None, max_length=255)

class Categoria(CategoriaBase, table=True):
    __tablename__ = "categorias"
    id_categoria: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    productos: list["Producto"] = Relationship(back_populates="categoria")

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=255)

class CategoriaPublic(CategoriaBase):
    id_categoria: int
    created_at: datetime
    updated_at: datetime
