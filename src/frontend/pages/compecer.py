"""Módulo de Alianza Compecer — registro y seguimiento de referidos."""
from datetime import date

import streamlit as st

from ..components.metrics import separador_seccion, tarjeta_kpi

_NORMAS_ISO = [
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

_ESTADOS = [
    "ENVIADO",
    "EN_NEGOCIACION",
    "CONTRATO_FIRMADO",
    "BONIFICACION_COBRADA",
    "PERDIDO",
]

_ESTADO_LABEL = {
    "ENVIADO":             "📤 Enviado",
    "EN_NEGOCIACION":      "🔄 En negociación",
    "CONTRATO_FIRMADO":    "✅ Contrato firmado",
    "BONIFICACION_COBRADA":"💰 Bonificación cobrada",
    "PERDIDO":             "❌ Perdido",
}

_ESTADO_COLOR = {
    "ENVIADO":             "#3B82F6",
    "EN_NEGOCIACION":      "#F59E0B",
    "CONTRATO_FIRMADO":    "#10B981",
    "BONIFICACION_COBRADA":"#8B5CF6",
    "PERDIDO":             "#EF4444",
}


def _cargar_referidos() -> list[dict]:
    try:
        from src.database.connection import get_session
        from src.database.models import ReferidoCompecer
        with get_session() as session:
            rows = session.query(ReferidoCompecer).order_by(
                ReferidoCompecer.fecha_referido.desc()
            ).all()
            return [
                {
                    "id":            r.id_referido,
                    "Empresa":       r.razon_social,
                    "NIT":           r.nit or "—",
                    "Contacto":      r.nombre_contacto or "—",
                    "Email":         r.email_contacto or "—",
                    "Teléfono":      r.telefono or "—",
                    "Ciudad":        r.ciudad or "—",
                    "Norma ISO":     r.norma_iso,
                    "Estado":        r.estado,
                    "Bonificación":  r.valor_bonificacion or 0,
                    "Notas":         r.notas or "—",
                    "Fecha":         str(r.fecha_referido),
                    "Registrado por":r.registrado_por or "—",
                }
                for r in rows
            ]
    except Exception as exc:
        st.error(f"Error cargando referidos: {exc}")
        return []


def _guardar_referido(datos: dict) -> bool:
    try:
        from src.database.connection import get_session
        from src.database.models import ReferidoCompecer
        with get_session() as session:
            session.add(ReferidoCompecer(
                razon_social=datos["razon_social"],
                nit=datos.get("nit") or None,
                nombre_contacto=datos.get("nombre_contacto") or None,
                email_contacto=datos.get("email_contacto") or None,
                telefono=datos.get("telefono") or None,
                ciudad=datos.get("ciudad") or None,
                norma_iso=datos["norma_iso"],
                fecha_referido=date.today(),
                estado="ENVIADO",
                notas=datos.get("notas") or None,
                registrado_por=datos.get("registrado_por") or "Asesor",
            ))
        return True
    except Exception as exc:
        st.error(f"Error guardando referido: {exc}")
        return False


def _actualizar_estado(id_referido: int, nuevo_estado: str, bonificacion: float, notas: str) -> bool:
    try:
        from src.database.connection import get_session
        from src.database.models import ReferidoCompecer
        with get_session() as session:
            r = session.get(ReferidoCompecer, id_referido)
            if r:
                r.estado = nuevo_estado
                r.valor_bonificacion = bonificacion if bonificacion > 0 else None
                r.notas = notas or None
                if nuevo_estado in ("CONTRATO_FIRMADO", "BONIFICACION_COBRADA"):
                    r.fecha_cierre = date.today()
        return True
    except Exception as exc:
        st.error(f"Error actualizando estado: {exc}")
        return False


def render() -> None:
    # ── Encabezado ────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;">
        <div>
            <div style="font-size:22px;font-weight:800;color:#F1F5F9;">
                🤝 Alianza Compecer
            </div>
            <div style="font-size:12px;color:#94A3B8;">
                Organismo Internacional de Certificación · Seguimiento de referidos
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    referidos = _cargar_referidos()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total        = len(referidos)
    enviados     = sum(1 for r in referidos if r["Estado"] == "ENVIADO")
    en_neg       = sum(1 for r in referidos if r["Estado"] == "EN_NEGOCIACION")
    cerrados     = sum(1 for r in referidos if r["Estado"] == "CONTRATO_FIRMADO")
    bonificados  = sum(1 for r in referidos if r["Estado"] == "BONIFICACION_COBRADA")
    total_bonif  = sum(r["Bonificación"] for r in referidos if r["Estado"] == "BONIFICACION_COBRADA")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total referidos",     total)
    c2.metric("Enviados",            enviados)
    c3.metric("En negociación",      en_neg)
    c4.metric("Contratos firmados",  cerrados)
    c5.metric("Bonificaciones cobradas", f"$ {total_bonif:,.0f}".replace(",", ".") if total_bonif else "$ 0")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📋 Referidos", "➕ Nuevo referido", "🔄 Actualizar estado"])

    # ── Tab 1: Lista de referidos ─────────────────────────────────────────────
    with tab1:
        if not referidos:
            st.info("Aún no hay referidos registrados. Usa la pestaña **Nuevo referido** para agregar el primero.")
        else:
            for r in referidos:
                color  = _ESTADO_COLOR.get(r["Estado"], "#64748B")
                label  = _ESTADO_LABEL.get(r["Estado"], r["Estado"])
                bonif  = f"$ {r['Bonificación']:,.0f}".replace(",", ".") if r["Bonificación"] else "Pendiente"
                with st.container():
                    st.markdown(
                        f"""
                        <div style="
                            background:#1E293B;
                            border:1px solid #334155;
                            border-left:4px solid {color};
                            border-radius:8px;
                            padding:14px 18px;
                            margin-bottom:10px;
                        ">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <div>
                                    <span style="font-size:14px;font-weight:700;color:#F1F5F9;">{r['Empresa']}</span>
                                    <span style="font-size:11px;color:#64748B;margin-left:10px;">NIT: {r['NIT']}</span>
                                </div>
                                <span style="
                                    background:{color}22;color:{color};
                                    font-size:11px;font-weight:700;
                                    padding:3px 10px;border-radius:12px;
                                ">{label}</span>
                            </div>
                            <div style="margin-top:8px;font-size:12px;color:#94A3B8;display:flex;gap:24px;flex-wrap:wrap;">
                                <span>🏅 {r['Norma ISO']}</span>
                                <span>📍 {r['Ciudad']}</span>
                                <span>📅 {r['Fecha']}</span>
                                <span>💰 Bonificación: <b style="color:#F1F5F9;">{bonif}</b></span>
                            </div>
                            {'<div style="margin-top:6px;font-size:11px;color:#64748B;">📝 ' + r['Notas'] + '</div>' if r['Notas'] != '—' else ''}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # ── Tab 2: Nuevo referido ─────────────────────────────────────────────────
    with tab2:
        separador_seccion("Datos del cliente referido a Compecer")
        with st.form("form_nuevo_referido", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                razon_social    = st.text_input("Razón Social *", placeholder="Empresa SAS")
                nit             = st.text_input("NIT", placeholder="900123456-1")
                nombre_contacto = st.text_input("Nombre del contacto", placeholder="Gerente")
                email_contacto  = st.text_input("Email", placeholder="gerencia@empresa.com")
            with col2:
                telefono        = st.text_input("Teléfono", placeholder="601 234 5678")
                ciudad          = st.text_input("Ciudad", placeholder="Bogotá D.C.")
                norma_iso       = st.selectbox("Norma ISO que necesita *", _NORMAS_ISO)
                registrado_por  = st.text_input("Registrado por", placeholder="Nombre del asesor")

            notas = st.text_area("Notas (opcional)", placeholder="Contexto de la referencia, cómo surgió la oportunidad...")

            enviado = st.form_submit_button("✅ Registrar referido", type="primary", use_container_width=True)

        if enviado:
            if not razon_social.strip():
                st.error("La Razón Social es obligatoria.")
            else:
                ok = _guardar_referido({
                    "razon_social":    razon_social.strip(),
                    "nit":             nit,
                    "nombre_contacto": nombre_contacto,
                    "email_contacto":  email_contacto,
                    "telefono":        telefono,
                    "ciudad":          ciudad,
                    "norma_iso":       norma_iso,
                    "registrado_por":  registrado_por,
                    "notas":           notas,
                })
                if ok:
                    st.success(f"✅ Referido registrado: **{razon_social.strip()}** — {norma_iso}")
                    st.cache_data.clear()

    # ── Tab 3: Actualizar estado ───────────────────────────────────────────────
    with tab3:
        if not referidos:
            st.info("No hay referidos registrados aún.")
        else:
            separador_seccion("Selecciona el referido a actualizar")
            opciones = {f"{r['Empresa']} — {r['Norma ISO']} ({r['Estado']})": r["id"] for r in referidos}
            seleccion = st.selectbox("Referido", list(opciones.keys()))
            id_sel = opciones[seleccion]

            col1, col2 = st.columns(2)
            with col1:
                nuevo_estado = st.selectbox(
                    "Nuevo estado",
                    _ESTADOS,
                    format_func=lambda x: _ESTADO_LABEL.get(x, x),
                )
            with col2:
                bonificacion = st.number_input(
                    "Valor bonificación (si aplica)",
                    min_value=0, step=50000, format="%d",
                )

            notas_upd = st.text_area("Notas de seguimiento")

            if st.button("💾 Guardar cambios", type="primary", use_container_width=True):
                ok = _actualizar_estado(id_sel, nuevo_estado, float(bonificacion), notas_upd)
                if ok:
                    st.success("Estado actualizado correctamente.")
                    st.cache_data.clear()
                    st.rerun()
