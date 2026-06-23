"""
Módulo 4 — Auditor de Conversión y Optimización Continua.
Métricas de tasa de apertura, clics, respuestas y conversión del pipeline.
Optimización asistida por IA de los asuntos de correo.
"""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..components.metrics import separador_seccion, tarjeta_kpi

_ROOT = Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_ETAPAS_ORDEN = [
    "NUEVO",
    "EN_SEGUIMIENTO",
    "COTIZACION_ENVIADA",
    "NEGOCIACION",
    "CERRADO_GANADO",
    "CERRADO_PERDIDO",
]
_ETAPA_LABEL = {
    "NUEVO":              "Leads Nuevos",
    "EN_SEGUIMIENTO":     "Contactados",
    "COTIZACION_ENVIADA": "Cotización Enviada",
    "NEGOCIACION":        "En Negociación",
    "CERRADO_GANADO":     "Cierre Ganado",
    "CERRADO_PERDIDO":    "Cierre Perdido",
}


# ── Helpers de BD ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def _metricas_correo() -> dict:
    try:
        from src.database.connection import get_session
        from src.database.models import HistorialInteracciones

        with get_session() as session:
            total = (
                session.query(HistorialInteracciones)
                .filter(HistorialInteracciones.canal == "EMAIL",
                        HistorialInteracciones.tipo_interaccion == "EMAIL_SALIENTE")
                .count()
            )
            abiertos = (
                session.query(HistorialInteracciones)
                .filter(HistorialInteracciones.canal == "EMAIL",
                        HistorialInteracciones.estado_respuesta == "ABIERTO")
                .count()
            )
            respondidos = (
                session.query(HistorialInteracciones)
                .filter(HistorialInteracciones.canal == "EMAIL",
                        HistorialInteracciones.estado_respuesta == "RESPONDIDO")
                .count()
            )
            # Últimas 8 semanas
            corte = datetime.now() - timedelta(weeks=8)
            recientes = (
                session.query(
                    HistorialInteracciones.fecha_interaccion,
                    HistorialInteracciones.estado_respuesta,
                    HistorialInteracciones.asunto,
                )
                .filter(
                    HistorialInteracciones.canal == "EMAIL",
                    HistorialInteracciones.tipo_interaccion == "EMAIL_SALIENTE",
                    HistorialInteracciones.fecha_interaccion >= corte,
                )
                .all()
            )
            # Agrupar por semana
            semanas: dict[str, int] = {}
            asuntos_rendimiento: dict[str, dict] = {}
            for fecha, estado, asunto in recientes:
                sem = fecha.strftime("%Y-W%V")
                semanas[sem] = semanas.get(sem, 0) + 1
                if asunto:
                    if asunto not in asuntos_rendimiento:
                        asuntos_rendimiento[asunto] = {"enviados": 0, "respondidos": 0}
                    asuntos_rendimiento[asunto]["enviados"] += 1
                    if estado == "RESPONDIDO":
                        asuntos_rendimiento[asunto]["respondidos"] += 1

        return {
            "ok": True,
            "total": total,
            "abiertos": abiertos,
            "respondidos": respondidos,
            "semanas": semanas,
            "asuntos": asuntos_rendimiento,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@st.cache_data(ttl=30)
def _metricas_pipeline() -> dict:
    try:
        from sqlalchemy import func
        from src.database.connection import get_session
        from src.database.models import EmpresaProspecto

        with get_session() as session:
            raw = (
                session.query(
                    EmpresaProspecto.estado_prospecto,
                    func.count(EmpresaProspecto.id_empresa),
                )
                .filter(EmpresaProspecto.opt_out == False)
                .group_by(EmpresaProspecto.estado_prospecto)
                .all()
            )
        estados = {k: v for k, v in raw}
        return {"ok": True, "estados": estados}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "estados": {}}


@st.cache_data(ttl=30)
def _metricas_whatsapp() -> dict:
    try:
        from src.database.connection import get_session
        from src.database.models import HistorialInteracciones

        with get_session() as session:
            total = (
                session.query(HistorialInteracciones)
                .filter(HistorialInteracciones.canal == "WHATSAPP")
                .count()
            )
        return {"ok": True, "total": total}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "total": 0}


