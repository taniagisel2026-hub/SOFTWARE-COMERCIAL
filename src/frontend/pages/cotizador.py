import sys
from pathlib import Path

import streamlit as st

from ..components.metrics import separador_seccion

_ROOT = Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_CIUDADES = [
    "Bogotá D.C.", "Medellín", "Cali", "Barranquilla", "Bucaramanga",
    "Pereira", "Manizales", "Ibagué", "Cúcuta", "Santa Marta",
    "Cartagena", "Villavicencio", "Pasto", "Armenia", "Neiva",
    "Montería", "Sincelejo", "Valledupar", "Popayán", "Tunja",
]

_SECTORES = [
    "Construcción", "Manufactura / Industria", "Transporte y Logística",
    "Comercio y Retail", "Servicios Empresariales", "Salud y Clínicas",
    "Educación", "Agricultura y Ganadería", "Minería y Energía",
    "Tecnología y Software", "Alimentos y Bebidas", "Seguridad Privada",
    "Ingeniería y Consultoría", "Petróleo y Gas", "Otro",
]

_RIESGOS = [
    "I — Bajo (oficinas, comercio)",
    "II — Bajo-Medio",
    "III — Medio (industria ligera)",
    "IV — Alto (manufactura pesada)",
    "V — Muy Alto (minería, petróleo)",
]

# Clave única en session_state para el cálculo activo
_KEY = "calculo_actual"


def render() -> None:
    st.title("🧮 Cotizador Inteligente")
    st.caption("Calcula el nivel de estándares y el costo del SG-SST según la Resolución 0312/2019")

    col_form, col_result = st.columns([1, 1], gap="large")

    # ── Formulario ────────────────────────────────────────────────────────────
    with col_form:
        separador_seccion("Datos de la empresa")
        with st.form("form_cotizador", clear_on_submit=False):
            razon_social    = st.text_input("Razón Social *",
                                            placeholder="Ej: Constructora El Progreso SAS")
            nit             = st.text_input("NIT (opcional)",
                                            placeholder="Ej: 900123456-1")
            ciudad          = st.selectbox("Ciudad *", _CIUDADES)
            sector          = st.selectbox("Sector Económico *", _SECTORES)

            col_emp, col_riesgo = st.columns(2)
            with col_emp:
                num_empleados = st.number_input("N.° Trabajadores *",
                                                min_value=1, max_value=9999,
                                                value=15, step=1)
            with col_riesgo:
                nivel_label   = st.selectbox("Riesgo ARL *", _RIESGOS)

            email_contacto  = st.text_input("Email de contacto",
                                            placeholder="gerencia@empresa.com")
            nombre_contacto = st.text_input("Nombre del contacto",
                                            placeholder="Gerente o responsable HSEQ")

            calcular = st.form_submit_button("⚡ Calcular Cotización",
                                             type="primary",
                                             use_container_width=True)

        # Botón fuera del form para limpiar resultado sin re-enviar
        if _KEY in st.session_state:
            if st.button("🔄 Nueva cotización", use_container_width=True):
                del st.session_state[_KEY]
                st.rerun()

    # ── Procesar submit: calcular + generar PDF + guardar en session_state ────
    # Todo ocurre en el mismo rerun del form submit, antes de renderizar resultado.
    if calcular:
        if not razon_social.strip():
            st.session_state.pop(_KEY, None)
            with col_result:
                st.error("La Razón Social es obligatoria.")
        else:
            nivel_riesgo_str = nivel_label.split(" ")[0]
            with col_result:
                with st.spinner("Calculando y generando PDF..."):
                    try:
                        cotizacion = _calcular_backend(
                            razon_social.strip(), nit, ciudad, sector,
                            int(num_empleados), nivel_riesgo_str,
                            email_contacto, nombre_contacto,
                        )
                        # Generar PDF inmediatamente y guardar bytes en memory
                        pdf_bytes, pdf_nombre = _generar_pdf_bytes(
                            cotizacion, razon_social.strip(), ciudad
                        )
                        # Persistir todo en session_state
                        st.session_state[_KEY] = {
                            "cotizacion":     cotizacion,
                            "razon_social":   razon_social.strip(),
                            "ciudad":         ciudad,
                            "pdf_bytes":      pdf_bytes,
                            "pdf_nombre":     pdf_nombre,
                        }
                    except Exception as exc:
                        st.session_state.pop(_KEY, None)
                        st.error(f"Error al calcular: {exc}")

    # ── Columna de resultado: siempre desde session_state ────────────────────
    with col_result:
        if _KEY in st.session_state:
            _mostrar_resultado(st.session_state[_KEY])
        else:
            if not calcular:          # evita doble mensaje si hubo error arriba
                separador_seccion("Resultado de la cotización")
                st.info("👈 Completa el formulario y presiona **Calcular** para ver el resultado.")
                _mostrar_tabla_referencia()


