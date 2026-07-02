# 🛒 Monitor Precios Éxito Colombia

Sistema profesional de monitoreo automático de precios de productos de [Éxito Colombia](https://www.exito.com).

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.36-red?logo=streamlit)](https://streamlit.io)
[![Playwright](https://img.shields.io/badge/Playwright-1.44-orange?logo=playwright)](https://playwright.dev)
[![SQLite](https://img.shields.io/badge/SQLite-3-lightblue?logo=sqlite)](https://sqlite.org)

---

## 📋 Características

- 🔍 **Scraping automático** de precios normales y con Tarjeta Éxito
- 💾 **Historial completo** de todas las consultas (nunca se sobrescribe)
- 🔔 **Notificaciones** por Telegram, Email y Discord
- 📊 **Dashboard interactivo** con gráficas Plotly
- 🎯 **Alertas de precio objetivo** configurables por producto
- 🔄 **Reintentos automáticos** con backoff exponencial
- 🌐 **API REST** con FastAPI y documentación automática
- ⏰ **Google Apps Script** para mantener Streamlit activo
- 📱 Compatible con UptimeRobot, GitHub Actions y Cron Jobs

---

## 🗂️ Estructura del Proyecto

```
monitor-precios/
├── app/                        # Frontend Streamlit
│   ├── Home.py                 # Dashboard principal
│   └── pages/
│       ├── Productos.py        # Gestión de productos
│       ├── Historial.py        # Historial de precios
│       └── Configuracion.py   # Configuración del sistema
│
├── api/                        # Backend FastAPI
│   ├── main.py                 # App FastAPI principal
│   ├── routes.py               # Endpoints REST
│   └── schemas.py              # Esquemas Pydantic
│
├── scraper/
│   └── exito.py                # Scraper Playwright para Éxito
│
├── database/
│   ├── database.py             # Gestor SQLAlchemy + SQLite
│   └── models.py               # Modelos de base de datos
│
├── notifications/
│   ├── telegram.py             # Notificaciones Telegram
│   ├── smtp.py                 # Notificaciones Email
│   └── discord.py              # Notificaciones Discord
│
├── scheduler/
│   └── monitor_service.py      # Servicio de monitoreo central
│
├── config/
│   └── settings.py             # Configuración con Pydantic Settings
│
├── utils/
│   └── api_client.py           # Cliente HTTP para Streamlit
│
├── google_apps_script/
│   └── monitor.gs              # Script Google Apps Script
│
├── logs/                       # Archivos de log (auto-generado)
├── database/                   # Base de datos SQLite (auto-generado)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/usuario/monitor-precios.git
cd monitor-precios
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Instalar navegador Playwright

```bash
playwright install chromium
playwright install-deps chromium
```

### 5. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus valores
```

---

## ⚙️ Configuración

Edita el archivo `.env` en la raíz del proyecto:

### Variables de entorno

| Variable | Descripción | Por defecto |
|---|---|---|
| `DATABASE_URL` | URL de la base de datos SQLite | `sqlite:///./database/monitor.db` |
| `API_HOST` | Host del servidor FastAPI | `0.0.0.0` |
| `API_PORT` | Puerto del servidor FastAPI | `8000` |
| `SCRAPER_TIMEOUT` | Timeout del scraper (ms) | `30000` |
| `SCRAPER_RETRIES` | Reintentos en caso de fallo | `3` |
| `SCRAPER_HEADLESS` | Modo headless del navegador | `true` |
| `DEFAULT_FREQUENCY_MINUTES` | Frecuencia global de monitoreo | `60` |
| `TELEGRAM_ENABLED` | Activar notificaciones Telegram | `false` |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram | — |
| `TELEGRAM_CHAT_ID` | Chat ID de Telegram | — |
| `SMTP_ENABLED` | Activar notificaciones Email | `false` |
| `SMTP_HOST` | Servidor SMTP | `smtp.gmail.com` |
| `SMTP_USER` | Usuario SMTP | — |
| `SMTP_PASSWORD` | Contraseña SMTP | — |
| `DISCORD_ENABLED` | Activar notificaciones Discord | `false` |
| `DISCORD_WEBHOOK_URL` | URL del webhook de Discord | — |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

---

## 🖥️ Uso Local

### Iniciar la API (Terminal 1)

```bash
# Desde la raíz del proyecto
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

La documentación interactiva estará disponible en:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Iniciar Streamlit (Terminal 2)

```bash
streamlit run app/Home.py
```

La interfaz estará disponible en: http://localhost:8501

---

## 🌐 API REST

### Endpoints disponibles

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/health` | Verificar estado del sistema |
| `GET` | `/run` | Ejecutar monitoreo de todos los productos |
| `GET` | `/run?producto_id={id}` | Ejecutar monitoreo de un producto |
| `GET` | `/products` | Listar todos los productos |
| `GET` | `/products?activo=true` | Listar productos activos |
| `GET` | `/products?search=texto` | Buscar productos |
| `POST` | `/product` | Agregar nuevo producto |
| `GET` | `/product/{id}` | Obtener un producto |
| `PUT` | `/product/{id}` | Editar un producto |
| `DELETE` | `/product/{id}` | Eliminar un producto |
| `GET` | `/product/{id}/history` | Historial de un producto |
| `GET` | `/history` | Historial completo |

### Ejemplo: Agregar un producto

```bash
curl -X POST http://localhost:8000/product \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.exito.com/producto/ejemplo",
    "precio_objetivo_normal": 800000,
    "precio_objetivo_tarjeta": 700000,
    "frecuencia_minutos": 60
  }'
```

### Ejemplo: Ejecutar monitoreo

```bash
curl http://localhost:8000/run
```

---

## 🔔 Configuración de Notificaciones

### Telegram

1. Crea un bot con [@BotFather](https://t.me/BotFather): `/newbot`
2. Copia el token
3. Envía un mensaje al bot
4. Obtén el chat_id: `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. Configura en `.env`:

```env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=1234567890:ABCDEfghij...
TELEGRAM_CHAT_ID=123456789
```

### Discord

1. Edita el canal Discord → Integraciones → Webhooks → Nuevo Webhook
2. Copia la URL del webhook
3. Configura en `.env`:

```env
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Gmail SMTP

1. Activa la verificación en 2 pasos en tu cuenta Google
2. Genera una "Contraseña de aplicación" en la configuración de seguridad
3. Configura en `.env`:

```env
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD=xxxx_xxxx_xxxx_xxxx
SMTP_TO=destino@gmail.com
```

---

## ☁️ Despliegue en Streamlit Community Cloud

### 1. Subir a GitHub

```bash
git add .
git commit -m "Monitor Precios Éxito v1.0"
git push origin main
```

### 2. Configurar en Streamlit Cloud

1. Ve a [share.streamlit.io](https://share.streamlit.io)
2. Conecta tu repositorio
3. Configura `app/Home.py` como archivo principal
4. Agrega las variables de entorno en **Secrets** (formato TOML)

```toml
DATABASE_URL = "sqlite:///./database/monitor.db"
TELEGRAM_ENABLED = "true"
TELEGRAM_BOT_TOKEN = "tu_token"
TELEGRAM_CHAT_ID = "tu_chat_id"
# ... resto de variables
```

> ⚠️ **Nota:** Streamlit Community Cloud suspende la app cuando no hay usuarios activos. Usa Google Apps Script o UptimeRobot para mantenerla activa.

---

## ⏰ Google Apps Script (Monitoreo Automático)

El archivo `google_apps_script/monitor.gs` mantiene la aplicación activa y ejecuta el monitoreo automáticamente.

### Configuración

1. Abre [script.google.com](https://script.google.com)
2. Crea un nuevo proyecto
3. Pega el contenido de `monitor.gs`
4. Cambia `APP_URL` por tu URL de Streamlit
5. Ejecuta `setupTrigger()` **una sola vez**

### Características del script

- ✅ Trigger automático cada 30 minutos (configurable)
- 🔄 Reintentos con backoff exponencial
- 📊 Logs en Google Sheets
- 📧 Alertas por email ante fallos
- 💤 Despierta la app antes de ejecutar el monitoreo
- 🎛️ Menú personalizado en Google Sheets

---

## 🛠️ Mantener Streamlit Activo

### Opción 1: UptimeRobot (Recomendado gratis)

1. Crea cuenta en [uptimerobot.com](https://uptimerobot.com)
2. Nuevo monitor → HTTP(s)
3. URL: `https://tu-app.streamlit.app/health`
4. Intervalo: 5 minutos

### Opción 2: GitHub Actions

Crea `.github/workflows/keepalive.yml`:

```yaml
name: Keep Alive
on:
  schedule:
    - cron: '*/15 * * * *'
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping app
        run: |
          curl -f https://tu-app.streamlit.app/health
          curl -f https://tu-app.streamlit.app/run
```

### Opción 3: Cron Job (servidor propio)

```bash
# Agregar al crontab
*/30 * * * * curl -s https://tu-app.streamlit.app/run >> /var/log/monitor.log
```

---

## 🔬 Playwright

### Instalación del navegador

```bash
# Instalar Chromium
playwright install chromium

# Instalar dependencias del sistema (Linux)
playwright install-deps chromium
```

### Configuración para servidor sin GUI

```env
SCRAPER_HEADLESS=true
```

### Depuración (ver el navegador)

```env
SCRAPER_HEADLESS=false
SCRAPER_SLOW_MO=500
```

---

## 📐 Arquitectura

```
┌─────────────────────────────────────────┐
│          Frontend (Streamlit)           │
│  Dashboard │ Productos │ Historial │ Config │
└─────────────────┬───────────────────────┘
                  │ HTTP REST
┌─────────────────▼───────────────────────┐
│           Backend (FastAPI)             │
│    /health │ /run │ /products │ /history │
└──────┬──────────────────────────────────┘
       │                        │
┌──────▼──────┐        ┌────────▼────────┐
│   Scraper   │        │   SQLite DB     │
│ (Playwright)│        │   SQLAlchemy    │
└──────┬──────┘        └─────────────────┘
       │
┌──────▼──────────────────────────────────┐
│            Notificaciones               │
│  Telegram │ Email SMTP │ Discord        │
└─────────────────────────────────────────┘
```

---

## 🧪 Verificación del sistema

```bash
# Verificar que la API está funcionando
curl http://localhost:8000/health

# Ejecutar monitoreo manual
curl http://localhost:8000/run

# Listar productos
curl http://localhost:8000/products
```

---

## 📝 Logs

Los logs se guardan en `logs/monitor.log` y también se imprimen en consola.

Para cambiar el nivel de detalle:

```env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

---

## 🤝 Contribuciones

1. Fork del repositorio
2. Crea tu branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'Agrega nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Abre un Pull Request

---

## 📜 Licencia

MIT License - ver [LICENSE](LICENSE) para detalles.

---

*Desarrollado con ❤️ para monitorear precios de Éxito Colombia*
