"""
Panel de Control Comercial — Medina SST Empresarial SAS
Ejecutar: streamlit run app.py
"""
import sys
from pathlib import Path

# Asegura que src/ sea encontrado como paquete desde cualquier directorio
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

st.set_page_config(
    page_title="Medina SST — Panel Comercial",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Panel Comercial · Medina SST Empresarial SAS · v1.0.0"
    },
)

from src.frontend.styles import aplicar_estilos
from src.frontend.pages import dashboard, cotizador, scraper, campanas, analitica, contenido

aplicar_estilos()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:12px 0 4px;">
        <div style="font-size:32px;">🏢</div>
        <div style="font-size:16px;font-weight:800;color:#FFFFFF;letter-spacing:-0.3px;">
            Medina SST
        </div>
        <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:1px;">
            Panel Comercial
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    pagina = st.radio(
        "Navegación",
        options=[
            "📊 Panel de Control",
            "🧮 Cotizador",
            "🕵️ Motor de Prospección",
            "✉️ Campañas y Habeas Data",
            "📈 Analítica y Conversión",
            "🎨 Fábrica de Contenido",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown("""
    <div style="font-size:10px;color:#64748B;text-align:center;padding-bottom:8px;">
        Resolución 0312/2019<br>
        Ley 1581/2012 · Decreto 472/2015<br><br>
        <span style="color:#475569;">v1.0.0 · MVP Fases 1–4</span>
    </div>
    """, unsafe_allow_html=True)

# ── Enrutamiento de páginas ────────────────────────────────────────────────────
if pagina == "📊 Panel de Control":
    dashboard.render()
elif pagina == "🧮 Cotizador":
    cotizador.render()
elif pagina == "🕵️ Motor de Prospección":
    scraper.render()
elif pagina == "✉️ Campañas y Habeas Data":
    campanas.render()
elif pagina == "📈 Analítica y Conversión":
    analitica.render()
elif pagina == "🎨 Fábrica de Contenido":
    contenido.render()