def _optimizar_con_ia(asuntos_data: dict) -> str:
    """Llama a Claude para analizar rendimiento de asuntos y sugerir mejoras."""
    import os
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return "⚠️ Configura `ANTHROPIC_API_KEY` en `.env` para activar la optimización con IA."

    if not asuntos_data:
        return "No hay suficientes datos de asuntos para analizar. Envía al menos 5 correos primero."

    # Construir tabla de rendimiento
    filas = []
    for asunto, stats in list(asuntos_data.items())[:15]:
        enviados = stats["enviados"]
        respondidos = stats["respondidos"]
        tasa = (respondidos / enviados * 100) if enviados > 0 else 0
        filas.append(f"- '{asunto[:80]}' → {enviados} envíos, {respondidos} resp. ({tasa:.0f}%)")
    tabla = "\n".join(filas)

    prompt = f"""Eres el experto en email marketing B2B de Medina SST Empresarial SAS, \
consultoría de Seguridad y Salud en el Trabajo en Colombia.

Analiza el rendimiento de estos asuntos de correo enviados a prospectos corporativos:

{tabla}

Proporciona:
1. **Diagnóstico** (2 oraciones): qué patrón de asuntos funciona mejor y por qué.
2. **Top 3 asuntos nuevos** para correos de primer contacto, optimizados para empresas colombianas \
con obligaciones bajo la Resolución 0312/2019. Incluye por qué funcionarán.
3. **Una cosa a evitar** en los asuntos actuales.

Responde en español, formato Markdown, máximo 200 palabras."""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key, timeout=20.0)
        msg = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        return f"Error al llamar a Claude: {exc}"


# ── Render principal ──────────────────────────────────────────────────────────

def render() -> None:
    import os

    col_t, col_r = st.columns([6, 1])
    col_t.title("📈 Analítica y Conversión")
    if col_r.button("🔄", help="Actualizar métricas", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption("Módulo 4 — Auditor de Conversión, Rendimiento de Correos y Optimización con IA")

    tab_pipeline, tab_correos, tab_ia, tab_respuestas, tab_roi = st.tabs([
        "🎯 Embudo de Conversión",
        "📧 Rendimiento de Correos",
        "⚡ Optimización IA",
        "📥 Detección de Respuestas",
        "💰 ROI del Software",
    ])

    with tab_pipeline:
        _render_pipeline()

    with tab_correos:
        _render_correos()

    with tab_ia:
        _render_optimizacion_ia()

    with tab_respuestas:
        _render_respuestas()

    with tab_roi:
        _render_roi()


def _render_pipeline() -> None:
    datos = _metricas_pipeline()
    correo = _metricas_correo()

    if not datos["ok"]:
        st.error(f"Error: {datos.get('error')}")
        return

    estados = datos["estados"]
    total = sum(estados.values())

    # KPIs
    nuevos    = estados.get("NUEVO", 0)
    cotizados = estados.get("COTIZACION_ENVIADA", 0)
    ganados   = estados.get("CERRADO_GANADO", 0)
    conv      = f"{ganados/total*100:.1f}%" if total else "0%"

    c1, c2, c3, c4 = st.columns(4)
    with c1: tarjeta_kpi("Total Prospectos", str(total),               icono="🏢", color="#1B3A6B")
    with c2: tarjeta_kpi("Correos Enviados", str(correo.get("total", 0)), icono="📧", color="#7C3AED")
    with c3: tarjeta_kpi("Nuevos",           str(nuevos),              icono="🆕", color="#10B981")
    with c4: tarjeta_kpi("Tasa de Cierre",   conv,                     icono="🏆", color="#E65C00")

    st.divider()
    separador_seccion("Conversión por etapa del embudo")

    # Tabla de conversión entre etapas
    filas = []
    prev_count = None
    for etapa in _ETAPAS_ORDEN:
        if etapa == "CERRADO_PERDIDO":
            continue
        count = estados.get(etapa, 0)
        conv_etapa = f"{count/total*100:.1f}%" if total else "0%"
        drop = ""
        if prev_count is not None and prev_count > 0:
            drop = f"↓ {(1 - count/prev_count)*100:.0f}% abandono"
        filas.append({
            "Etapa":       _ETAPA_LABEL.get(etapa, etapa),
            "Prospectos":  count,
            "% del Total": conv_etapa,
            "Abandono":    drop,
        })
        prev_count = count if count > 0 else prev_count

    df = pd.DataFrame(filas)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    separador_seccion("Embudo visual")

    etapas_vis = [e for e in _ETAPAS_ORDEN if e != "CERRADO_PERDIDO"]
    valores = [estados.get(e, 0) for e in etapas_vis]
    labels  = [_ETAPA_LABEL[e] for e in etapas_vis]

    fig = go.Figure(go.Funnel(
        y=labels, x=valores,
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(color=["#1B3A6B", "#2D5896", "#4A7CC2", "#E65C00", "#10B981"]),
        connector=dict(line=dict(color="#E5E7EB", width=1)),
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0), height=300,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="sans-serif", size=13),
    )
    st.plotly_chart(fig, use_container_width=True)

    # KPI: tasa de conversión del pipeline (PDF)
    if total > 0:
        tasa_cot = cotizados / total * 100
        st.metric(
            "KPI — Tasa de conversión a Cotización Enviada",
            f"{tasa_cot:.1f}%",
            help="Meta del PDF: maximizar % de prospectos fríos que llegan a cotización",
        )


