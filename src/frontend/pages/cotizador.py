import sys
from pathlib import Path

import streamlit as st

from ..components.metrics import separador_seccion

# Ciudades principales de Colombia para el selector
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

_RIESGOS = ["I — Bajo (oficinas, comercio)", "II — Bajo-Medio", "III — Medio (industria ligera)",
            "IV — Alto (manufactura pesada)", "V — Muy Alto (minería, petróleo)"]

_RIESGO_VALOR = {"I": "I", "II": "II", "III": "III", "IV": "IV", "V": "V"}


def render() -> None:
    st.title("🧮 Cotizador Inteligente")
    st.caption("Calcula automáticamente el nivel de estándares y el costo del SG-SST según la Resolución 0312/2019")

    col_form, col_result = st.columns([1, 1], gap="large")

    # ── Formulario ────────────────────────────────────────────────────────────
    with col_form:
        separador_seccion("Datos de la empresa")
        with st.form("form_cotizador", clear_on_submit=False):
            razon_social = st.text_input(
                "Razón Social *",
                placeholder="Ej: Constructora El Progreso SAS",
            )
            nit = st.text_input(
                "NIT (opcional)",
                placeholder="Ej: 900123456-1",
            )
            ciudad = st.selectbox("Ciudad *", options=_CIUDADES)
            sector = st.selectbox("Sector Económico *", options=_SECTORES)

            col_emp, col_riesgo = st.columns(2)
            with col_emp:
                num_empleados = st.number_input(
                    "N.° Trabajadores *",
                    min_value=1, max_value=9999, value=15, step=1,
                )
            with col_riesgo:
                nivel_label = st.selectbox("Riesgo ARL *", options=_RIESGOS)

            email_contacto = st.text_input("Email de contacto", placeholder="gerencia@empresa.com")
            nombre_contacto = st.text_input("Nombre del contacto", placeholder="Nombre del gerente o HSEQ")

            calcular = st.form_submit_button("⚡ Calcular Cotización", type="primary", use_container_width=True)

    # ── Resultado ─────────────────────────────────────────────────────────────
    with col_result:
        separador_seccion("Resultado de la cotización")

        if not calcular:
            st.info("👈 Completa el formulario y presiona **Calcular** para ver el resultado.")
            _mostrar_tabla_referencia()
            return

        if not razon_social:
            st.error("La Razón Social es obligatoria.")
            return

        nivel_riesgo_str = nivel_label.split(" ")[0]  # Extrae "I", "II", etc.

        try:
            resultado = _calcular_backend(
                razon_social, nit, ciudad, sector,
                int(num_empleados), nivel_riesgo_str,
                email_contacto, nombre_contacto,
            )
            _mostrar_resultado(resultado, razon_social, ciudad)
        except Exception as exc:
            st.error(f"Error al calcular: {exc}")


def _calcular_backend(
    razon_social, nit, ciudad, sector, num_empleados, nivel_riesgo_str,
    email_contacto, nombre_contacto,
):
    """Conecta con CotizadorService del backend. Lógica pura sin DB."""
    # Añadir src/ al path si es necesario
    root = Path(__file__).parent.parent.parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

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
    cotizacion = CotizadorService().generar_cotizacion(empresa, creado_por="Asesor")
    return cotizacion


def _mostrar_resultado(cotizacion, razon_social: str, ciudad: str) -> None:
    from src.domain.resolution_0312 import ESPECIFICACIONES

    spec = ESPECIFICACIONES[cotizacion.nivel_estandares]

    # Bloque de resultado principal
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

    # Desglose de costos
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("Valor total del proyecto", f"$ {float(cotizacion.valor_total_proyecto):,.0f}".replace(",", ".") + " COP")
    c2.metric("Cuota mensual equivalente", f"$ {float(cotizacion.valor_total_mensual):,.0f}".replace(",", ".") + " COP")

    if float(cotizacion.valor_viaticos) > 0:
        st.info(f"📍 Viáticos estimados por desplazamiento a {ciudad}: "
                f"**$ {float(cotizacion.valor_viaticos):,.0f} COP**".replace(",", "."))

    # Servicios incluidos
    with st.expander("📋 Ver desglose de servicios incluidos"):
        for i, svc in enumerate(cotizacion.servicios_incluidos, 1):
            cols = st.columns([4, 1, 2])
            cols[0].markdown(f"{i}. {svc.descripcion}")
            cols[1].markdown(f"`{svc.cantidad_horas}h`")
            cols[2].markdown(f"$ {float(svc.valor_total):,.0f}".replace(",", "."))

    st.divider()

    # Botón Generar PDF
    col_pdf, col_guardar = st.columns(2)
    with col_pdf:
        if st.button("📄 Generar PDF", type="primary", use_container_width=True):
            _generar_y_descargar_pdf(cotizacion, razon_social, ciudad)
    with col_guardar:
        st.button("💾 Guardar en CRM", use_container_width=True,
                  help="TODO: guardará la empresa y cotización en EMPRESA_PROSPECTO y COTIZACION")


def _generar_y_descargar_pdf(cotizacion, razon_social: str, ciudad: str) -> None:
    from src.domain.entities import EmpresaProspecto, NivelRiesgo
    from src.modules.cotizador import exportar_pdf

    empresa_temp = EmpresaProspecto(
        razon_social=razon_social, nit="N/A",
        ciudad=ciudad, departamento="",
        num_empleados=cotizacion.num_empleados_cotizados,
        nivel_riesgo_arl=cotizacion.nivel_riesgo,
    )
    with st.spinner("Generando PDF..."):
        pdf_path = exportar_pdf(cotizacion, empresa_temp)

    with open(pdf_path, "rb") as f:
        st.download_button(
            label="⬇️ Descargar PDF",
            data=f.read(),
            file_name=f"{cotizacion.codigo_cotizacion}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    st.success(f"PDF generado: `{cotizacion.codigo_cotizacion}.pdf`")


def _mostrar_tabla_referencia() -> None:
    """Tabla de referencia rápida de la Res. 0312 mientras no hay resultado."""
    import pandas as pd
    separador_seccion("Referencia rápida Res. 0312/2019")
    df = pd.DataFrame([
        {"Trabajadores": "1 – 10",  "Riesgo ARL": "I / II / III", "Estándares": "7",  "Artículo": "Art. 3"},
        {"Trabajadores": "11 – 50", "Riesgo ARL": "I / II / III", "Estándares": "21", "Artículo": "Art. 16"},
        {"Trabajadores": "> 50",    "Riesgo ARL": "Cualquiera",   "Estándares": "60", "Artículo": "Art. 27"},
        {"Trabajadores": "1 – 50",  "Riesgo ARL": "IV / V",       "Estándares": "60", "Artículo": "Art. 27"},
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
