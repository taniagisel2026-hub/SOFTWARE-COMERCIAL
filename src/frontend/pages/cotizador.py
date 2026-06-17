"""Cotizador manual — precios definidos por el asesor, PDF con logo Medina SST."""
import uuid
from datetime import date
from pathlib import Path

import streamlit as st

from ..components.metrics import separador_seccion

_CIUDADES = [
    "Bogotá D.C.", "Medellín", "Cali", "Barranquilla", "Bucaramanga",
    "Pereira", "Manizales", "Ibagué", "Cúcuta", "Santa Marta",
    "Cartagena", "Villavicencio", "Pasto", "Armenia", "Neiva",
    "Montería", "Sincelejo", "Valledupar", "Popayán", "Tunja",
]

_SERVICIOS_COMPECER = [
    "ISO 9001:2015 — Gestión de la Calidad",
    "ISO 45001:2018 — Seguridad y Salud en el Trabajo",
    "ISO 14001:2015 — Gestión Ambiental",
    "ISO 27001:2022 — Seguridad de la Información",
    "ISO 37001:2016 — Gestión Antisoborno",
    "ISO 21001:2018 — Organizaciones Educativas",
    "ISO 20000-1:2018 — Gestión de Servicios TI",
    "ISO 50001:2018 — Gestión de la Energía",
    "ISO 22000:2018 — Gestión de Inocuidad Alimentaria",
    "ISO 56002:2019 — Gestión de la Innovación",
]

_SERVICIOS = [
    "Implementación y administración SG-SST",
    "Mediciones Ambientales (Luxometría, Sonometría, Dosimetría, Estrés Térmico, Gases y Vapores, Material Particulado)",
    "Batería de Riesgo Psicosocial",
    "Rumba Terapia",
    "Capacitación y Talleres en Seguridad y Salud en el Trabajo",
    "Planos de Emergencia",
    "Capacitación y Certificación de Brigadas de Emergencia",
    "Acompañamiento en Certificación de Estándares Mínimos (ARL y Ministerio del Trabajo)",
    "Profesiograma",
    "Análisis de Puesto de Trabajo",
    "Red Contra Incendios",
    "Inspecciones de Puesto de Trabajo",
    "Investigación de Accidentes de Trabajo",
    "Acompañamiento en Seguridad y Salud en el Trabajo",
]

_KEY = "cotizacion_manual"


def _nuevo_codigo() -> str:
    return f"COT-{date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"


