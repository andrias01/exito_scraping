"""
Inicia ambos servicios (FastAPI + Streamlit) en un solo contenedor Railway.
FastAPI corre en el PORT de Railway.
Streamlit corre en PORT+1 internamente.

Railway solo expone un puerto, así que ponemos Streamlit
detrás de FastAPI usando un reverse-proxy liviano.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Railway asigna PORT (normalmente 8080)
PORT = int(os.environ.get("PORT", "8080"))
STREAMLIT_PORT = PORT + 1  # puerto interno para Streamlit


def start_streamlit() -> None:
    """Arranca Streamlit en el puerto interno."""
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(ROOT / "app" / "Home.py"),
        "--server.port", str(STREAMLIT_PORT),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
        "--browser.gatherUsageStats", "false",
    ]
    subprocess.run(cmd, check=True)


def start_api() -> None:
    """Arranca FastAPI/uvicorn en el puerto principal."""
    import uvicorn
    from config.settings import configure_logging
    configure_logging()

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info",
    )


if __name__ == "__main__":
    # Streamlit en hilo background
    t = threading.Thread(target=start_streamlit, daemon=True)
    t.start()

    print(f"[startup] FastAPI iniciando en puerto {PORT}")
    print(f"[startup] Streamlit iniciando en puerto {STREAMLIT_PORT}")

    # Pequeña pausa para que Streamlit arranque
    time.sleep(3)

    # FastAPI en el hilo principal (bloquea hasta que muera)
    start_api()
