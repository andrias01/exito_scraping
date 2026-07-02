"""
Página Home / Dashboard principal de Streamlit.
Muestra un resumen del sistema con métricas y gráficas.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Agregar el directorio raíz al path de Python
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.api_client import (
    api_get_all_history,
    api_get_products,
    api_health,
    api_run_all,
    fmt_discount,
    fmt_price,
)

# ─── Configuración de la página ───────────────────────────────────────────────

st.set_page_config(
    page_title="Monitor Precios Éxito | Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Estilos CSS ──────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #e53e3e 0%, #c53030 50%, #9b2c2c 100%);
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 10px 40px rgba(229, 62, 62, 0.3);
    }

    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.02em;
    }

    .main-header p {
        font-size: 1.1rem;
        opacity: 0.9;
        margin: 0.5rem 0 0 0;
    }

    .metric-card {
        background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        color: white;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        transition: transform 0.2s ease;
    }

    .metric-card:hover {
        transform: translateY(-2px);
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #fc8181;
        line-height: 1;
    }

    .metric-label {
        font-size: 0.875rem;
        color: #a0aec0;
        margin-top: 0.5rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .status-ok { background: #c6f6d5; color: #22543d; }
    .status-error { background: #fed7d7; color: #742a2a; }

    .section-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #2d3748;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e53e3e;
    }

    .producto-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        transition: box-shadow 0.2s ease;
    }

    .producto-card:hover {
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── Header ──────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="main-header">
        <h1>🛒 Monitor Precios Éxito</h1>
        <p>Sistema profesional de monitoreo de precios en tiempo real</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Estado del sistema ───────────────────────────────────────────────────────

col_status, col_run = st.columns([3, 1])

with col_status:
    health = api_health()
    if health:
        st.markdown(
            f'<span class="status-badge status-ok">🟢 API Online · {health.get("timestamp", "")[:19]}</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="status-badge status-error">🔴 API Offline</span>',
            unsafe_allow_html=True,
        )

with col_run:
    if st.button("▶ Actualizar Todos", type="primary", use_container_width=True):
        with st.spinner("Ejecutando monitoreo de todos los productos..."):
            result = api_run_all()
            if result:
                st.success(
                    f"✅ Completado: {result['exitosos']}/{result['productos_monitoreados']} "
                    f"exitosos en {result['duracion_segundos']}s"
                )
                st.rerun()

st.markdown("---")

# ─── Cargar datos ─────────────────────────────────────────────────────────────

productos = api_get_products()
historial = api_get_all_history(limit=500)

# ─── Métricas principales ─────────────────────────────────────────────────────

total = len(productos)
activos = sum(1 for p in productos if p.get("activo"))
con_descuento = sum(1 for p in productos if p.get("descuento") and p["descuento"] > 0)
no_disponibles = sum(1 for p in productos if p.get("disponible") is False)

revisados_hoy = 0
if historial:
    from datetime import date
    hoy = date.today().isoformat()
    revisados_hoy = sum(1 for h in historial if h.get("fecha", "").startswith(hoy))

col1, col2, col3, col4, col5 = st.columns(5)

metrics = [
    (col1, str(total), "Total Productos"),
    (col2, str(activos), "Activos"),
    (col3, str(con_descuento), "Con Descuento"),
    (col4, str(no_disponibles), "Sin Stock"),
    (col5, str(revisados_hoy), "Revisados Hoy"),
]

for col, value, label in metrics:
    with col:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("---")

# ─── Gráficas ─────────────────────────────────────────────────────────────────

if historial:
    df_hist = pd.DataFrame(historial)
    df_hist["fecha"] = pd.to_datetime(df_hist["fecha"])

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown('<div class="section-title">📊 Evolución de Precios (Últimos 30 días)</div>', unsafe_allow_html=True)

        if productos:
            # Tomar el primero con historial para mostrar
            df_con_precios = df_hist.dropna(subset=["precio_normal"])
            if not df_con_precios.empty:
                fig = px.line(
                    df_con_precios,
                    x="fecha",
                    y="precio_normal",
                    color="producto_id",
                    title="",
                    color_discrete_sequence=px.colors.qualitative.Bold,
                    template="plotly_white",
                )
                fig.update_layout(
                    showlegend=True,
                    legend_title_text="Producto ID",
                    xaxis_title="Fecha",
                    yaxis_title="Precio (COP)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter"),
                )
                fig.update_traces(line_width=2)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos de precios en el historial.")
        else:
            st.info("Agrega productos para ver la evolución de precios.")

    with col_g2:
        st.markdown('<div class="section-title">🥧 Distribución por Estado</div>', unsafe_allow_html=True)

        estado_data = {
            "Activos": activos,
            "Inactivos": total - activos,
            "Con Descuento": con_descuento,
            "Sin Stock": no_disponibles,
        }
        estado_data = {k: v for k, v in estado_data.items() if v > 0}

        if estado_data:
            fig_pie = px.pie(
                values=list(estado_data.values()),
                names=list(estado_data.keys()),
                color_discrete_sequence=["#e53e3e", "#fc8181", "#f6ad55", "#68d391"],
                template="plotly_white",
            )
            fig_pie.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter"),
                showlegend=True,
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Sin datos suficientes para mostrar la distribución.")

else:
    st.info("📭 No hay datos en el historial. Agrega productos y ejecuta el monitoreo.")

# ─── Tabla de productos recientes ─────────────────────────────────────────────

st.markdown("---")
st.markdown('<div class="section-title">📦 Productos Monitoreados</div>', unsafe_allow_html=True)

if productos:
    rows = []
    for p in productos:
        rows.append({
            "ID": p["id"],
            "Nombre": p["nombre"][:60] + ("..." if len(p.get("nombre", "")) > 60 else ""),
            "Precio Normal": fmt_price(p.get("ultimo_precio_normal")),
            "Precio Tarjeta": fmt_price(p.get("ultimo_precio_tarjeta")),
            "Descuento": fmt_discount(p.get("descuento")),
            "Disponible": "✅" if p.get("disponible") else ("❌" if p.get("disponible") is False else "—"),
            "Activo": "🟢" if p.get("activo") else "🔴",
            "Última revisión": (p.get("ultima_revision", "")[:16] if p.get("ultima_revision") else "Nunca"),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Exportar
    col_exp1, col_exp2, _ = st.columns([1, 1, 4])
    with col_exp1:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Exportar CSV", csv, "productos.csv", "text/csv")
    with col_exp2:
        try:
            import io
            output = io.BytesIO()
            df.to_excel(output, index=False)
            st.download_button(
                "📥 Exportar Excel",
                output.getvalue(),
                "productos.xlsx",
                "application/vnd.ms-excel",
            )
        except ImportError:
            st.caption("Instala openpyxl para exportar Excel")
else:
    st.info("👈 Ve a **Productos** para agregar tu primer producto a monitorear.")
