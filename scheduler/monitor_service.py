"""
Servicio principal de monitoreo.
Orquesta el scraping, almacenamiento y notificaciones.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from config.settings import get_settings
from database.database import db_manager
from database.models import Historial, Producto
from notifications.discord import DiscordNotifier
from notifications.smtp import SMTPNotifier
from notifications.telegram import TelegramNotifier
from scraper.exito import ExitoScraper, ProductoScraped

logger = logging.getLogger(__name__)


class MonitorService:
    """
    Servicio de monitoreo de precios.
    Coordina scraping → almacenamiento → comparación → notificaciones.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._telegram = TelegramNotifier()
        self._smtp = SMTPNotifier()
        self._discord = DiscordNotifier()

    def _save_historial(
        self,
        session: Session,
        producto: Producto,
        scraped: ProductoScraped,
    ) -> Historial:
        """Guarda un registro en el historial de precios."""
        entry = Historial(
            producto_id=producto.id,
            fecha=datetime.now(),
            precio_normal=scraped.precio_normal,
            precio_tarjeta=scraped.precio_tarjeta,
            disponible=scraped.disponible,
            descuento=scraped.descuento,
            error=scraped.error,
        )
        session.add(entry)
        logger.debug(
            "Historial guardado para producto %d: normal=%s tarjeta=%s",
            producto.id,
            scraped.precio_normal,
            scraped.precio_tarjeta,
        )
        return entry

    def _update_product(
        self,
        session: Session,
        producto: Producto,
        scraped: ProductoScraped,
    ) -> None:
        """Actualiza los datos del producto con los valores del scraping."""
        if scraped.nombre and scraped.nombre != producto.nombre:
            producto.nombre = scraped.nombre
        if scraped.imagen_url:
            producto.imagen_url = scraped.imagen_url

        producto.ultimo_precio_normal = scraped.precio_normal
        producto.ultimo_precio_tarjeta = scraped.precio_tarjeta
        producto.descuento = scraped.descuento
        producto.disponible = scraped.disponible
        producto.ultima_revision = datetime.now()

    def _check_and_notify(
        self,
        producto: Producto,
        scraped: ProductoScraped,
        precio_normal_anterior: Optional[float],
        precio_tarjeta_anterior: Optional[float],
    ) -> None:
        """Compara precios y dispara notificaciones si corresponde."""
        fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")

        # ── Bajó precio normal ─────────────────────────────────────────────
        if (
            scraped.precio_normal
            and precio_normal_anterior
            and scraped.precio_normal < precio_normal_anterior
        ):
            ahorro = precio_normal_anterior - scraped.precio_normal
            logger.info(
                "Precio normal bajó: %s -> %s (ahorro: %s)",
                precio_normal_anterior,
                scraped.precio_normal,
                ahorro,
            )
            self._send_all_price_alerts(
                producto_nombre=producto.nombre,
                precio_anterior=precio_normal_anterior,
                precio_nuevo=scraped.precio_normal,
                tipo_precio="Precio Normal",
                ahorro=ahorro,
                url=producto.url,
                fecha=fecha_str,
            )

        # ── Bajó precio tarjeta ────────────────────────────────────────────
        if (
            scraped.precio_tarjeta
            and precio_tarjeta_anterior
            and scraped.precio_tarjeta < precio_tarjeta_anterior
        ):
            ahorro = precio_tarjeta_anterior - scraped.precio_tarjeta
            logger.info(
                "Precio tarjeta bajó: %s -> %s (ahorro: %s)",
                precio_tarjeta_anterior,
                scraped.precio_tarjeta,
                ahorro,
            )
            self._send_all_price_alerts(
                producto_nombre=producto.nombre,
                precio_anterior=precio_tarjeta_anterior,
                precio_nuevo=scraped.precio_tarjeta,
                tipo_precio="Precio Tarjeta Éxito",
                ahorro=ahorro,
                url=producto.url,
                fecha=fecha_str,
            )

        # ── Alcanzó precio objetivo normal ─────────────────────────────────
        if (
            producto.precio_objetivo_normal
            and scraped.precio_normal
            and scraped.precio_normal <= producto.precio_objetivo_normal
        ):
            logger.info(
                "Precio objetivo normal alcanzado: %s <= %s",
                scraped.precio_normal,
                producto.precio_objetivo_normal,
            )
            self._telegram.send_target_alert(
                producto.nombre,
                scraped.precio_normal,
                producto.precio_objetivo_normal,
                "Precio Normal",
                producto.url,
            )
            self._discord.send_target_alert(
                producto.nombre,
                scraped.precio_normal,
                producto.precio_objetivo_normal,
                "Precio Normal",
                producto.url,
            )

        # ── Alcanzó precio objetivo tarjeta ────────────────────────────────
        if (
            producto.precio_objetivo_tarjeta
            and scraped.precio_tarjeta
            and scraped.precio_tarjeta <= producto.precio_objetivo_tarjeta
        ):
            logger.info(
                "Precio objetivo tarjeta alcanzado: %s <= %s",
                scraped.precio_tarjeta,
                producto.precio_objetivo_tarjeta,
            )
            self._telegram.send_target_alert(
                producto.nombre,
                scraped.precio_tarjeta,
                producto.precio_objetivo_tarjeta,
                "Precio Tarjeta Éxito",
                producto.url,
            )
            self._discord.send_target_alert(
                producto.nombre,
                scraped.precio_tarjeta,
                producto.precio_objetivo_tarjeta,
                "Precio Tarjeta Éxito",
                producto.url,
            )

    def _send_all_price_alerts(
        self,
        producto_nombre: str,
        precio_anterior: Optional[float],
        precio_nuevo: Optional[float],
        tipo_precio: str,
        ahorro: Optional[float],
        url: str,
        fecha: str,
    ) -> None:
        """Envía la alerta por todos los canales configurados."""
        self._telegram.send_price_alert(
            producto_nombre, precio_anterior, precio_nuevo,
            tipo_precio, ahorro, url, fecha,
        )
        self._smtp.send_price_alert(
            producto_nombre, precio_anterior, precio_nuevo,
            tipo_precio, ahorro, url, fecha,
        )
        self._discord.send_price_alert(
            producto_nombre, precio_anterior, precio_nuevo,
            tipo_precio, ahorro, url, fecha,
        )

    async def monitor_product(self, producto_id: int) -> dict:
        """
        Monitorea un producto específico.

        Args:
            producto_id: ID del producto en la base de datos.

        Returns:
            Diccionario con el resultado del monitoreo.
        """
        with db_manager.get_session() as session:
            producto = session.get(Producto, producto_id)
            if not producto:
                logger.error("Producto %d no encontrado.", producto_id)
                return {"success": False, "error": "Producto no encontrado"}

            if not producto.activo:
                logger.info("Producto %d inactivo, omitiendo.", producto_id)
                return {"success": False, "error": "Producto inactivo"}

            # Guardar precios anteriores antes de actualizar
            precio_normal_ant = producto.ultimo_precio_normal
            precio_tarjeta_ant = producto.ultimo_precio_tarjeta

            async with ExitoScraper() as scraper:
                scraped = await scraper.scrape_url(producto.url)

            # Guardar historial siempre (incluso si hay error)
            self._save_historial(session, producto, scraped)

            if scraped.exitoso:
                self._check_and_notify(producto, scraped, precio_normal_ant, precio_tarjeta_ant)
                self._update_product(session, producto, scraped)
                logger.info("Producto %d monitoreado exitosamente.", producto_id)
                return {
                    "success": True,
                    "producto_id": producto_id,
                    "nombre": producto.nombre,
                    "precio_normal": scraped.precio_normal,
                    "precio_tarjeta": scraped.precio_tarjeta,
                    "descuento": scraped.descuento,
                    "disponible": scraped.disponible,
                }
            else:
                logger.warning(
                    "Scraping fallido para producto %d: %s",
                    producto_id,
                    scraped.error,
                )
                return {
                    "success": False,
                    "producto_id": producto_id,
                    "error": scraped.error,
                }

    async def monitor_all(self) -> list[dict]:
        """
        Monitorea todos los productos activos secuencialmente.
        Reutiliza el navegador para mayor eficiencia.
        """
        with db_manager.get_session() as session:
            productos = (
                session.query(Producto)
                .filter(Producto.activo == True)  # noqa: E712
                .all()
            )

        if not productos:
            logger.info("No hay productos activos para monitorear.")
            return []

        logger.info("Iniciando monitoreo de %d productos activos.", len(productos))
        results: list[dict] = []

        async with ExitoScraper() as scraper:
            for producto in productos:
                with db_manager.get_session() as session:
                    p = session.get(Producto, producto.id)
                    if not p:
                        continue

                    precio_normal_ant = p.ultimo_precio_normal
                    precio_tarjeta_ant = p.ultimo_precio_tarjeta

                    scraped = await scraper.scrape_url(p.url)
                    self._save_historial(session, p, scraped)

                    if scraped.exitoso:
                        self._check_and_notify(p, scraped, precio_normal_ant, precio_tarjeta_ant)
                        self._update_product(session, p, scraped)
                        results.append({
                            "success": True,
                            "producto_id": p.id,
                            "nombre": p.nombre,
                            "precio_normal": scraped.precio_normal,
                            "precio_tarjeta": scraped.precio_tarjeta,
                        })
                    else:
                        results.append({
                            "success": False,
                            "producto_id": p.id,
                            "error": scraped.error,
                        })

        exitosos = sum(1 for r in results if r["success"])
        logger.info(
            "Monitoreo completado: %d/%d exitosos.", exitosos, len(results)
        )
        return results
