"""
Página de gestión de productos.
Permite agregar, editar, eliminar, activar/desactivar y actualizar productos.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from utils.api_client import (
    api_create_product,
    api_delete_product,
    api_get_products,
    api_run_product,
    api_update_product,
    fmt_discount,
    fmt_price,
)

st.set_page_config(
    page_title="Productos | Monitor Éxito",
    page_icon="📦",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .page-header {
        background: linear-gradient(135deg, #2b6cb0 0%, #2c5282 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .page-header h2 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .page-header p { margin: 0.3rem 0 0 0; opacity: 0.85; }

    .product-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        transition: box-shadow 0.2s;
    }
    .product-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
    .product-name { font-size: 1rem; font-weight: 600; color: #2d3748; }
    .product-url { font-size: 0.8rem; color: #718096; word-break: break-all; }
    .price-badge { background: #e53e3e; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; }
    .discount-badge { background: #48bb78; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="page-header">
        <h2>📦 Gestión de Productos</h2>
        <p>Agrega, edita y administra los productos monitoreados</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Formulario agregar producto ──────────────────────────────────────────────

with st.expander("➕ Agregar Nuevo Producto", expanded=False):
    with st.form("form_agregar", clear_on_submit=True):
        st.markdown("**URL del Producto en Éxito**")
        url = st.text_input(
            "URL",
            placeholder="https://www.exito.com/producto/ejemplo",
            label_visibility="collapsed",
        )
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            precio_obj_normal = st.number_input(
                "Precio objetivo (normal)", min_value=0.0, value=0.0, step=1000.0,
                help="Recibe alerta cuando baje de este precio"
            )
        with col_f2:
            precio_obj_tarjeta = st.number_input(
                "Precio objetivo (tarjeta)", min_value=0.0, value=0.0, step=1000.0,
            )
        with col_f3:
            frecuencia = st.selectbox(
                "Frecuencia de monitoreo",
                options=[15, 30, 60, 120, 240, 480, 1440],
                format_func=lambda x: f"Cada {x} min" if x < 60 else f"Cada {x//60}h",
                index=2,
            )

        submitted = st.form_submit_button("🔍 Agregar y Escanear", type="primary")
        if submitted:
            if not url or "exito.com" not in url:
                st.error("Por favor ingresa una URL válida de exito.com")
            else:
                with st.spinner("Realizando scraping inicial del producto..."):
                    data = {
                        "url": url,
                        "precio_objetivo_normal": precio_obj_normal or None,
                        "precio_objetivo_tarjeta": precio_obj_tarjeta or None,
                        "frecuencia_minutos": frecuencia,
                        "activo": True,
                    }
                    result = api_create_product(data)
                    if result:
                        st.success(f"✅ Producto agregado: **{result['nombre']}**")
                        st.rerun()

st.markdown("---")

# ─── Filtros y búsqueda ───────────────────────────────────────────────────────

col_search, col_filter = st.columns([3, 1])
with col_search:
    busqueda = st.text_input(
        "🔍 Buscar producto",
        placeholder="Nombre, URL...",
        label_visibility="collapsed",
    )
with col_filter:
    filtro_estado = st.selectbox(
        "Estado",
        options=["Todos", "Activos", "Inactivos"],
        label_visibility="collapsed",
    )

# Cargar productos
activo_filter = None
if filtro_estado == "Activos":
    activo_filter = True
elif filtro_estado == "Inactivos":
    activo_filter = False

productos = api_get_products(activo=activo_filter, search=busqueda or None)

st.markdown(f"**{len(productos)} producto(s) encontrado(s)**")

# ─── Lista de productos ───────────────────────────────────────────────────────

if not productos:
    st.info("No se encontraron productos. Agrega el primero usando el formulario de arriba.")
else:
    for producto in productos:
        pid = producto["id"]
        nombre = producto.get("nombre", "Sin nombre")
        url = producto.get("url", "")
        activo = producto.get("activo", True)
        precio_normal = producto.get("ultimo_precio_normal")
        precio_tarjeta = producto.get("ultimo_precio_tarjeta")
        descuento = producto.get("descuento")
        disponible = producto.get("disponible")
        frecuencia = producto.get("frecuencia_minutos", 60)
        ultima_rev = producto.get("ultima_revision", "")[:16] if producto.get("ultima_revision") else "Nunca"

        with st.container():
            st.markdown(f'<div class="product-card">', unsafe_allow_html=True)

            col_info, col_precios, col_acciones = st.columns([4, 3, 3])

            with col_info:
                estado_icon = "🟢" if activo else "🔴"
                st.markdown(f'<div class="product-name">{estado_icon} {nombre[:70]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="product-url">{url[:80]}{"..." if len(url) > 80 else ""}</div>', unsafe_allow_html=True)
                st.caption(f"Frecuencia: {frecuencia} min | Última revisión: {ultima_rev}")

            with col_precios:
                st.markdown(f"**Normal:** {fmt_price(precio_normal)}")
                st.markdown(f"**Tarjeta:** {fmt_price(precio_tarjeta)}")
                if descuento:
                    st.markdown(f"**Descuento:** 🏷 {descuento:.1f}%")
                disp_text = "✅ Disponible" if disponible else ("❌ No disponible" if disponible is False else "❓ Desconocido")
                st.caption(disp_text)

            with col_acciones:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🔄", key=f"upd_{pid}", help="Actualizar precio ahora"):
                        with st.spinner("Actualizando..."):
                            r = api_run_product(pid)
                            if r and r.get("exitosos", 0) > 0:
                                st.success("✅")
                                st.rerun()
                            else:
                                st.error("❌")

                    toggle_label = "⏸ Desactivar" if activo else "▶ Activar"
                    if st.button(toggle_label, key=f"tog_{pid}", use_container_width=True):
                        api_update_product(pid, {"activo": not activo})
                        st.rerun()

                with c2:
                    if st.button("✏️", key=f"edit_{pid}", help="Editar producto"):
                        st.session_state[f"editing_{pid}"] = True

                    if st.button("🗑️", key=f"del_{pid}", help="Eliminar producto"):
                        st.session_state[f"confirm_del_{pid}"] = True

            # ── Formulario de edición ──────────────────────────────────────
            if st.session_state.get(f"editing_{pid}"):
                with st.form(f"form_edit_{pid}"):
                    st.markdown("**Editar producto**")
                    col_e1, col_e2, col_e3 = st.columns(3)
                    with col_e1:
                        new_obj_normal = st.number_input(
                            "Precio obj. normal",
                            value=float(producto.get("precio_objetivo_normal") or 0),
                            step=1000.0,
                        )
                    with col_e2:
                        new_obj_tarjeta = st.number_input(
                            "Precio obj. tarjeta",
                            value=float(producto.get("precio_objetivo_tarjeta") or 0),
                            step=1000.0,
                        )
                    with col_e3:
                        new_freq = st.selectbox(
                            "Frecuencia",
                            options=[15, 30, 60, 120, 240, 480, 1440],
                            index=[15, 30, 60, 120, 240, 480, 1440].index(frecuencia)
                            if frecuencia in [15, 30, 60, 120, 240, 480, 1440]
                            else 2,
                            format_func=lambda x: f"{x} min" if x < 60 else f"{x//60}h",
                        )
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.form_submit_button("💾 Guardar", type="primary"):
                            api_update_product(pid, {
                                "precio_objetivo_normal": new_obj_normal or None,
                                "precio_objetivo_tarjeta": new_obj_tarjeta or None,
                                "frecuencia_minutos": new_freq,
                            })
                            del st.session_state[f"editing_{pid}"]
                            st.success("✅ Guardado")
                            st.rerun()
                    with col_cancel:
                        if st.form_submit_button("✖ Cancelar"):
                            del st.session_state[f"editing_{pid}"]
                            st.rerun()

            # ── Confirmación de eliminación ────────────────────────────────
            if st.session_state.get(f"confirm_del_{pid}"):
                st.warning(f"⚠️ ¿Seguro que deseas eliminar **{nombre}**? Se perderá todo el historial.")
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("✅ Sí, eliminar", key=f"conf_del_{pid}", type="primary"):
                        result = api_delete_product(pid)
                        if result:
                            st.success(f"Producto eliminado: {nombre}")
                            del st.session_state[f"confirm_del_{pid}"]
                            st.rerun()
                with cc2:
                    if st.button("✖ Cancelar", key=f"cancel_del_{pid}"):
                        del st.session_state[f"confirm_del_{pid}"]
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

# ─── Actualizar todos ─────────────────────────────────────────────────────────

st.markdown("---")
if st.button("▶ Actualizar Todos los Productos", type="primary", use_container_width=True):
    with st.spinner("Monitoreando todos los productos activos..."):
        r = api_run_all()
        if r:
            st.success(
                f"✅ {r['exitosos']}/{r['productos_monitoreados']} productos actualizados "
                f"en {r['duracion_segundos']}s"
            )
            st.rerun()
