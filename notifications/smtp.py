"""
Notificador por correo electrónico usando SMTP.
Compatible con Gmail, Outlook y servidores SMTP personalizados.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from config.settings import get_settings

logger = logging.getLogger(__name__)


class SMTPNotifier:
    """Envía notificaciones por correo electrónico mediante SMTP."""

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def _enabled(self) -> bool:
        return (
            self._settings.smtp_enabled
            and bool(self._settings.smtp_host)
            and bool(self._settings.smtp_user)
            and bool(self._settings.smtp_password)
            and bool(self._settings.smtp_to)
        )

    def _build_connection(self) -> smtplib.SMTP:
        """Establece conexión SMTP con TLS."""
        smtp = smtplib.SMTP(
            self._settings.smtp_host,  # type: ignore[arg-type]
            self._settings.smtp_port,
        )
        smtp.ehlo()
        smtp.starttls()
        smtp.login(
            self._settings.smtp_user,  # type: ignore[arg-type]
            self._settings.smtp_password,  # type: ignore[arg-type]
        )
        return smtp

    def send_email(self, subject: str, body_html: str, body_text: str = "") -> bool:
        """
        Envía un correo electrónico.

        Args:
            subject: Asunto del correo.
            body_html: Cuerpo en formato HTML.
            body_text: Cuerpo en texto plano (fallback).

        Returns:
            True si el envío fue exitoso.
        """
        if not self._enabled:
            logger.debug("SMTP desactivado, omitiendo notificación.")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._settings.smtp_from or self._settings.smtp_user  # type: ignore[assignment]
        msg["To"] = self._settings.smtp_to  # type: ignore[assignment]

        if body_text:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            with self._build_connection() as smtp:
                smtp.sendmail(
                    msg["From"],
                    [self._settings.smtp_to],  # type: ignore[list-item]
                    msg.as_string(),
                )
            logger.info("Email enviado correctamente a %s", self._settings.smtp_to)
            return True
        except smtplib.SMTPException as exc:
            logger.error("Error enviando email: %s", exc)
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
        """Envía alerta de cambio de precio por correo."""
        precio_ant_fmt = (
            f"${precio_anterior:,.0f}".replace(",", ".") if precio_anterior else "N/A"
        )
        precio_nvo_fmt = (
            f"${precio_nuevo:,.0f}".replace(",", ".") if precio_nuevo else "N/A"
        )
        ahorro_fmt = (
            f"${ahorro:,.0f}".replace(",", ".") if ahorro else "N/A"
        )

        subject = f"🛒 Alerta de Precio: {producto_nombre[:50]}"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #e53e3e, #fc8181); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <h1 style="color: white; margin: 0; font-size: 24px;">🛒 Alerta de Precio</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0;">Éxito Colombia</p>
            </div>
            <div style="background: #f7fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0;">
                <h2 style="color: #2d3748; margin-top: 0;">{producto_nombre}</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; color: #718096; font-weight: bold;">Tipo de precio</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; color: #2d3748;">{tipo_precio}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; color: #718096; font-weight: bold;">Precio anterior</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; color: #e53e3e; text-decoration: line-through;">{precio_ant_fmt}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; color: #718096; font-weight: bold;">Precio nuevo</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; color: #38a169; font-size: 20px; font-weight: bold;">{precio_nvo_fmt}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; color: #718096; font-weight: bold;">Ahorro</td>
                        <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; color: #2d3748;">{ahorro_fmt}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; color: #718096; font-weight: bold;">Fecha</td>
                        <td style="padding: 10px; color: #2d3748;">{fecha}</td>
                    </tr>
                </table>
                <div style="margin-top: 20px; text-align: center;">
                    <a href="{url}" style="background: #e53e3e; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block;">
                        Ver Producto en Éxito
                    </a>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = (
            f"Alerta de Precio - Éxito Colombia\n\n"
            f"Producto: {producto_nombre}\n"
            f"Tipo: {tipo_precio}\n"
            f"Precio anterior: {precio_ant_fmt}\n"
            f"Precio nuevo: {precio_nvo_fmt}\n"
            f"Ahorro: {ahorro_fmt}\n"
            f"Fecha: {fecha}\n"
            f"URL: {url}"
        )

        return self.send_email(subject, body_html, body_text)

    def test_connection(self) -> bool:
        """Prueba la conexión SMTP."""
        if not self._enabled:
            return False
        try:
            with self._build_connection():
                pass
            logger.info("Conexión SMTP exitosa con %s:%d", self._settings.smtp_host, self._settings.smtp_port)
            return True
        except smtplib.SMTPException as exc:
            logger.error("Error de conexión SMTP: %s", exc)
            return False
