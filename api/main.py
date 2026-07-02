"""
Punto de entrada de la API FastAPI.
Configura la aplicación, middlewares y rutas.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router
from config.settings import configure_logging, get_settings
from database.database import db_manager

# Configurar logging al inicio
configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

# ─── Inicialización de la aplicación ─────────────────────────────────────────

app = FastAPI(
    title="Monitor Precios Éxito Colombia",
    description=(
        "API REST para monitorear automáticamente los precios de productos "
        "de Éxito Colombia. Soporta notificaciones por Telegram, Email y Discord."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Monitor Precios",
        "url": "https://github.com/usuario/monitor-precios",
    },
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configurar dominios específicos en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Rutas ────────────────────────────────────────────────────────────────────

app.include_router(router)


# ─── Eventos del ciclo de vida ────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup() -> None:
    """Inicializa la base de datos al arrancar."""
    logger.info("Iniciando Monitor Precios Éxito Colombia API v1.0.0")
    db_manager.initialize()
    logger.info("API lista en http://%s:%d", settings.api_host, settings.api_port)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Limpieza al apagar el servidor."""
    logger.info("Apagando Monitor Precios API.")


# ─── Manejadores de excepciones ───────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """Maneja excepciones no capturadas."""
    logger.error("Error no manejado: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Error interno del servidor", "detail": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