# ── Backend: cálculo puro ────────────────────────────────────────────────────

def _calcular_backend(razon_social, nit, ciudad, sector,
                      num_empleados, nivel_riesgo_str,
                      email_contacto, nombre_contacto):
    from src.domain.entities import EmpresaProspecto, NivelRiesgo
    from src.modules.cotizador import CotizadorService

    empresa = EmpresaProspecto(
        razon_social=razon_social,
        nit=nit or "000000000-0",
        ciudad=ciudad,
        departamento="",
        num_empleados=num_empleados,
        nivel_riesgo_arl=NivelRiesgo(nivel_riesgo_str),
        sector_economico=sector,
        email_contacto=email_contacto,
        nombre_contacto=nombre_contacto,
    )
    return CotizadorService().generar_cotizacion(empresa, creado_por="Asesor")


def _generar_pdf_bytes(cotizacion, razon_social: str, ciudad: str) -> tuple[bytes, str]:
    """Genera el PDF y retorna (bytes, nombre_archivo). Sin side-effects de UI."""
    from src.domain.entities import EmpresaProspecto
    from src.modules.cotizador import exportar_pdf

    empresa_temp = EmpresaProspecto(
        razon_social=razon_social,
        nit="N/A",
        ciudad=ciudad,
        departamento="",
        num_empleados=cotizacion.num_empleados_cotizados,
        nivel_riesgo_arl=cotizacion.nivel_riesgo,
    )
    pdf_path = exportar_pdf(cotizacion, empresa_temp)
    nombre   = f"{cotizacion.codigo_cotizacion}.pdf"
    return pdf_path.read_bytes(), nombre


# ── Renderizado del resultado ────────────────────────────────────────────────

