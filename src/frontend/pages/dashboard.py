import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..components.metrics import separador_seccion, tarjeta_kpi

_ROOT = Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Orden y etiquetas del embudo de ventas
_ETAPAS = [
    ("NUEVO",              "Leads Nuevos"),
    ("EN_SEGUIMIENTO",     "Contactados"),
    ("COTIZACION_ENVIADA", "Cotización Enviada"),
    ("NEGOCIACION",        "En Negociación"),
    ("CERRADO_GANADO",     "Cierre"),
]
_COLORES_EMBUDO = ["#1B3A6B", "#2D5896", "#4A7CC2", "#E65C00", "#10B981"]


@st.cache_data(ttl=30)
def _cargar_datos() -> dict:
    """Consulta la BD y retorna datos serializables. Cachea 30 segundos."""
    try:
        from sqlalchemy import func
        from src.database.connection import get_session
        from src.database.models import Cotizacion, EmpresaProspecto, HistorialInteracciones

        with get_session() as session:
            # Conteo por estado (excluyendo opt-out)
            estados_raw = (
                session.query(
                    EmpresaProspecto.estado_prospecto,
                    func.count(EmpresaProspecto.id_empresa),
                )
                .filter(EmpresaProspecto.opt_out == False)
                .group_by(EmpresaProspecto.estado_prospecto)
                .all()
            )
            estados = {k: v for k, v in estados_raw}

            total_prospectos = (
                session.query(EmpresaProspecto)
                .filter(EmpresaProspecto.opt_out == False)
                .count()
            )
            total_cotizaciones = session.query(Cotizacion).count()
            total_emails = (
                session.query(HistorialInteracciones)
                .filter(
                    HistorialInteracciones.canal == "EMAIL",
                    HistorialInteracciones.estado_respuesta == "ENVIADO",
                )
                .count()
            )
            total_abiertos = (
                session.query(HistorialInteracciones)
                .filter(HistorialInteracciones.estado_respuesta == "ABIERTO")
                .count()
            )

            # KPI: % prospectos que llegaron a cotización o más
            estados_conversion = ["COTIZACION_ENVIADA", "NEGOCIACION",
                                   "CERRADO_GANADO", "CERRADO_PERDIDO"]
            total_convertidos = (
                session.query(EmpresaProspecto)
                .filter(
                    EmpresaProspecto.opt_out == False,
                    EmpresaProspecto.estado_prospecto.in_(estados_conversion),
                )
                .count()
            )

            # KPI: promedio de días desde registro hasta primera cotización (SQLite)
            primera_cot = (
                session.query(
                    Cotizacion.id_empresa,
                    func.min(Cotizacion.fecha_emision).label("primera"),
                )
                .group_by(Cotizacion.id_empresa)
                .subquery()
            )
            avg_dias_raw = (
                session.query(
                    func.avg(
                        func.julianday(primera_cot.c.primera)
                        - func.julianday(EmpresaProspecto.fecha_registro)
                    )
                )
                .join(primera_cot,
                      EmpresaProspecto.id_empresa == primera_cot.c.id_empresa)
                .scalar()
            )
            avg_dias_cotizacion = round(float(avg_dias_raw), 1) if avg_dias_raw else None

            # Distribución por ciudad (top 8)
            por_ciudad = (
                session.query(
                    EmpresaProspecto.ciudad,
                    func.count(EmpresaProspecto.id_empresa),
                )
                .filter(EmpresaProspecto.opt_out == False)
                .group_by(EmpresaProspecto.ciudad)
                .order_by(func.count(EmpresaProspecto.id_empresa).desc())
                .limit(8)
                .all()
            )

            # Actividad reciente
            recientes = (
                session.query(
                    HistorialInteracciones,
                    EmpresaProspecto.razon_social,
                )
                .join(EmpresaProspecto,
                      HistorialInteracciones.id_empresa == EmpresaProspecto.id_empresa)
                .order_by(HistorialInteracciones.fecha_interaccion.desc())
                .limit(6)
                .all()
            )
            actividad = [
                {
                    "empresa":   rs,
                    "tipo":      h.tipo_interaccion,
                    "canal":     h.canal or "",
                    "asunto":    (h.asunto or "")[:60],
                    "fecha":     h.fecha_interaccion.strftime("%d/%m %H:%M"),
                    "estado":    h.estado_respuesta or "",
                }
                for h, rs in recientes
            ]

        return {
            "ok": True,
            "estados": estados,
            "total_prospectos": total_prospectos,
            "total_cotizaciones": total_cotizaciones,
            "total_emails": total_emails,
            "total_abiertos": total_abiertos,
            "total_convertidos": total_convertidos,
            "avg_dias_cotizacion": avg_dias_cotizacion,
            "total_cerrados": estados.get("CERRADO_GANADO", 0),
            "por_ciudad": [{"Ciudad": c, "Prospectos": n} for c, n in por_ciudad],
            "actividad": actividad,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def render() -> None:
    col_titulo, col_refresh = st.columns([6, 1])
    col_titulo.title("📊 Panel de Control")
    if col_refresh.button("🔄 Actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption("Métricas en tiempo real · Medina SST Empresarial SAS")

    datos = _cargar_datos()

    # ── Estado de la BD ────────────────────────────────────────────────────────
    if not datos["ok"]:
        st.error(f"No se pudo conectar a la base de datos: `{datos['error']}`")
        st.info(
            "**Inicializa el esquema ejecutando:**\n"
            "```bash\npython -m src.database.init_db\n```"
        )
        return

    if datos["total_prospectos"] == 0:
        st.info(
            "📭 La base de datos está vacía. "
            "Usa el **Motor de Prospección** para extraer tus primeros prospectos "
            "o añade empresas desde el **Cotizador**."
        )

    # ── KPIs fila 1: volumen ───────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        tarjeta_kpi("Total Prospectos", str(datos["total_prospectos"]),
                    icono="🏢", color="#1B3A6B")
    with c2:
        tarjeta_kpi("Cotizaciones", str(datos["total_cotizaciones"]),
                    icono="📄", color="#E65C00")
    with c3:
        tarjeta_kpi("Emails Enviados", str(datos["total_emails"]),
                    icono="📬", color="#7C3AED")
    with c4:
        tarjeta_kpi("Cierres Ganados", str(datos["total_cerrados"]),
                    icono="✅", color="#10B981")

    # ── KPIs fila 2: rendimiento (KPIs del PDF) ────────────────────────────────
    import os
    total_emails   = datos["total_emails"]
    total_abiertos = datos["total_abiertos"]
    total_conv     = datos["total_convertidos"]
    total_prosp    = datos["total_prospectos"]
    avg_dias       = datos["avg_dias_cotizacion"]
    cerrados       = datos["total_cerrados"]

    open_rate  = f"{total_abiertos/total_emails*100:.1f}%" if total_emails else "—"
    conv_rate  = f"{total_conv/total_prosp*100:.1f}%" if total_prosp else "—"
    vel_cot    = f"{avg_dias} días" if avg_dias is not None else "< 3 min"

    # ROI: configurable vía .env
    valor_cto  = float(os.getenv("VALOR_CONTRATO_PROMEDIO_COP", "0") or 0)
    costo_dev  = float(os.getenv("COSTO_DESARROLLO_SOFTWARE_COP", "0") or 0)
    if valor_cto > 0 and costo_dev > 0:
        ingresos = cerrados * valor_cto
        roi_val  = (ingresos - costo_dev) / costo_dev * 100
        roi_str  = f"{roi_val:+.0f}%"
    elif valor_cto > 0:
        roi_str  = f"$ {cerrados * valor_cto:,.0f}".replace(",", ".")
    else:
        roi_str  = "Configura .env"

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        tarjeta_kpi(
            "Open Rate correos",
            open_rate,
            icono="👁️",
            color="#1D4ED8" if total_abiertos else "#94A3B8",
        )
    with k2:
        tarjeta_kpi(
            "Conversión a cotización",
            conv_rate,
            icono="📊",
            color="#7C3AED",
        )
    with k3:
        tarjeta_kpi(
            "Velocidad cotización",
            vel_cot,
            icono="⚡",
            color="#10B981",
        )
    with k4:
        tarjeta_kpi(
            "ROI / Ingresos CRM",
            roi_str,
            icono="💰",
            color="#E65C00",
        )

    st.divider()

    # ── Embudo + Ciudades ──────────────────────────────────────────────────────
    col_embudo, col_ciudades = st.columns([3, 2])

    with col_embudo:
        separador_seccion("Embudo de ventas — datos reales")
        valores = [datos["estados"].get(clave, 0) for clave, _ in _ETAPAS]
        etiquetas = [label for _, label in _ETAPAS]

        fig_funnel = go.Figure(go.Funnel(
            y=etiquetas,
            x=valores,
            textposition="inside",
            textinfo="value+percent initial",
            marker=dict(color=_COLORES_EMBUDO),
            connector=dict(line=dict(color="#E5E7EB", width=1)),
        ))
        fig_funnel.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="sans-serif", size=13),
        )
        st.plotly_chart(fig_funnel, use_container_width=True)

    with col_ciudades:
        separador_seccion("Prospectos por ciudad")
        if datos["por_ciudad"]:
            df_c = pd.DataFrame(datos["por_ciudad"])
            fig_bar = go.Figure(go.Bar(
                x=df_c["Prospectos"],
                y=df_c["Ciudad"],
                orientation="h",
                marker_color="#1B3A6B",
                text=df_c["Prospectos"],
                textposition="outside",
            ))
            fig_bar.update_layout(
                margin=dict(l=0, r=30, t=10, b=0),
                height=320,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(tickfont=dict(size=12)),
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Sin datos de ciudades aún.")

    # ── Actividad reciente ────────────────────────────────────────────────────
    separador_seccion("Actividad reciente del CRM")
    if datos["actividad"]:
        for item in datos["actividad"]:
            icono = "📧" if item["canal"] == "EMAIL" else "💬" if item["canal"] == "WHATSAPP" else "🔔"
            c1, c2, c3 = st.columns([3, 3, 1])
            c1.markdown(f"**{item['empresa']}**")
            c2.markdown(
                f"<small style='color:#6B7280;'>{icono} {item['tipo']} "
                f"{'· ' + item['asunto'] if item['asunto'] else ''}</small>",
                unsafe_allow_html=True,
            )
            estado_color = "#10B981" if item["estado"] == "ENVIADO" else "#EF4444"
            c3.markdown(
                f"<small style='color:{estado_color};'>{item['fecha']}</small>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Aún no hay interacciones registradas. Los correos enviados aparecerán aquí.")
