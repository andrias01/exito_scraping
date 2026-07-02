"""
Modelos SQLAlchemy para la base de datos SQLite.
Define las tablas productos e historial.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Clase base para todos los modelos."""
    pass


class Producto(Base):
    """Modelo de producto monitoreado."""

    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    imagen_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Precios objetivo (alertas)
    precio_objetivo_normal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precio_objetivo_tarjeta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Últimos precios conocidos
    ultimo_precio_normal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ultimo_precio_tarjeta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Metadatos
    ultima_revision: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    frecuencia_minutos: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disponible: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    descuento: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relación con historial
    historial: Mapped[List["Historial"]] = relationship(
        "Historial",
        back_populates="producto",
        cascade="all, delete-orphan",
        order_by="Historial.fecha.desc()",
    )

    def __repr__(self) -> str:
        return f"<Producto id={self.id} nombre={self.nombre!r}>"


class Historial(Base):
    """Registro histórico de precios por consulta."""

    __tablename__ = "historial"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False, index=True
    )
    precio_normal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precio_tarjeta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disponible: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    descuento: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relación con producto
    producto: Mapped["Producto"] = relationship("Producto", back_populates="historial")

    def __repr__(self) -> str:
        return (
            f"<Historial id={self.id} producto_id={self.producto_id} "
            f"fecha={self.fecha} precio_normal={self.precio_normal}>"
        )