def _mostrar_resultado(state: dict) -> None:
    """
    Lee exclusivamente de session_state.
    Sobrevive cualquier rerun posterior, incluyendo el click de st.download_button.
    """
    from src.domain.resolution_0312 import ESPECIFICACIONES

    cotizacion  = state["cotizacion"]
    ciudad      = state["ciudad"]
    pdf_bytes   = state["pdf_bytes"]
    pdf_nombre  = state["pdf_nombre"]
    spec        = ESPECIFICACIONES[cotizacion.nivel_estandares]

    separador_seccion("Resultado de la cotización")

    # Bloque principal de estándares
    st.markdown(f"""
    <div class="resultado-box">
        <div class="res-num">{spec.num_estandares}</div>
        <div class="res-label"><strong>estándares mínimos</strong> aplicables</div>
        <div style="margin-top:6px;font-size:13px;color:#374151;">
            {spec.articulo_resolucion} · Resolución 0312/2019
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"**{spec.descripcion_legal}**")
    st.divider()

    # Métricas de costo
    c1, c2 = st.columns(2)
    c1.metric(
        "Valor total del proyecto",
        f"$ {float(cotizacion.valor_total_proyecto):,.0f}".replace(",", ".") + " COP",
    )
    c2.metric(
        "Cuota mensual equivalente",
        f"$ {float(cotizacion.valor_total_mensual):,.0f}".replace(",", ".") + " COP",
    )

    if float(cotizacion.valor_viaticos) > 0:
        st.info(
            f"📍 Viáticos estimados ({ciudad}): "
            f"**$ {float(cotizacion.valor_viaticos):,.0f} COP**".replace(",", ".")
        )

    # Desglose de servicios
    with st.expander("📋 Ver desglose de servicios incluidos"):
        for i, svc in enumerate(cotizacion.servicios_incluidos, 1):
            cols = st.columns([4, 1, 2])
            cols[0].markdown(f"{i}. {svc.descripcion}")
            cols[1].markdown(f"`{svc.cantidad_horas}h`")
            cols[2].markdown(f"$ {float(svc.valor_total):,.0f}".replace(",", "."))

    st.divider()

    # ── Botones de acción ────────────────────────────────────────────────────
    col_pdf, col_crm = st.columns(2)

    with col_pdf:
        # st.download_button recibe los bytes directamente desde session_state.
        # No genera un rerun que limpie el estado; la descarga ocurre en el navegador
        # y el resultado permanece visible en pantalla.
        st.download_button(
            label="📄 Descargar PDF",
            data=pdf_bytes,
            file_name=pdf_nombre,
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            help=f"Descarga {pdf_nombre} generado por ReportLab",
        )

    with col_crm:
        if st.button("💾 Guardar en CRM", use_container_width=True,
                     help="Registra la empresa y cotización en la base de datos"):
            _guardar_en_crm(cotizacion, state["razon_social"], ciudad)


def _guardar_en_crm(cotizacion, razon_social: str, ciudad: str) -> None:
    """Persiste la empresa y cotización en la BD."""
    try:
        from datetime import date
        from src.database.connection import get_session
        from src.database.models import (
            Cotizacion as CotizacionORM,
            EmpresaProspecto as EmpresaORM,
        )
        from src.modules.scraper.crm_injector import CRMInjectorService
        from src.modules.scraper.base import ProspectoExtraido

        prospecto = ProspectoExtraido(
            razon_social=razon_social,
            ciudad=ciudad,
            departamento="",
            fuente="Cotizador Web",
            sector_economico=cotizacion.servicios_incluidos[0].nombre if cotizacion.servicios_incluidos else "",
            num_empleados=cotizacion.num_empleados_cotizados,
            nivel_riesgo_arl=cotizacion.nivel_riesgo.value,
        )
        id_empresa, fue_nuevo = CRMInjectorService().inyectar(prospecto)

        with get_session() as session:
            session.add(CotizacionORM(
                id_empresa=id_empresa,
                codigo_cotizacion=cotizacion.codigo_cotizacion,
                version=cotizacion.version,
                num_empleados_cotizados=cotizacion.num_empleados_cotizados,
                nivel_riesgo=cotizacion.nivel_riesgo.value,
                nivel_estandares=cotizacion.nivel_estandares.value,
                servicios_incluidos=[s.to_dict() for s in cotizacion.servicios_incluidos],
                valor_servicios=float(cotizacion.valor_servicios),
                valor_viaticos=float(cotizacion.valor_viaticos),
                valor_total_proyecto=float(cotizacion.valor_total_proyecto),
                valor_total_mensual=float(cotizacion.valor_total_mensual),
                valor_total_anual=float(cotizacion.valor_total_anual),
                estado_cotizacion=cotizacion.estado_cotizacion.value,
                fecha_emision=cotizacion.fecha_emision,
                fecha_vencimiento=cotizacion.fecha_vencimiento,
                creado_por="Asesor Web",
            ))

        etiqueta = "nueva empresa" if fue_nuevo else "empresa existente"
        st.success(f"✅ Guardado en CRM ({etiqueta}) · Cotización `{cotizacion.codigo_cotizacion}`")
        st.cache_data.clear()

    except Exception as exc:
        st.error(f"Error al guardar en CRM: {exc}")


def _mostrar_tabla_referencia() -> None:
    import pandas as pd
    separador_seccion("Referencia rápida Res. 0312/2019")
    df = pd.DataFrame([
        {"Trabajadores": "1 – 10",  "Riesgo ARL": "I / II / III", "Estándares": "7",  "Artículo": "Art. 3"},
        {"Trabajadores": "11 – 50", "Riesgo ARL": "I / II / III", "Estándares": "21", "Artículo": "Art. 16"},
        {"Trabajadores": "> 50",    "Riesgo ARL": "Cualquiera",   "Estándares": "60", "Artículo": "Art. 27"},
        {"Trabajadores": "1 – 50",  "Riesgo ARL": "IV / V",       "Estándares": "60", "Artículo": "Art. 27"},
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
