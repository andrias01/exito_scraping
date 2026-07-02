"""
Página de configuración del sistema.
Permite configurar notificaciones, frecuencia global y parámetros del scraper.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from config.settings import get_settings

st.set_page_config(
    page_title="Configuración | Monitor Éxito",
    page_icon="⚙️",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .page-header {
        background: linear-gradient(135deg, #805ad5 0%, #553c9a 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .page-header h2 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .page-header p { margin: 0.3rem 0 0 0; opacity: 0.85; }

    .config-section {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .config-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2d3748;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #805ad5;
    }
    .env-hint {
        background: #ebf8ff;
        border-left: 4px solid #3182ce;
        padding: 0.75rem 1rem;
        border-radius: 4px;
        font-size: 0.85rem;
        color: #2c5282;
        margin-top: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="page-header">
        <h2>⚙️ Configuración</h2>
        <p>Gestiona las notificaciones y parámetros del sistema</p>
    </div>
    """,
    unsafe_allow_html=True,
)

settings = get_settings()

# ─── Información del .env ─────────────────────────────────────────────────────

st.info(
    "💡 Las configuraciones se gestionan mediante el archivo **`.env`** en la raíz del proyecto. "
    "Edita ese archivo y reinicia el servidor para aplicar cambios. "
    "Abajo se muestra el estado actual de cada integración.",
    icon="ℹ️",
)

# ─── Estado de notificaciones ─────────────────────────────────────────────────

st.markdown("### 🔔 Estado de Notificaciones")

col_t, col_s, col_d = st.columns(3)

def status_icon(enabled: bool, configured: bool) -> str:
    if enabled and configured:
        return "🟢 **Activo**"
    elif not enabled:
        return "⚫ **Desactivado**"
    else:
        return "🟡 **Falta configurar**"

with col_t:
    tg_configured = bool(settings.telegram_bot_token and settings.telegram_chat_id)
    st.markdown(f"**Telegram**")
    st.markdown(status_icon(settings.telegram_enabled, tg_configured))
    st.caption(f"Token: {'✅' if settings.telegram_bot_token else '❌'}")
    st.caption(f"Chat ID: {'✅' if settings.telegram_chat_id else '❌'}")

with col_s:
    smtp_configured = bool(settings.smtp_host and settings.smtp_user and settings.smtp_to)
    st.markdown(f"**Email SMTP**")
    st.markdown(status_icon(settings.smtp_enabled, smtp_configured))
    st.caption(f"Host: {settings.smtp_host or '❌ No configurado'}")
    st.caption(f"Puerto: {settings.smtp_port}")

with col_d:
    dc_configured = bool(settings.discord_webhook_url)
    st.markdown(f"**Discord**")
    st.markdown(status_icon(settings.discord_enabled, dc_configured))
    st.caption(f"Webhook: {'✅' if settings.discord_webhook_url else '❌ No configurado'}")

# ─── Guía de configuración de Telegram ───────────────────────────────────────

st.markdown("---")
st.markdown("### 📖 Guía de Configuración")

with st.expander("📱 Telegram", expanded=False):
    st.markdown("""
    **Pasos para configurar Telegram:**

    1. Busca **@BotFather** en Telegram y crea un nuevo bot con `/newbot`
    2. Copia el **token del bot**
    3. Envía un mensaje al bot y visita: `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
    4. Copia el **chat_id** del resultado
    5. Agrega al archivo `.env`:

    ```env
    TELEGRAM_ENABLED=true
    TELEGRAM_BOT_TOKEN=tu_token_aqui
    TELEGRAM_CHAT_ID=tu_chat_id_aqui
    ```
    """)

with st.expander("📧 Correo SMTP (Gmail)", expanded=False):
    st.markdown("""
    **Pasos para configurar Gmail SMTP:**

    1. Ve a tu cuenta de Google → Seguridad → Verificación en 2 pasos (actívala)
    2. Busca **Contraseñas de aplicación** y genera una para "Correo"
    3. Copia esa contraseña de 16 caracteres
    4. Agrega al archivo `.env`:

    ```env
    SMTP_ENABLED=true
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=tu_correo@gmail.com
    SMTP_PASSWORD=tu_contraseña_de_aplicacion
    SMTP_FROM=tu_correo@gmail.com
    SMTP_TO=destino@gmail.com
    ```
    """)

