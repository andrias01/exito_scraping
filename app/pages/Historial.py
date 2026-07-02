"""
Página de historial de precios.
Muestra gráficas de evolución, estadísticas y tabla de registros.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.api_client import (
    api_get_history,
    api_get_products,
    fmt_price,
)

st.set_page_config(
    page_title="Historial | Monitor Éxito",
    page_icon="📈",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .page-header {
        background: linear-gradient(135deg, #38a169 0%, #276749 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .page-header h2 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .page-header p { margin: 0.3rem 0 0 0; opacity: 0.85; }

    .stat-card {
        background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        color: white;
    }
    .stat-value { font-size: 1.8rem; font-weight: 700; color: #68d391; }
    .stat-label { font-size: 0.8rem; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.05em; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="page-header">
        <h2>📈 Historial de Precios</h2>
        <p>Evolución histórica, estadísticas y análisis de precios</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Selector de producto ─────────────────────────────────────────────────────

productos = api_get_products()

if not productos:
    st.info("👈 No hay productos registrados. Ve a la sección **Productos** para agregar uno.")
    st.stop()

opciones = {f"{p['id']} · {p['nombre'][:60]}": p["id"] for p in productos}
seleccion = st.selectbox(
    "Selecciona un producto",
    options=list(opciones.keys()),
    label_visibility="visible",
)

producto_id = opciones[seleccion]
producto_info = next((p for p in productos if p["id"] == producto_id), None)

col_limit, col_period = st.columns(2)
with col_limit:
    limit = st.selectbox(
        "Cantidad de registros",
        options=[50, 100, 200, 500, 1000],
        index=1,
    )
with col_period:
    periodo = st.selectbox(
        "Período",
        options=["Todos", "Últimos 7 días", "Últimos 30 días", "Último mes"],
    )

# ─── Cargar historial ─────────────────────────────────────────────────────────

historial = api_get_history(producto_id, limit=limit)

if not historial:
    st.info("No hay registros en el historial para este producto. Ejecuta un monitoreo primero.")
    st.stop()

df = pd.DataFrame(historial)
df["fecha"] = pd.to_datetime(df["fecha"])
df = df.sort_values("fecha")

# Filtrar por período
if periodo == "Últimos 7 días":
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=7)
    df = df[df["fecha"] >= cutoff]
elif periodo == "Últimos 30 días":
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
    df = df[df["fecha"] >= cutoff]
elif periodo == "Último mes":
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
    df = df[df["fecha"] >= cutoff]

st.markdown(f"**{len(df)} registro(s)** para el período seleccionado")

# ─── Estadísticas ─────────────────────────────────────────────────────────────

df_precios = df.dropna(subset=["precio_normal"])

if not df_precios.empty:
    precio_min = df_precios["precio_normal"].min()
    precio_max = df_precios["precio_normal"].max()
    precio_avg = df_precios["precio_normal"].mean()
    variacion = precio_max - precio_min
    precio_actual = df_precios.iloc[-1]["precio_normal"]

    col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
    stats = [
        (col_s1, fmt_price(precio_actual), "Precio Actual"),
        (col_s2, fmt_price(precio_min), "Precio Mínimo"),
        (col_s3, fmt_price(precio_max), "Precio Máximo"),
        (col_s4, fmt_price(precio_avg), "Promedio"),
        (col_s5, fmt_price(variacion), "Variación"),
    ]
    for col, value, label in stats:
        with col:
            st.markdown(
                f"""<div class="stat-card">
                    <div class="stat-value">{value}</div>
                    <div class="stat-label">{label}</div>
                </div>""",
                unsafe_allow_html=True,
            )

st.markdown("---")

# ─── Gráficas ─────────────────────────────────────────────────────────────────

# Gráfico de evolución de precios
st.markdown("#### 📊 Evolución de Precios")

fig = go.Figure()

if "precio_normal" in df.columns:
    df_normal = df.dropna(subset=["precio_normal"])
    if not df_normal.empty:
        fig.add_trace(go.Scatter(
            x=df_normal["fecha"],
            y=df_normal["precio_normal"],
            name="Precio Normal",
            line=dict(color="#e53e3e", width=2),
            mode="lines+markers",
            marker=dict(size=5),
        ))

if "precio_tarjeta" in df.columns:
    df_tarjeta = df.dropna(subset=["precio_tarjeta"])
    if not df_tarjeta.empty:
        fig.add_trace(go.Scatter(
            x=df_tarjeta["fecha"],
            y=df_tarjeta["precio_tarjeta"],
            name="Precio Tarjeta Éxito",
            line=dict(color="#3182ce", width=2, dash="dash"),
            mode="lines+markers",
            marker=dict(size=5),
        ))

fig.update_layout(
    title="Evolución de Precios en el Tiempo",
    xaxis_title="Fecha",
    yaxis_title="Precio (COP)",
    template="plotly_white",
    font=dict(family="Inter"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# Gráfico de descuento
if "descuento" in df.columns:
    df_desc = df.dropna(subset=["descuento"])
    if not df_desc.empty and df_desc["descuento"].sum() > 0:
        fig_desc = px.bar(
            df_desc,
            x="fecha",
            y="descuento",
            title="Descuento a lo largo del tiempo (%)",
            color_discrete_sequence=["#48bb78"],
            template="plotly_white",
        )
        fig_desc.update_layout(
            font=dict(family="Inter"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_desc, use_container_width=True)

# ─── Gráficos por período ─────────────────────────────────────────────────────

st.markdown("#### 📅 Análisis por Período")
tab_dia, tab_sem, tab_mes = st.tabs(["Diario", "Semanal", "Mensual"])

df_agg_base = df.dropna(subset=["precio_normal"]).copy()

with tab_dia:
    if not df_agg_base.empty:
        df_dia = df_agg_base.set_index("fecha").resample("D").agg({
            "precio_normal": ["min", "max", "mean"],
        }).reset_index()
        df_dia.columns = ["fecha", "minimo", "maximo", "promedio"]
        fig_dia = px.line(
            df_dia, x="fecha", y=["minimo", "maximo", "promedio"],
            title="Precio diario (Min / Max / Promedio)",
            color_discrete_sequence=["#48bb78", "#e53e3e", "#3182ce"],
            template="plotly_white",
        )
        fig_dia.update_layout(font=dict(family="Inter"))
        st.plotly_chart(fig_dia, use_container_width=True)

with tab_sem:
    if not df_agg_base.empty:
        df_sem = df_agg_base.set_index("fecha").resample("W").agg({
            "precio_normal": ["min", "max", "mean"],
        }).reset_index()
        df_sem.columns = ["fecha", "minimo", "maximo", "promedio"]
        fig_sem = px.line(
            df_sem, x="fecha", y=["minimo", "maximo", "promedio"],
            title="Precio semanal (Min / Max / Promedio)",
            color_discrete_sequence=["#48bb78", "#e53e3e", "#3182ce"],
            template="plotly_white",
        )
        fig_sem.update_layout(font=dict(family="Inter"))
        st.plotly_chart(fig_sem, use_container_width=True)

with tab_mes:
    if not df_agg_base.empty:
        df_mes = df_agg_base.set_index("fecha").resample("ME").agg({
            "precio_normal": ["min", "max", "mean"],
        }).reset_index()
        df_mes.columns = ["fecha", "minimo", "maximo", "promedio"]
        fig_mes = px.bar(
            df_mes, x="fecha", y="promedio",
            title="Precio promedio mensual",
            color_discrete_sequence=["#3182ce"],
            template="plotly_white",
        )
        fig_mes.update_layout(font=dict(family="Inter"))
        st.plotly_chart(fig_mes, use_container_width=True)

# ─── Tabla de datos ───────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("#### 📋 Tabla de Registros")

df_display = df.copy()
df_display["precio_normal"] = df_display["precio_normal"].apply(
    lambda x: fmt_price(x) if pd.notna(x) else "N/A"
)
df_display["precio_tarjeta"] = df_display["precio_tarjeta"].apply(
    lambda x: fmt_price(x) if pd.notna(x) else "N/A"
)
df_display["descuento"] = df_display["descuento"].apply(
    lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
)
df_display["disponible"] = df_display["disponible"].apply(
    lambda x: "✅" if x else ("❌" if x is False else "—")
)
df_display["fecha"] = df_display["fecha"].dt.strftime("%Y-%m-%d %H:%M")

cols_show = ["id", "fecha", "precio_normal", "precio_tarjeta", "descuento", "disponible", "error"]
cols_show = [c for c in cols_show if c in df_display.columns]

st.dataframe(df_display[cols_show], use_container_width=True, hide_index=True)

# Exportar
col_e1, col_e2, _ = st.columns([1, 1, 4])
csv = df[cols_show].to_csv(index=False).encode("utf-8")
with col_e1:
    st.download_button("📥 CSV", csv, "historial.csv", "text/csv")
