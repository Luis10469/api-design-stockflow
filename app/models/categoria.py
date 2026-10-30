from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class CategoriaBase(SQLModel):
    nombre: str = Field(max_length=100, unique=True, index=True)
    descripcion: Optional[str] = Field(default=None, max_length=255)

class Categoria(CategoriaBase, table=True):
    __tablename__ = "categoria"
    id_categoria: Optional[int] = Field(default=None, primary_key=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    fecha_actualizacion: datetime = Field(default_factory=datetime.utcnow, nullable=False)

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=255)

class CategoriaPublic(CategoriaBase):
    id_categoria: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime
