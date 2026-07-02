"""
Utilidades para interactuar con la API REST desde Streamlit.
Maneja todas las llamadas HTTP al backend FastAPI.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import requests
import os

import streamlit as st

logger = logging.getLogger(__name__)

# En Railway: API_URL apunta al servicio FastAPI (ej: https://mi-api.railway.app)
# En local: usa localhost:8000
API_BASE = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")


def _get(endpoint: str, params: Optional[dict] = None) -> Optional[Any]:
    """Realiza una petición GET a la API."""
    try:
        response = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError:
        st.error("❌ No se puede conectar con la API. Asegúrate de que el servidor está corriendo.")
        return None
    except requests.HTTPError as exc:
        st.error(f"❌ Error HTTP: {exc.response.status_code} - {exc.response.text}")
        return None
    except Exception as exc:
        st.error(f"❌ Error inesperado: {exc}")
        return None


def _post(endpoint: str, data: dict) -> Optional[Any]:
    """Realiza una petición POST a la API."""
    try:
        response = requests.post(f"{API_BASE}{endpoint}", json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError:
        st.error("❌ No se puede conectar con la API.")
        return None
    except requests.HTTPError as exc:
        detail = exc.response.json().get("detail", exc.response.text)
        st.error(f"❌ Error: {detail}")
        return None
    except Exception as exc:
        st.error(f"❌ Error inesperado: {exc}")
        return None


def _put(endpoint: str, data: dict) -> Optional[Any]:
    """Realiza una petición PUT a la API."""
    try:
        response = requests.put(f"{API_BASE}{endpoint}", json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError:
        st.error("❌ No se puede conectar con la API.")
        return None
    except requests.HTTPError as exc:
        detail = exc.response.json().get("detail", exc.response.text)
        st.error(f"❌ Error: {detail}")
        return None
    except Exception as exc:
        st.error(f"❌ Error inesperado: {exc}")
        return None


def _delete(endpoint: str) -> Optional[Any]:
    """Realiza una petición DELETE a la API."""
    try:
        response = requests.delete(f"{API_BASE}{endpoint}", timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError:
        st.error("❌ No se puede conectar con la API.")
        return None
    except requests.HTTPError as exc:
        detail = exc.response.json().get("detail", exc.response.text)
        st.error(f"❌ Error: {detail}")
        return None
    except Exception as exc:
        st.error(f"❌ Error inesperado: {exc}")
        return None


# ─── Funciones de API ─────────────────────────────────────────────────────────

def api_health() -> Optional[dict]:
    return _get("/health")


def api_run_all() -> Optional[dict]:
    return _get("/run")


def api_run_product(producto_id: int) -> Optional[dict]:
    return _get("/run", params={"producto_id": producto_id})


def api_get_products(activo: Optional[bool] = None, search: Optional[str] = None) -> list[dict]:
    params: dict = {}
    if activo is not None:
        params["activo"] = activo
    if search:
        params["search"] = search
    result = _get("/products", params=params)
    return result or []


def api_get_product(producto_id: int) -> Optional[dict]:
    return _get(f"/product/{producto_id}")


def api_create_product(data: dict) -> Optional[dict]:
    return _post("/product", data)


def api_update_product(producto_id: int, data: dict) -> Optional[dict]:
    return _put(f"/product/{producto_id}", data)


def api_delete_product(producto_id: int) -> Optional[dict]:
    return _delete(f"/product/{producto_id}")


def api_get_history(producto_id: int, limit: int = 100) -> list[dict]:
    result = _get(f"/product/{producto_id}/history", params={"limit": limit})
    return result or []


def api_get_all_history(limit: int = 200) -> list[dict]:
    result = _get("/history", params={"limit": limit})
    return result or []


# ─── Formateo ─────────────────────────────────────────────────────────────────

def fmt_price(price: Optional[float]) -> str:
    """Formatea un precio en formato colombiano."""
    if price is None:
        return "N/A"
    return f"${price:,.0f}".replace(",", ".")


def fmt_discount(discount: Optional[float]) -> str:
    """Formatea un porcentaje de descuento."""
    if discount is None:
        return "—"
    return f"{discount:.1f}%"
