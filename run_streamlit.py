"""
Punto de entrada para Streamlit en Railway.
Lanza Streamlit usando el PORT asignado por Railway.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

port = os.environ.get("PORT", "8501")

subprocess.run(
    [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(ROOT / "app" / "Home.py"),
        "--server.port", port,
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
        "--browser.gatherUsageStats", "false",
    ],
    check=True,
)