with st.expander("💬 Discord", expanded=False):
    st.markdown("""
    **Pasos para configurar Discord:**

    1. En tu servidor Discord, edita el canal deseado
    2. Ve a **Integraciones → Webhooks → Nuevo Webhook**
    3. Copia la URL del webhook
    4. Agrega al archivo `.env`:

    ```env
    DISCORD_ENABLED=true
    DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
    ```
    """)

# ─── Parámetros actuales del sistema ─────────────────────────────────────────

st.markdown("---")
st.markdown("### 🔧 Parámetros Actuales del Sistema")

col_p1, col_p2 = st.columns(2)

with col_p1:
    st.markdown("**🕒 Monitoreo**")
    st.markdown(f"- Frecuencia por defecto: `{settings.default_frequency_minutes} min`")
    st.markdown(f"- Reintentos máximos: `{settings.max_retries}`")
    st.markdown(f"- Timeout scraper: `{settings.scraper_timeout // 1000}s`")
    st.markdown(f"- Delay entre reintentos: `{settings.scraper_retry_delay}s`")

with col_p2:
    st.markdown("**⚙️ Sistema**")
    st.markdown(f"- Modo headless: `{settings.scraper_headless}`")
    st.markdown(f"- Nivel de log: `{settings.log_level}`")
    st.markdown(f"- API Host: `{settings.api_host}:{settings.api_port}`")
    st.markdown(f"- Base de datos: `{settings.database_url}`")

# ─── Referencia .env ─────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### 📄 Referencia del archivo `.env`")

env_content = """# ────────────────────────────────────────
# Monitor Precios Éxito - Variables de entorno
# ────────────────────────────────────────

# Base de datos
DATABASE_URL=sqlite:///./database/monitor.db

# API
API_HOST=0.0.0.0
API_PORT=8000

# Scraper
SCRAPER_TIMEOUT=30000
SCRAPER_RETRIES=3
SCRAPER_RETRY_DELAY=5
SCRAPER_HEADLESS=true

# Monitoreo
DEFAULT_FREQUENCY_MINUTES=60
MAX_RETRIES=3

# Telegram
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# SMTP
SMTP_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_TO=

# Discord
DISCORD_ENABLED=false
DISCORD_WEBHOOK_URL=

# Logging
LOG_LEVEL=INFO
"""

st.code(env_content, language="ini")

col_copy, _ = st.columns([1, 3])
with col_copy:
    st.download_button(
        "📥 Descargar .env.example",
        env_content.encode("utf-8"),
        ".env.example",
        "text/plain",
    )

# ─── Prueba de conexión ───────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### 🧪 Probar Notificaciones")

col_test_t, col_test_s, col_test_d = st.columns(3)

with col_test_t:
    if st.button("📱 Probar Telegram", use_container_width=True):
        from notifications.telegram import TelegramNotifier
        notifier = TelegramNotifier()
        if notifier.test_connection():
            st.success("✅ Telegram conectado correctamente")
        else:
            st.error("❌ Fallo la conexión con Telegram")

with col_test_s:
    if st.button("📧 Probar SMTP", use_container_width=True):
        from notifications.smtp import SMTPNotifier
        notifier = SMTPNotifier()
        if notifier.test_connection():
            st.success("✅ SMTP conectado correctamente")
        else:
            st.error("❌ Fallo la conexión SMTP")

with col_test_d:
    if st.button("💬 Probar Discord", use_container_width=True):
        from notifications.discord import DiscordNotifier
        notifier = DiscordNotifier()
        if notifier.test_connection():
            st.success("✅ Discord conectado correctamente")
        else:
            st.error("❌ Fallo la conexión con Discord")
