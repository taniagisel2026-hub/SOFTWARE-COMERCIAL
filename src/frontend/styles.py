import streamlit as st


def aplicar_estilos() -> None:
    st.markdown("""
    <style>
    /* ── Sidebar ─────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        min-width: 260px;
        background: linear-gradient(180deg, #1B3A6B 0%, #0F2347 100%);
    }
    [data-testid="stSidebar"] * { color: #E8EEF7 !important; }
    [data-testid="stSidebar"] .stRadio label { color: #CBD5E1 !important; font-size: 14px; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15); }

    /* ── Contenido principal ──────────────────────────────────── */
    .main .block-container { padding-top: 1.5rem; max-width: 1200px; }
    h1 { color: #1B3A6B; font-size: 1.6rem !important; font-weight: 700; }
    h2 { color: #1B3A6B; font-size: 1.2rem !important; }
    h3 { color: #374151; font-size: 1rem !important; }

    /* ── Tarjetas KPI ─────────────────────────────────────────── */
    .kpi-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 20px 24px;
        border-left: 5px solid #1B3A6B;
        box-shadow: 0 1px 6px rgba(0,0,0,0.07);
        margin-bottom: 8px;
    }
    .kpi-card .kpi-icon  { font-size: 22px; margin-bottom: 6px; }
    .kpi-card .kpi-value { font-size: 32px; font-weight: 800; color: #1B3A6B; line-height: 1; }
    .kpi-card .kpi-label { font-size: 12px; color: #6B7280; margin-top: 4px; text-transform: uppercase; letter-spacing: .5px; }
    .kpi-card .kpi-delta { font-size: 12px; color: #10B981; margin-top: 4px; font-weight: 600; }
    .kpi-card .kpi-delta.neg { color: #EF4444; }

    /* ── Badges de estado ─────────────────────────────────────── */
    .badge {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 11px; font-weight: 600; letter-spacing: .3px;
    }
    .badge-nuevo           { background: #DBEAFE; color: #1D4ED8; }
    .badge-seguimiento     { background: #FEF3C7; color: #92400E; }
    .badge-cotizacion      { background: #EDE9FE; color: #5B21B6; }
    .badge-negociacion     { background: #FFEDD5; color: #C2410C; }
    .badge-ganado          { background: #D1FAE5; color: #065F46; }
    .badge-perdido         { background: #FEE2E2; color: #991B1B; }
    .badge-optout          { background: #F3F4F6; color: #6B7280; }

    /* ── Sección de resultados ────────────────────────────────── */
    .resultado-box {
        background: #EEF2F9; border-radius: 8px; padding: 20px;
        border-left: 5px solid #E65C00; margin: 12px 0;
    }
    .resultado-box .res-num { font-size: 48px; font-weight: 900; color: #1B3A6B; }
    .resultado-box .res-label { font-size: 14px; color: #374151; }

    /* ── Log en vivo ──────────────────────────────────────────── */
    .log-area {
        background: #0F172A; color: #94A3B8; font-family: monospace;
        font-size: 12px; border-radius: 6px; padding: 12px;
        max-height: 240px; overflow-y: auto;
    }

    /* ── Botón primario personalizado ─────────────────────────── */
    .stButton > button[kind="primary"] {
        background: #E65C00 !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)
