from datetime import datetime, timezone
from pydantic import EmailStr
from sqlmodel import Field, SQLModel


# ==========================================
# 1. Base Común (Propiedades compartidas)
# ==========================================
class ProveedorBase(SQLModel):
    """Propiedades base compartidas: fuente única de verdad para la entidad y la API."""

    nombre: str = Field(
        max_length=150,
        index=True,
        description="Nombre o razón social del proveedor (máximo 150 letras)",
    )
    telefono: str | None = Field(
        default=None,
        max_length=20,
        description="Teléfono de contacto del proveedor",
    )
    correo: EmailStr = Field(
        unique=True,
        index=True,
        description="Correo electrónico válido (rechazado por el sistema si el formato es inválido)",
    )
    direccion: str | None = Field(
        default=None,
        max_length=255,
        description="Dirección física del proveedor",
    )
    origen: str | None = Field(
        default=None,
        max_length=100,
        description="Lugar o país de origen del proveedor",
    )


# ==========================================
# 2. Modelo de Base de Datos (ORM Table)
# ==========================================
class Proveedor(ProveedorBase, table=True):
    """Tabla de base de datos 'proveedores' generada por SQLModel."""

    __tablename__ = "proveedores"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ==========================================
# 3. DTOs de la API
# ==========================================
class ProveedorCreate(ProveedorBase):
    """Schema para registrar o crear un nuevo proveedor (POST)."""

    pass


class ProveedorUpdate(SQLModel):
    """Schema para actualizar un proveedor mediante PATCH (todos los campos opcionales)."""

    nombre: str | None = Field(default=None, max_length=150)
    telefono: str | None = Field(default=None, max_length=20)
    correo: EmailStr | None = Field(default=None)
    direccion: str | None = Field(default=None, max_length=255)
    origen: str | None = Field(default=None, max_length=100)


class ProveedorPublic(ProveedorBase):
    """Schema de respuesta pública para la API (GET / Response)."""

    id: int
    created_at: datetime
    updated_at: datetime
