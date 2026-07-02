"""
Esquemas Pydantic para validación de datos en la API REST.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator


# ─── Producto ─────────────────────────────────────────────────────────────────

class ProductoBase(BaseModel):
    """Campos base compartidos para crear y editar productos."""
    url: str
    precio_objetivo_normal: Optional[float] = None
    precio_objetivo_tarjeta: Optional[float] = None
    frecuencia_minutos: int = 60
    activo: bool = True

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Valida que la URL sea de Éxito Colombia."""
        v = v.strip()
        if not v.startswith("http"):
            raise ValueError("La URL debe comenzar con http o https")
        if "exito.com" not in v:
            raise ValueError("La URL debe ser de exito.com")
        return v

    @field_validator("frecuencia_minutos")
    @classmethod
    def validate_frecuencia(cls, v: int) -> int:
        if v < 5:
            raise ValueError("La frecuencia mínima es 5 minutos")
        return v


class ProductoCreate(ProductoBase):
    """Esquema para crear un nuevo producto."""
    pass


class ProductoUpdate(BaseModel):
    """Esquema para actualizar un producto (todos los campos opcionales)."""
    url: Optional[str] = None
    precio_objetivo_normal: Optional[float] = None
    precio_objetivo_tarjeta: Optional[float] = None
    frecuencia_minutos: Optional[int] = None
    activo: Optional[bool] = None


class ProductoResponse(BaseModel):
    """Esquema de respuesta con todos los datos del producto."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    url: str
    imagen_url: Optional[str] = None
    precio_objetivo_normal: Optional[float] = None
    precio_objetivo_tarjeta: Optional[float] = None
    ultimo_precio_normal: Optional[float] = None
    ultimo_precio_tarjeta: Optional[float] = None
    ultima_revision: Optional[datetime] = None
    frecuencia_minutos: int
    activo: bool
    disponible: Optional[bool] = None
    descuento: Optional[float] = None
    creado_en: datetime
    actualizado_en: datetime


# ─── Historial ────────────────────────────────────────────────────────────────

class HistorialResponse(BaseModel):
    """Esquema de respuesta para el historial de precios."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    fecha: datetime
    precio_normal: Optional[float] = None
    precio_tarjeta: Optional[float] = None
    disponible: Optional[bool] = None
    descuento: Optional[float] = None
    error: Optional[str] = None


# ─── Respuestas genéricas ─────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Respuesta del endpoint /health."""
    status: str
    timestamp: datetime
    version: str = "1.0.0"
    database: str = "ok"


class RunResponse(BaseModel):
    """Respuesta del endpoint /run."""
    status: str
    productos_monitoreados: int
    exitosos: int
    fallidos: int
    resultados: list[dict]
    duracion_segundos: float


class MessageResponse(BaseModel):
    """Respuesta genérica con mensaje."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Respuesta de error."""
    error: str
    detail: Optional[str] = None
