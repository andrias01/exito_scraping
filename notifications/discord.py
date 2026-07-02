"""
Notificador de Discord usando Webhooks.
Envía mensajes enriquecidos (embeds) cuando hay cambios de precio.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import requests

from config.settings import get_settings

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Envía notificaciones a Discord mediante webhooks."""

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def _enabled(self) -> bool:
        return (
            self._settings.discord_enabled
            and bool(self._settings.discord_webhook_url)
        )

    def send_embed(self, payload: dict) -> bool:
        """
        Envía un mensaje embed a Discord.

        Args:
            payload: Diccionario con la estructura del embed de Discord.

        Returns:
            True si el envío fue exitoso.
        """
        if not self._enabled:
            logger.debug("Discord desactivado, omitiendo notificación.")
            return False

        try:
            response = requests.post(
                self._settings.discord_webhook_url,  # type: ignore[arg-type]
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            logger.info("Notificación Discord enviada correctamente.")
            return True
        except requests.RequestException as exc:
            logger.error("Error enviando mensaje a Discord: %s", exc)
            return False

    def send_price_alert(
        self,
        producto_nombre: str,
        precio_anterior: Optional[float],
        precio_nuevo: Optional[float],
        tipo_precio: str,
        ahorro: Optional[float],
        url: str,
        fecha: str,
    ) -> bool:
        """Envía alerta de cambio de precio a Discord con embed enriquecido."""
        precio_ant_fmt = (
            f"${precio_anterior:,.0f}".replace(",", ".") if precio_anterior else "N/A"
        )
        precio_nvo_fmt = (
            f"${precio_nuevo:,.0f}".replace(",", ".") if precio_nuevo else "N/A"
        )
        ahorro_fmt = (
            f"${ahorro:,.0f}".replace(",", ".") if ahorro else "N/A"
        )

        baja = (precio_nuevo or 0) < (precio_anterior or 0)
        color = 0x38A169 if baja else 0xE53E3E  # verde o rojo
        emoji = "🔻" if baja else "🔺"

        payload = {
            "username": "Monitor Éxito",
            "avatar_url": "https://www.exito.com/favicon.ico",
            "embeds": [
                {
                    "title": f"{emoji} Alerta de Precio - {producto_nombre[:100]}",
                    "url": url,
                    "color": color,
                    "fields": [
                        {
                            "name": "💰 Tipo de Precio",
                            "value": tipo_precio,
                            "inline": True,
                        },
                        {
                            "name": "📉 Precio Anterior",
                            "value": f"~~{precio_ant_fmt}~~",
                            "inline": True,
                        },
                        {
                            "name": "✅ Precio Nuevo",
                            "value": f"**{precio_nvo_fmt}**",
                            "inline": True,
                        },
                        {
                            "name": "💵 Ahorro",
                            "value": ahorro_fmt,
                            "inline": True,
                        },
                        {
                            "name": "📅 Fecha",
                            "value": fecha,
                            "inline": True,
                        },
                    ],
                    "footer": {
                        "text": "Monitor Precios Éxito Colombia",
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        }

        return self.send_embed(payload)

    def send_target_alert(
        self,
        producto_nombre: str,
        precio_actual: float,
        precio_objetivo: float,
        tipo_precio: str,
        url: str,
    ) -> bool:
        """Envía alerta cuando un producto alcanza el precio objetivo."""
        precio_act_fmt = f"${precio_actual:,.0f}".replace(",", ".")
        precio_obj_fmt = f"${precio_objetivo:,.0f}".replace(",", ".")

        payload = {
            "username": "Monitor Éxito",
            "embeds": [
                {
                    "title": f"🎯 ¡Precio Objetivo Alcanzado! - {producto_nombre[:100]}",
                    "url": url,
                    "color": 0xF6AD55,  # naranja/dorado
                    "description": "¡El producto ha alcanzado tu precio objetivo!",
                    "fields": [
                        {
                            "name": "💰 Tipo de Precio",
                            "value": tipo_precio,
                            "inline": True,
                        },
                        {
                            "name": "✅ Precio Actual",
                            "value": f"**{precio_act_fmt}**",
                            "inline": True,
                        },
                        {
                            "name": "🎯 Precio Objetivo",
                            "value": precio_obj_fmt,
                            "inline": True,
                        },
                    ],
                    "footer": {"text": "Monitor Precios Éxito Colombia"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        }

        return self.send_embed(payload)

    def test_connection(self) -> bool:
        """Prueba la conexión con el webhook de Discord."""
        if not self._enabled:
            return False
        payload = {
            "content": "✅ Conexión con Monitor Precios Éxito establecida correctamente.",
        }
        return self.send_embed(payload)
