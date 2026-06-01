import streamlit as st


def tarjeta_kpi(
    label: str,
    valor: str,
    delta: str = "",
    icono: str = "📊",
    color: str = "#1B3A6B",
    delta_negativo: bool = False,
) -> None:
    delta_class = "kpi-delta neg" if delta_negativo else "kpi-delta"
    delta_html = f'<div class="{delta_class}">{delta}</div>' if delta else ""
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color:{color};">
        <div class="kpi-icon">{icono}</div>
        <div class="kpi-value">{valor}</div>
        <div class="kpi-label">{label}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def badge_estado(estado: str) -> str:
    mapa = {
        "NUEVO":              ("badge-nuevo",       "🔵 Nuevo"),
        "EN_SEGUIMIENTO":     ("badge-seguimiento", "🟡 En seguimiento"),
        "COTIZACION_ENVIADA": ("badge-cotizacion",  "🟣 Cotización enviada"),
        "NEGOCIACION":        ("badge-negociacion", "🟠 Negociación"),
        "CERRADO_GANADO":     ("badge-ganado",      "🟢 Cerrado ✓"),
        "CERRADO_PERDIDO":    ("badge-perdido",      "🔴 Perdido"),
    }
    css, texto = mapa.get(estado, ("badge-optout", estado))
    return f'<span class="badge {css}">{texto}</span>'


def separador_seccion(titulo: str) -> None:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin:18px 0 10px;">
        <div style="flex:1;height:1px;background:#E5E7EB;"></div>
        <span style="font-size:11px;font-weight:700;color:#9CA3AF;
                     text-transform:uppercase;letter-spacing:1px;white-space:nowrap;">
            {titulo}
        </span>
        <div style="flex:1;height:1px;background:#E5E7EB;"></div>
    </div>
    """, unsafe_allow_html=True)