def _render_correos() -> None:
    import os
    datos = _metricas_correo()

    if not datos["ok"]:
        st.error(f"Error al cargar métricas: {datos.get('error')}")
        return

    total      = datos["total"]
    abiertos   = datos["abiertos"]
    respondidos = datos["respondidos"]
    tracking_activo = bool(os.getenv("TRACKING_URL", "").strip())

    # KPIs
    c1, c2, c3 = st.columns(3)
    with c1:
        tarjeta_kpi("Correos Enviados", str(total), icono="📤", color="#1B3A6B")
    with c2:
        if tracking_activo:
            tasa_ap = f"{abiertos/total*100:.1f}%" if total else "0%"
            tarjeta_kpi("Tasa de Apertura", tasa_ap, icono="👁️", color="#7C3AED")
        else:
            tarjeta_kpi("Tasa de Apertura", "—", icono="👁️", color="#94A3B8")
    with c3:
        tasa_resp = f"{respondidos/total*100:.1f}%" if total else "0%"
        tarjeta_kpi("Tasa de Respuesta", tasa_resp, icono="↩️", color="#10B981")

    # Advertencia si tracking no configurado
    if not tracking_activo:
        st.info(
            "📡 **Tracking de aperturas inactivo.** Para activarlo, configura `TRACKING_URL` "
            "en `.env` apuntando a tu servidor de tracking. La tasa de respuesta sí está disponible."
        )

    st.divider()
    separador_seccion("Correos enviados por semana (últimas 8 semanas)")

    semanas = datos["semanas"]
    if semanas:
        df_sem = pd.DataFrame(
            sorted(semanas.items()),
            columns=["Semana", "Enviados"],
        )
        fig = go.Figure(go.Bar(
            x=df_sem["Semana"], y=df_sem["Enviados"],
            marker_color="#1B3A6B",
            text=df_sem["Enviados"], textposition="outside",
        ))
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0), height=250,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickfont=dict(size=11)),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sin correos enviados en las últimas 8 semanas.")

    st.divider()
    separador_seccion("Rendimiento por asunto de correo")

    asuntos = datos["asuntos"]
    if asuntos:
        filas = []
        for asunto, stats in asuntos.items():
            env = stats["enviados"]
            res = stats["respondidos"]
            filas.append({
                "Asunto":      asunto[:70],
                "Enviados":    env,
                "Respondidos": res,
                "Tasa resp.":  f"{res/env*100:.0f}%" if env else "0%",
            })
        df_asuntos = pd.DataFrame(sorted(filas, key=lambda x: x["Respondidos"], reverse=True))
        st.dataframe(df_asuntos, use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos de asuntos aún. Los correos enviados aparecerán aquí.")


def _render_optimizacion_ia() -> None:
    separador_seccion("Optimización de Copys con Inteligencia Artificial")
    st.markdown(
        "Claude analiza los asuntos de correo con mejor y peor rendimiento en tu CRM "
        "y sugiere variantes optimizadas para el mercado colombiano SST."
    )

    import os
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        st.warning(
            "⚠️ Configura `ANTHROPIC_API_KEY` en tu `.env` para activar esta funcionalidad."
        )
        return

    datos = _metricas_correo()
    asuntos = datos.get("asuntos", {})

    col_btn, col_info = st.columns([2, 3])
    with col_info:
        total_asuntos = len(asuntos)
        st.markdown(
            f"<small style='color:#6B7280;'>Datos disponibles: "
            f"**{total_asuntos}** asuntos únicos de correo</small>",
            unsafe_allow_html=True,
        )

    with col_btn:
        analizar = st.button(
            "⚡ Analizar y Optimizar con Claude",
            type="primary",
            use_container_width=True,
            disabled=total_asuntos == 0,
        )

    if analizar:
        with st.spinner("Claude analizando rendimiento de correos..."):
            resultado = _optimizar_con_ia(asuntos)
        st.divider()
        st.markdown(resultado)

    if total_asuntos == 0:
        st.info(
            "Aún no hay datos de rendimiento de correos. "
            "Envía al menos 5 correos para habilitar el análisis."
        )


def _render_respuestas() -> None:
    separador_seccion("Detección automática de respuestas en Gmail")
    st.markdown(
        "Escanea tu bandeja de entrada de Gmail y marca automáticamente como "
        "**RESPONDIDO** las interacciones de prospectos que contestaron tus correos."
    )

    st.info(
        "**Nota:** Esta función requiere que Gmail haya sido autenticado con el scope "
        "`gmail.readonly`. Si ya tenías el token guardado, elimina "
        "`credentials/gmail_token.json` y vuelve a autenticar para obtener el nuevo permiso."
    )

    col_btn, col_res = st.columns([2, 3])
    with col_btn:
        detectar = st.button(
            "📥 Detectar Respuestas Ahora",
            type="primary",
            use_container_width=True,
        )

    if detectar:
        with st.spinner("Escaneando bandeja de entrada..."):
            from src.modules.tracking.reply_detector import detectar_y_registrar_respuestas
            count, msg = detectar_y_registrar_respuestas()
        if count > 0:
            st.success(f"✅ {msg}")
            st.cache_data.clear()
        else:
            st.info(f"ℹ️ {msg}")

    st.divider()
    separador_seccion("Últimas respuestas registradas en el CRM")
    _mostrar_ultimas_respuestas()


def _render_roi() -> None:
    import os
    separador_seccion("Retorno de Inversión del Software (ROI)")
    st.markdown(
        "Calcula el retorno real del ecosistema comparando el costo de desarrollo "
        "contra los ingresos generados por contratos SST cerrados directamente por el CRM."
    )

    # Leer valores de .env como defaults
    default_valor_cto = float(os.getenv("VALOR_CONTRATO_PROMEDIO_COP", "5000000") or 5000000)
    default_costo_dev = float(os.getenv("COSTO_DESARROLLO_SOFTWARE_COP", "0") or 0)

    # Cargar contratos cerrados desde BD
    datos_pipe = _metricas_pipeline()
    estados = datos_pipe.get("estados", {})
    contratos_cerrados = estados.get("CERRADO_GANADO", 0)

    col_inputs, col_resultado = st.columns([2, 3])

    with col_inputs:
        separador_seccion("Parámetros")
        valor_contrato = st.number_input(
            "Valor promedio contrato SST (COP)",
            min_value=0,
            value=int(default_valor_cto),
            step=500_000,
            format="%d",
            help="Precio promedio de un contrato de servicios SST cerrado",
        )
        costo_desarrollo = st.number_input(
            "Costo total del software (COP)",
            min_value=0,
            value=int(default_costo_dev),
            step=100_000,
            format="%d",
            help="Inversión total en desarrollo del ecosistema",
        )
        n_contratos = st.number_input(
            "Contratos cerrados vía CRM",
            min_value=0,
            value=contratos_cerrados,
            step=1,
            help="Detectado automáticamente de BD (estado CERRADO_GANADO). Puedes ajustarlo.",
        )

        # Guardar en .env como defaults
        if st.button("💾 Guardar como valores por defecto", use_container_width=True):
            _guardar_roi_env(int(valor_contrato), int(costo_desarrollo))

    with col_resultado:
        separador_seccion("Resultado")

        ingresos = n_contratos * valor_contrato
        beneficio_neto = ingresos - costo_desarrollo
        roi_pct = (beneficio_neto / costo_desarrollo * 100) if costo_desarrollo > 0 else None

        def _fmt(v: float) -> str:
            return f"$ {v:,.0f}".replace(",", ".")

        # Tarjetas de resultado
        r1, r2 = st.columns(2)
        with r1:
            tarjeta_kpi("Ingresos generados", _fmt(ingresos), icono="💵", color="#10B981")
        with r2:
            if roi_pct is not None:
                color = "#10B981" if roi_pct >= 0 else "#EF4444"
                tarjeta_kpi("ROI del Software", f"{roi_pct:+.0f}%", icono="📈", color=color)
            else:
                tarjeta_kpi("ROI del Software", "∞", icono="📈", color="#10B981")

        r3, r4 = st.columns(2)
        with r3:
            color_ben = "#10B981" if beneficio_neto >= 0 else "#EF4444"
            tarjeta_kpi("Beneficio neto", _fmt(beneficio_neto), icono="🏆", color=color_ben)
        with r4:
            tarjeta_kpi("Contratos cerrados", str(n_contratos), icono="🤝", color="#1B3A6B")

        st.divider()

        # Gráfico: punto de equilibrio
        if costo_desarrollo > 0 and valor_contrato > 0:
            separador_seccion("Curva de break-even")
            contratos_rango = list(range(0, max(n_contratos * 2 + 2, 12)))
            ingresos_rango  = [c * valor_contrato for c in contratos_rango]
            costo_rango     = [costo_desarrollo] * len(contratos_rango)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=contratos_rango, y=ingresos_rango,
                name="Ingresos acumulados",
                line=dict(color="#10B981", width=2),
                fill="tozeroy", fillcolor="rgba(16,185,129,0.08)",
            ))
            fig.add_trace(go.Scatter(
                x=contratos_rango, y=costo_rango,
                name="Costo del software",
                line=dict(color="#EF4444", width=2, dash="dash"),
            ))
            # Marcar posición actual
            fig.add_vline(
                x=n_contratos, line_color="#E65C00", line_dash="dot",
                annotation_text=f"Hoy ({n_contratos})", annotation_position="top right",
            )

            breakeven = costo_desarrollo / valor_contrato if valor_contrato else 0
            fig.add_vline(
                x=breakeven, line_color="#1B3A6B", line_dash="dash",
                annotation_text=f"Break-even ({breakeven:.1f})", annotation_position="top left",
            )

            fig.update_layout(
                margin=dict(l=0, r=0, t=20, b=0), height=260,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="Contratos cerrados",
                yaxis_title="COP",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                font=dict(size=12),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "Ingresa el **Costo total del software** y el **Valor promedio de contrato** "
                "para ver la curva de break-even."
            )


