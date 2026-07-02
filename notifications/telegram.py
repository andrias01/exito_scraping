"""
Notificador de Telegram usando la Bot API.
Envía mensajes cuando hay cambios relevantes en precios.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

from config.settings import get_settings

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Envía notificaciones a Telegram mediante la Bot API."""

    BASE_URL = "https://api.telegram.org/bot{token}"

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def _enabled(self) -> bool:
        return (
            self._settings.telegram_enabled
            and bool(self._settings.telegram_bot_token)
            and bool(self._settings.telegram_chat_id)
        )

    def _build_url(self, endpoint: str) -> str:
        base = self.BASE_URL.format(token=self._settings.telegram_bot_token)
        return f"{base}/{endpoint}"

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Envía un mensaje al chat configurado.

        Args:
            message: Texto del mensaje (soporta HTML).
            parse_mode: 'HTML' o 'Markdown'.

        Returns:
            True si el envío fue exitoso.
        """
        if not self._enabled:
            logger.debug("Telegram desactivado, omitiendo notificación.")
            return False

        try:
            response = requests.post(
                self._build_url("sendMessage"),
                json={
                    "chat_id": self._settings.telegram_chat_id,
                    "text": message,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": False,
                },
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Notificación Telegram enviada correctamente.")
            return True
        except requests.RequestException as exc:
            logger.error("Error enviando mensaje a Telegram: %s", exc)
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
        """Envía alerta de cambio de precio formateada."""
        precio_ant_fmt = (
            f"${precio_anterior:,.0f}".replace(",", ".") if precio_anterior else "N/A"
        )
        precio_nvo_fmt = (
            f"${precio_nuevo:,.0f}".replace(",", ".") if precio_nuevo else "N/A"
        )
        ahorro_fmt = (
            f"${ahorro:,.0f}".replace(",", ".") if ahorro else "N/A"
        )

        arrow = "🔻" if (precio_nuevo or 0) < (precio_anterior or 0) else "🔺"

        message = (
            f"🛒 <b>Alerta de Precio - Éxito</b>\n\n"
            f"📦 <b>Producto:</b> {producto_nombre}\n"
            f"💰 <b>Tipo:</b> {tipo_precio}\n"
            f"{arrow} <b>Precio anterior:</b> {precio_ant_fmt}\n"
            f"✅ <b>Precio nuevo:</b> {precio_nvo_fmt}\n"
            f"💵 <b>Ahorro:</b> {ahorro_fmt}\n"
            f"📅 <b>Fecha:</b> {fecha}\n"
            f"🔗 <a href='{url}'>Ver producto</a>"
        )
        return self.send_message(message)

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

        message = (
            f"🎯 <b>¡Precio Objetivo Alcanzado! - Éxito</b>\n\n"
            f"📦 <b>Producto:</b> {producto_nombre}\n"
            f"💰 <b>Tipo:</b> {tipo_precio}\n"
            f"✅ <b>Precio actual:</b> {precio_act_fmt}\n"
            f"🎯 <b>Precio objetivo:</b> {precio_obj_fmt}\n"
            f"🔗 <a href='{url}'>¡Comprar ahora!</a>"
        )
        return self.send_message(message)

    def test_connection(self) -> bool:
        """Prueba la conexión con la Bot API."""
        if not self._enabled:
            return False
        try:
            response = requests.get(
                self._build_url("getMe"),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            logger.info("Telegram conectado: @%s", data.get("result", {}).get("username"))
            return True
        except requests.RequestException as exc:
            logger.error("Error probando Telegram: %s", exc)
            return False