def render() -> None:
    st.markdown("## 🧮 Cotizador")
    st.caption("Selecciona los servicios, ingresa los precios y descarga el PDF de propuesta.")

    col_form, col_result = st.columns([1, 1], gap="large")

    with col_form:
        separador_seccion("Datos del cliente")

        razon_social    = st.text_input("Razón Social *", placeholder="Constructora El Progreso SAS")
        nit             = st.text_input("NIT", placeholder="900123456-1")
        nombre_contacto = st.text_input("Nombre del contacto", placeholder="Gerente o responsable HSEQ")
        cargo_contacto  = st.text_input("Cargo", placeholder="Gerente General")
        ciudad          = st.selectbox("Ciudad", _CIUDADES)
        telefono        = st.text_input("Teléfono", placeholder="601 234 5678")
        email_contacto  = st.text_input("Email", placeholder="gerencia@empresa.com")
        elaborado_por   = st.text_input("Elaborado por", placeholder="Nombre del asesor")

        separador_seccion("Servicios a cotizar")
        st.caption("Selecciona los servicios e ingresa el precio de cada uno.")

        seleccionados: list[dict] = []
        for nombre in _SERVICIOS:
            key_check = f"chk_{nombre[:20]}"
            key_price = f"prc_{nombre[:20]}"
            checked = st.checkbox(nombre, key=key_check)
            if checked:
                precio = st.number_input(
                    f"Precio — {nombre[:45]}...",
                    min_value=0,
                    step=50000,
                    format="%d",
                    key=key_price,
                )
                seleccionados.append({"nombre": nombre, "precio": float(precio)})

        separador_seccion("Servicios Compecer (Alianza)")
        st.caption("Certificaciones ISO gestionadas por Compecer. Se incluyen en el PDF como sección separada.")
        seleccionados_compecer: list[dict] = []
        for nombre in _SERVICIOS_COMPECER:
            key_check = f"chk_comp_{nombre[:20]}"
            key_price = f"prc_comp_{nombre[:20]}"
            checked = st.checkbox(nombre, key=key_check)
            if checked:
                precio = st.number_input(
                    f"Precio — {nombre[:45]}...",
                    min_value=0, step=50000, format="%d", key=key_price,
                )
                seleccionados_compecer.append({"nombre": nombre, "precio": float(precio)})

        separador_seccion("Ajustes")
        descuento = st.number_input("Descuento (opcional)", min_value=0, step=50000,
                                    format="%d", help="Valor a restar del total")
        condiciones_pago = st.text_input(
            "Condiciones de pago",
            value="50% al inicio · 50% contra entrega",
        )

        generar = st.button("📄 Generar cotización", type="primary", use_container_width=True)

        if _KEY in st.session_state:
            if st.button("🔄 Nueva cotización", use_container_width=True):
                del st.session_state[_KEY]
                st.rerun()

    # ── Procesar ───────────────────────────────────────────────────────────────
    if generar:
        if not razon_social.strip():
            st.error("La Razón Social es obligatoria.")
        elif not seleccionados and not seleccionados_compecer:
            st.error("Selecciona al menos un servicio.")
        else:
            with col_result:
                with st.spinner("Generando PDF..."):
                    try:
                        codigo = _nuevo_codigo()
                        pdf_bytes, pdf_nombre = _generar_pdf(
                            codigo=codigo,
                            razon_social=razon_social.strip(),
                            nit=nit,
                            nombre_contacto=nombre_contacto,
                            cargo_contacto=cargo_contacto,
                            ciudad=ciudad,
                            telefono=telefono,
                            email_contacto=email_contacto,
                            servicios=seleccionados,
                            servicios_compecer=seleccionados_compecer,
                            descuento=float(descuento),
                            elaborado_por=elaborado_por or "Asesor",
                            condiciones_pago=condiciones_pago,
                        )
                        st.session_state[_KEY] = {
                            "razon_social":       razon_social.strip(),
                            "servicios":          seleccionados,
                            "servicios_compecer": seleccionados_compecer,
                            "descuento":          float(descuento),
                            "pdf_bytes":          pdf_bytes,
                            "pdf_nombre":         pdf_nombre,
                            "codigo":             codigo,
                        }
                    except Exception as exc:
                        st.session_state.pop(_KEY, None)
                        st.error(f"Error al generar PDF: {exc}")

    # ── Resultado ──────────────────────────────────────────────────────────────
    with col_result:
        if _KEY in st.session_state:
            _mostrar_resultado(st.session_state[_KEY])
        else:
            separador_seccion("Resumen de la cotización")
            st.info("👈 Completa el formulario y presiona **Generar cotización**.")


def _generar_pdf(
    codigo, razon_social, nit, nombre_contacto, cargo_contacto,
    ciudad, telefono, email_contacto, servicios, servicios_compecer,
    descuento, elaborado_por, condiciones_pago,
) -> tuple[bytes, str]:
    from src.modules.cotizador.pdf_manual import generar_pdf_manual

    pdf_path = generar_pdf_manual(
        codigo=codigo,
        razon_social=razon_social,
        nit=nit,
        nombre_contacto=nombre_contacto,
        cargo_contacto=cargo_contacto,
        ciudad=ciudad,
        telefono=telefono,
        email_contacto=email_contacto,
        servicios=servicios,
        servicios_compecer=servicios_compecer,
        descuento=descuento,
        elaborado_por=elaborado_por,
        condiciones_pago=condiciones_pago,
    )
    return pdf_path.read_bytes(), f"{codigo}.pdf"


def _mostrar_resultado(state: dict) -> None:
    separador_seccion("Resumen de la cotización")

    st.markdown(f"**Cliente:** {state['razon_social']}")
    st.markdown(f"**Código:** `{state['codigo']}`")

    st.divider()

    subtotal  = sum(s["precio"] for s in state["servicios"])
    descuento = state["descuento"]
    total     = subtotal - descuento

    for svc in state["servicios"]:
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"• {svc['nombre']}")
        c2.markdown(f"**$ {svc['precio']:,.0f}**".replace(",", "."))

    st.divider()

    if descuento > 0:
        c1, c2 = st.columns([3, 1])
        c1.markdown("Descuento")
        c2.markdown(f"- $ {descuento:,.0f}".replace(",", "."))

    c1, c2 = st.columns([3, 1])
    c1.markdown("### Total")
    c2.markdown(f"### $ {total:,.0f}".replace(",", "."))

    st.divider()

    st.download_button(
        label="📥 Descargar PDF",
        data=state["pdf_bytes"],
        file_name=state["pdf_nombre"],
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )
