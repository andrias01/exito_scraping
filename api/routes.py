"""
Rutas de la API FastAPI.
Define todos los endpoints del sistema.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.schemas import (
    ErrorResponse,
    HealthResponse,
    HistorialResponse,
    MessageResponse,
    ProductoCreate,
    ProductoResponse,
    ProductoUpdate,
    RunResponse,
)
from database.database import db_manager, get_db
from database.models import Historial, Producto
from scheduler.monitor_service import MonitorService

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Health ───────────────────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Estado del sistema",
    tags=["Sistema"],
)
def health_check() -> HealthResponse:
    """Verifica que el sistema está operativo."""
    db_status = "ok"
    try:
        with db_manager.get_session() as session:
            session.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"

    return HealthResponse(
        status="ok",
        timestamp=datetime.now(),
        database=db_status,
    )


# ─── Ejecutar monitoreo ───────────────────────────────────────────────────────

@router.get(
    "/run",
    response_model=RunResponse,
    summary="Ejecutar monitoreo completo",
    tags=["Monitoreo"],
)
async def run_monitoring(
    producto_id: Optional[int] = Query(None, description="ID del producto a monitorear (None = todos)")
) -> RunResponse:
    """
    Ejecuta el monitoreo de precios.
    - Sin parámetros: monitorea todos los productos activos.
    - Con producto_id: monitorea solo ese producto.
    """
    service = MonitorService()
    start = time.perf_counter()

    if producto_id is not None:
        result = await service.monitor_product(producto_id)
        resultados = [result]
    else:
        resultados = await service.monitor_all()

    duracion = time.perf_counter() - start
    exitosos = sum(1 for r in resultados if r.get("success"))
    fallidos = len(resultados) - exitosos

    return RunResponse(
        status="ok",
        productos_monitoreados=len(resultados),
        exitosos=exitosos,
        fallidos=fallidos,
        resultados=resultados,
        duracion_segundos=round(duracion, 2),
    )


# ─── Productos ────────────────────────────────────────────────────────────────

@router.get(
    "/products",
    response_model=list[ProductoResponse],
    summary="Listar productos",
    tags=["Productos"],
)
def get_products(
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    search: Optional[str] = Query(None, description="Buscar por nombre o URL"),
    session: Session = Depends(get_db),
) -> list[ProductoResponse]:
    """Retorna la lista de todos los productos registrados."""
    query = session.query(Producto)

    if activo is not None:
        query = query.filter(Producto.activo == activo)

    if search:
        term = f"%{search}%"
        query = query.filter(
            Producto.nombre.ilike(term) | Producto.url.ilike(term)
        )

    productos = query.order_by(Producto.creado_en.desc()).all()
    return [ProductoResponse.model_validate(p) for p in productos]


@router.post(
    "/product",
    response_model=ProductoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar producto",
    tags=["Productos"],
)
async def create_product(
    data: ProductoCreate,
    session: Session = Depends(get_db),
) -> ProductoResponse:
    """
    Registra un nuevo producto para monitorear.
    Realiza un scraping inicial para obtener el nombre e imagen.
    """
    # Verificar duplicados
    existing = session.query(Producto).filter(Producto.url == data.url).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un producto con esta URL.",
        )

    # Scraping inicial para obtener datos del producto
    from scraper.exito import ExitoScraper
    async with ExitoScraper() as scraper:
        scraped = await scraper.scrape_url(data.url)

    nombre = scraped.nombre or "Producto sin nombre"
    imagen_url = scraped.imagen_url

    producto = Producto(
        nombre=nombre,
        url=data.url,
        imagen_url=imagen_url,
        precio_objetivo_normal=data.precio_objetivo_normal,
        precio_objetivo_tarjeta=data.precio_objetivo_tarjeta,
        ultimo_precio_normal=scraped.precio_normal,
        ultimo_precio_tarjeta=scraped.precio_tarjeta,
        descuento=scraped.descuento,
        disponible=scraped.disponible,
        frecuencia_minutos=data.frecuencia_minutos,
        activo=data.activo,
        ultima_revision=datetime.now() if scraped.exitoso else None,
        creado_en=datetime.now(),
        actualizado_en=datetime.now(),
    )
    session.add(producto)
    session.flush()  # para obtener el ID

    # Guardar historial inicial
    if scraped.exitoso:
        historial = Historial(
            producto_id=producto.id,
            fecha=datetime.now(),
            precio_normal=scraped.precio_normal,
            precio_tarjeta=scraped.precio_tarjeta,
            disponible=scraped.disponible,
            descuento=scraped.descuento,
        )
        session.add(historial)

    session.refresh(producto)
    logger.info("Producto creado: %s (id=%d)", producto.nombre, producto.id)
    return ProductoResponse.model_validate(producto)


@router.get(
    "/product/{producto_id}",
    response_model=ProductoResponse,
    summary="Obtener producto",
    tags=["Productos"],
)
def get_product(
    producto_id: int,
    session: Session = Depends(get_db),
) -> ProductoResponse:
    """Retorna los datos de un producto específico."""
    producto = session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto {producto_id} no encontrado.",
        )
    return ProductoResponse.model_validate(producto)


@router.put(
    "/product/{producto_id}",
    response_model=ProductoResponse,
    summary="Editar producto",
    tags=["Productos"],
)
def update_product(
    producto_id: int,
    data: ProductoUpdate,
    session: Session = Depends(get_db),
) -> ProductoResponse:
    """Actualiza los datos de un producto existente."""
    producto = session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto {producto_id} no encontrado.",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(producto, field, value)

    producto.actualizado_en = datetime.now()
    session.flush()
    session.refresh(producto)
    logger.info("Producto %d actualizado: %s", producto_id, update_data)
    return ProductoResponse.model_validate(producto)


@router.delete(
    "/product/{producto_id}",
    response_model=MessageResponse,
    summary="Eliminar producto",
    tags=["Productos"],
)
def delete_product(
    producto_id: int,
    session: Session = Depends(get_db),
) -> MessageResponse:
    """Elimina un producto y todo su historial."""
    producto = session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto {producto_id} no encontrado.",
        )

    nombre = producto.nombre
    session.delete(producto)
    logger.info("Producto %d eliminado: %s", producto_id, nombre)
    return MessageResponse(
        message=f"Producto '{nombre}' eliminado correctamente.",
        success=True,
    )


# ─── Historial ────────────────────────────────────────────────────────────────

@router.get(
    "/product/{producto_id}/history",
    response_model=list[HistorialResponse],
    summary="Historial de precios",
    tags=["Historial"],
)
def get_product_history(
    producto_id: int,
    limit: int = Query(100, ge=1, le=1000),
    session: Session = Depends(get_db),
) -> list[HistorialResponse]:
    """Retorna el historial de precios de un producto."""
    producto = session.get(Producto, producto_id)
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto {producto_id} no encontrado.",
        )

    historial = (
        session.query(Historial)
        .filter(Historial.producto_id == producto_id)
        .order_by(Historial.fecha.desc())
        .limit(limit)
        .all()
    )
    return [HistorialResponse.model_validate(h) for h in historial]


@router.get(
    "/history",
    response_model=list[HistorialResponse],
    summary="Historial completo",
    tags=["Historial"],
)
def get_all_history(
    limit: int = Query(200, ge=1, le=2000),
    session: Session = Depends(get_db),
) -> list[HistorialResponse]:
    """Retorna el historial de precios de todos los productos."""
    historial = (
        session.query(Historial)
        .order_by(Historial.fecha.desc())
        .limit(limit)
        .all()
    )
    return [HistorialResponse.model_validate(h) for h in historial]
