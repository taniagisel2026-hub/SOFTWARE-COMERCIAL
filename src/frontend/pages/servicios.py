import streamlit as st

from ..components.metrics import separador_seccion

_SERVICIOS_MEDINA = [
    ("🏗️", "Implementación y administración SG-SST",
     "Diseño, implementación y administración del Sistema de Gestión de Seguridad y Salud en el Trabajo conforme a la Resolución 0312/2019."),
    ("🔬", "Mediciones Ambientales",
     "Luxometría, Sonometría, Dosimetría, Estrés Térmico, Gases y Vapores, y Material Particulado para control de condiciones laborales."),
    ("🧠", "Batería de Riesgo Psicosocial",
     "Aplicación e interpretación de la batería oficial del Ministerio del Trabajo para identificar factores de riesgo psicosocial."),
    ("💃", "Rumba Terapia",
     "Programa de bienestar laboral a través de actividad física guiada para reducir el estrés y mejorar el clima organizacional."),
    ("📚", "Capacitación y Talleres SST",
     "Formación al personal en prevención de riesgos, uso de EPP, manejo seguro de materiales y cultura de autocuidado."),
    ("🗺️", "Planos de Emergencia",
     "Elaboración de planos de evacuación, rutas de escape y señalización conforme a la normativa vigente."),
    ("🚒", "Brigadas de Emergencia",
     "Capacitación y certificación de brigadas en primeros auxilios, contra incendios, evacuación y rescate."),
    ("✅", "Certificación de Estándares Mínimos",
     "Acompañamiento para la autoevaluación y cumplimiento de estándares ante ARL y Ministerio del Trabajo."),
    ("📋", "Profesiograma",
     "Diseño del profesiograma ocupacional con definición de exámenes médicos por cargo y nivel de riesgo."),
    ("🪑", "Análisis de Puesto de Trabajo",
     "Evaluación ergonómica y de condiciones de trabajo para prevenir lesiones músculo-esqueléticas y enfermedades laborales."),
    ("🔥", "Red Contra Incendios",
     "Diseño, instalación y mantenimiento de sistemas de detección y extinción de incendios en instalaciones industriales y comerciales."),
    ("🔍", "Inspecciones de Puesto de Trabajo",
     "Visitas técnicas periódicas para identificar condiciones inseguras y proponer medidas correctivas inmediatas."),
    ("📝", "Investigación de Accidentes de Trabajo",
     "Metodología formal de investigación (árbol de causas, 5 por qué) con informe a ARL y acciones preventivas."),
    ("🤝", "Acompañamiento en SST",
     "Asesoría continua y soporte en terreno para el equipo responsable del SG-SST dentro de la empresa."),
]

_NORMAS_ISO = [
    ("ISO 9001:2015", "Gestión de la Calidad"),
    ("ISO 45001:2018", "Seguridad y Salud en el Trabajo"),
    ("ISO 14001:2015", "Gestión Ambiental"),
    ("ISO 27001:2022", "Seguridad de la Información"),
    ("ISO 37001:2016", "Gestión Antisoborno"),
    ("ISO 21001:2018", "Organizaciones Educativas"),
    ("ISO 20000-1:2018", "Gestión de Servicios TI"),
    ("ISO 50001:2018", "Gestión de la Energía"),
    ("ISO 22000:2018", "Gestión de Inocuidad Alimentaria"),
    ("ISO 56002:2019", "Gestión de la Innovación"),
]


def render() -> None:
    st.markdown("## 📂 Catálogo de Servicios")
    st.markdown(
        "Conoce toda la oferta de **Medina SST Empresarial SAS** y nuestra alianza estratégica con **Compecer**."
    )

    separador_seccion("Servicios Medina SST Empresarial SAS")

    cols_per_row = 2
    for i in range(0, len(_SERVICIOS_MEDINA), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(_SERVICIOS_MEDINA):
                break
            icono, titulo, desc = _SERVICIOS_MEDINA[idx]
            with col:
                st.markdown(
                    f"""
                    <div style="
                        background:#1E293B;
                        border:1px solid #334155;
                        border-left:4px solid #3B82F6;
                        border-radius:8px;
                        padding:16px 18px;
                        margin-bottom:14px;
                        min-height:110px;
                    ">
                        <div style="font-size:22px;margin-bottom:6px;">{icono}</div>
                        <div style="font-size:13px;font-weight:700;color:#F1F5F9;margin-bottom:6px;">{titulo}</div>
                        <div style="font-size:12px;color:#94A3B8;line-height:1.5;">{desc}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    separador_seccion("Alianza Estratégica — Compecer · Certificación ISO")

    st.markdown(
        """
        <div style="
            background:#0F2027;
            border:1px solid #1E3A5F;
            border-left:4px solid #F59E0B;
            border-radius:8px;
            padding:14px 18px;
            margin-bottom:20px;
            font-size:13px;
            color:#CBD5E1;
            line-height:1.7;
        ">
            A través de nuestra <strong style="color:#F59E0B;">alianza con Compecer</strong>,
            ofrecemos implementación y certificación en las principales normas ISO internacionales.
            Una sola alianza estratégica para cumplir SST <em>y</em> estándares de calidad mundial.
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols_iso = st.columns(2)
    for i, (norma, descripcion) in enumerate(_NORMAS_ISO):
        with cols_iso[i % 2]:
            st.markdown(
                f"""
                <div style="
                    background:#1E293B;
                    border:1px solid #334155;
                    border-left:4px solid #F59E0B;
                    border-radius:8px;
                    padding:12px 16px;
                    margin-bottom:10px;
                    display:flex;
                    align-items:center;
                    gap:12px;
                ">
                    <div style="
                        background:#78350F;
                        color:#FDE68A;
                        font-size:10px;
                        font-weight:800;
                        padding:4px 8px;
                        border-radius:4px;
                        white-space:nowrap;
                        min-width:110px;
                        text-align:center;
                    ">{norma}</div>
                    <div style="font-size:12px;color:#CBD5E1;">{descripcion}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()
    st.markdown(
        "<div style='text-align:center;font-size:12px;color:#64748B;'>"
        "¿Interesado en algún servicio? Usa el <strong>Motor de Prospección</strong> "
        "o <strong>Campañas</strong> para contactar clientes potenciales."
        "</div>",
        unsafe_allow_html=True,
    )
