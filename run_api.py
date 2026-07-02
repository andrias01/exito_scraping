"""
Punto de entrada para Railway.
Inicia la API FastAPI con uvicorn.
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al PYTHONPATH
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import uvicorn
from config.settings import configure_logging, get_settings

configure_logging()
settings = get_settings()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.api_port))
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        log_level=settings.log_level.lower(),
    )