def _guardar_roi_env(valor_contrato: int, costo_desarrollo: int) -> None:
    """Persiste los valores de ROI en el archivo .env."""
    try:
        from pathlib import Path as _P
        env_path = _P(__file__).parent.parent.parent.parent / ".env"
        if not env_path.exists():
            st.warning("No se encontró el archivo .env")
            return
        lines = env_path.read_text(encoding="utf-8").splitlines()
        nuevas = []
        keys_actualizadas = set()
        for line in lines:
            if line.startswith("VALOR_CONTRATO_PROMEDIO_COP="):
                nuevas.append(f"VALOR_CONTRATO_PROMEDIO_COP={valor_contrato}")
                keys_actualizadas.add("VALOR_CONTRATO_PROMEDIO_COP")
            elif line.startswith("COSTO_DESARROLLO_SOFTWARE_COP="):
                nuevas.append(f"COSTO_DESARROLLO_SOFTWARE_COP={costo_desarrollo}")
                keys_actualizadas.add("COSTO_DESARROLLO_SOFTWARE_COP")
            else:
                nuevas.append(line)
        if "VALOR_CONTRATO_PROMEDIO_COP" not in keys_actualizadas:
            nuevas.append(f"VALOR_CONTRATO_PROMEDIO_COP={valor_contrato}")
        if "COSTO_DESARROLLO_SOFTWARE_COP" not in keys_actualizadas:
            nuevas.append(f"COSTO_DESARROLLO_SOFTWARE_COP={costo_desarrollo}")
        env_path.write_text("\n".join(nuevas), encoding="utf-8")
        st.success("✅ Valores guardados en .env")
    except Exception as exc:
        st.error(f"No se pudo guardar: {exc}")


@st.cache_data(ttl=30)
def _mostrar_ultimas_respuestas() -> None:
    try:
        from src.database.connection import get_session
        from src.database.models import EmpresaProspecto, HistorialInteracciones

        with get_session() as session:
            rows = (
                session.query(
                    HistorialInteracciones,
                    EmpresaProspecto.razon_social,
                )
                .join(EmpresaProspecto,
                      HistorialInteracciones.id_empresa == EmpresaProspecto.id_empresa)
                .filter(HistorialInteracciones.estado_respuesta == "RESPONDIDO")
                .order_by(HistorialInteracciones.fecha_interaccion.desc())
                .limit(20)
                .all()
            )

        if not rows:
            st.info("Sin respuestas registradas aún.")
            return

        filas = [
            {
                "Empresa":    rs,
                "Asunto":     (h.asunto or "")[:60],
                "Fecha":      h.fecha_interaccion.strftime("%d/%m/%Y %H:%M"),
                "Canal":      h.canal or "—",
            }
            for h, rs in rows
        ]
        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    except Exception as exc:
        st.error(f"Error al cargar respuestas: {exc}")
