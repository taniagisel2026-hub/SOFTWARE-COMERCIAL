import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from ..components.metrics import badge_estado, separador_seccion, tarjeta_kpi

_ROOT = Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ── Helpers de acceso a BD ─────────────────────────────────────────────────────

@st.cache_data(ttl=15)
def _cargar_prospectos() -> dict:
    """Carga prospectos con opt_out=False de EMPRESA_PROSPECTO."""
    try:
        from src.database.connection import get_session
        from src.database.models import EmpresaProspecto

        with get_session() as session:
            rows = (
                session.query(EmpresaProspecto)
                .filter(EmpresaProspecto.opt_out == False)
                .order_by(EmpresaProspecto.fecha_registro.desc())
                .all()
            )
            return {
                "ok": True,
                "data": [
                    {
                        "ID":         r.id_empresa,
                        "Empresa":    r.razon_social,
                        "Ciudad":     r.ciudad,
                        "Sector":     r.sector_economico or "—",
                        "Empleados":  r.num_empleados,
                        "Email":      r.email_contacto or "—",
                        "Teléfono":   r.telefono or "—",
                        "Contacto":   r.nombre_contacto or "—",
                        "Estado":     r.estado_prospecto,
                        "Fuente":     r.fuente_origen or "—",
                        "Registro":   str(r.fecha_registro),
                        "_tiene_email": bool(r.email_contacto),
                        "_riesgo":    r.nivel_riesgo_arl,
                        "_depto":     r.departamento,
                    }
                    for r in rows
                ],
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "data": []}


@st.cache_data(ttl=15)
def _cargar_optout() -> dict:
    """Carga registros con opt_out=True para la Lista Negra."""
    try:
        from src.database.connection import get_session
        from src.database.models import EmpresaProspecto

        with get_session() as session:
            rows = (
                session.query(EmpresaProspecto)
                .filter(EmpresaProspecto.opt_out == True)
                .order_by(EmpresaProspecto.fecha_opt_out.desc())
                .all()
            )
            return {
                "ok": True,
                "data": [
                    {
                        "ID":           r.id_empresa,
                        "Empresa":      r.razon_social,
                        "Ciudad":       r.ciudad,
                        "Sector":       r.sector_economico or "—",
                        "Fecha Opt-Out": str(r.fecha_opt_out) if r.fecha_opt_out else "—",
                        "Motivo":       r.motivo_opt_out or "No especificado",
                        "Email":        r.email_contacto or "—",
                    }
                    for r in rows
                ],
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "data": []}


def _orm_a_dominio(id_empresa: int):
    """Carga empresa de la BD y la convierte a entidad de dominio para EmailService."""
    from src.database.connection import get_session
    from src.database.models import EmpresaProspecto as ORM
    from src.domain.entities import (
        EmpresaProspecto as Dominio,
        EstadoProspecto,
        NivelRiesgo,
    )

    with get_session() as session:
        r = session.get(ORM, id_empresa)
        if not r:
            return None
        return Dominio(
            id_empresa=r.id_empresa,
            razon_social=r.razon_social,
            nit=r.nit,
            ciudad=r.ciudad,
            departamento=r.departamento,
            num_empleados=r.num_empleados,
            nivel_riesgo_arl=NivelRiesgo(r.nivel_riesgo_arl),
            sector_economico=r.sector_economico or "",
            direccion=r.direccion or "",
            telefono=r.telefono or "",
            email_contacto=r.email_contacto or "",
            nombre_contacto=r.nombre_contacto or "",
            cargo_contacto=r.cargo_contacto or "",
            estado_prospecto=EstadoProspecto(r.estado_prospecto),
            fuente_origen=r.fuente_origen or "",
            fecha_registro=r.fecha_registro,
            fecha_ultima_actualizacion=r.fecha_ultima_actualizacion,
        )


def _enviar_correo(id_empresa: int, tipo: str = "PRIMER_CONTACTO") -> tuple[bool, str]:
    """
    Envía un correo a una empresa usando EmailService.
    Usa delay_min=0 para envíos manuales desde la UI (sin espera entre correos).
    Retorna (éxito: bool, mensaje: str).
    """
    try:
        empresa = _orm_a_dominio(id_empresa)
        if not empresa:
            return False, "Empresa no encontrada en la base de datos."
        if not empresa.email_contacto:
            return False, "Esta empresa no tiene email registrado."

        from src.modules.compliance.habeas_data import HabeasDataError
        from src.modules.email import EmailService
        from src.modules.email.gmail_client import GmailSendError
        from src.modules.email.rate_limiter import RateLimiter, RateLimitExceededError

        # Sin delay artificial para envíos manuales desde UI
        svc = EmailService(rate_limiter=RateLimiter(delay_min_s=0, delay_max_s=1))
        svc.enviar(empresa, tipo, creado_por="Panel Web")
        return True, f"✓ Correo enviado a **{empresa.email_contacto}**"

    except Exception as exc:
        # Importamos aquí para evitar error si el módulo no está disponible
        tipo_exc = type(exc).__name__
        if "HabeasDataError" in tipo_exc:
            return False, f"🚫 Opt-out activo: {exc}"
        if "RateLimitExceededError" in tipo_exc:
            return False, f"⏸ Límite diario alcanzado. Intenta mañana."
        if "GmailSendError" in tipo_exc:
            return False, f"📧 Error Gmail API: {exc}"
        if "GmailAuthError" in tipo_exc:
            return False, "🔑 Gmail no autenticado. Configura `credentials/gmail_credentials.json`."
        return False, f"Error inesperado: {exc}"


def _registrar_optout(id_empresa: int, motivo: str) -> tuple[bool, str]:
    try:
        from src.modules.compliance.habeas_data import HabeasDataService
        HabeasDataService().registrar_opt_out(id_empresa, motivo)
        st.cache_data.clear()
        return True, "Opt-out registrado correctamente."
    except Exception as exc:
        return False, str(exc)


def _registrar_optin(id_empresa: int) -> tuple[bool, str]:
    try:
        from src.modules.compliance.habeas_data import HabeasDataService
        HabeasDataService().registrar_opt_in(id_empresa)
        st.cache_data.clear()
        return True, "Empresa reactivada correctamente."
    except Exception as exc:
        return False, str(exc)


# ── Página principal ──────────────────────────────────────────────────────────

def render() -> None:
    col_t, col_r = st.columns([6, 1])
    col_t.title("✉️ Campañas y Habeas Data")
    if col_r.button("🔄", help="Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption("Gestión de prospectos, secuencias de correo y control Ley 1581/2012")

    tab_prospectos, tab_optout = st.tabs(["📋 Prospectos en CRM", "🚫 Lista Negra (Opt-Out)"])

    with tab_prospectos:
        _render_prospectos()

    with tab_optout:
        _render_lista_negra()


def _render_prospectos() -> None:
    resultado = _cargar_prospectos()

    if not resultado["ok"]:
        st.error(f"Error al cargar prospectos: `{resultado['error']}`")
        st.info("Ejecuta `python -m src.database.init_db` para inicializar el esquema.")
        return

    datos = resultado["data"]

    # ── KPIs ──────────────────────────────────────────────────────────────────
    estados = [p["Estado"] for p in datos]
    c1, c2, c3, c4 = st.columns(4)
    with c1: tarjeta_kpi("Total en CRM", str(len(datos)), icono="🏢", color="#1B3A6B")
    with c2: tarjeta_kpi("Nuevos", str(estados.count("NUEVO")), icono="🔵", color="#1D4ED8")
    with c3: tarjeta_kpi("Con email", str(sum(1 for p in datos if p["_tiene_email"])), icono="📧", color="#7C3AED")
    with c4: tarjeta_kpi("Cierres", str(estados.count("CERRADO_GANADO")), icono="✅", color="#10B981")

    if not datos:
        st.info("📭 No hay prospectos registrados aún. Usa el **Motor de Prospección** para comenzar.")
        return

    # ── Filtros ────────────────────────────────────────────────────────────────
    st.divider()
    separador_seccion("Filtros")
    fc1, fc2, fc3 = st.columns(3)
    filtro_estado = fc1.selectbox(
        "Estado",
        ["Todos", "NUEVO", "EN_SEGUIMIENTO", "COTIZACION_ENVIADA", "NEGOCIACION", "CERRADO_GANADO"],
    )
    ciudades_disponibles = sorted({p["Ciudad"] for p in datos})
    filtro_ciudad = fc2.selectbox("Ciudad", ["Todas"] + ciudades_disponibles)
    filtro_texto  = fc3.text_input("Buscar", placeholder="Nombre, email o sector...")

    # Aplicar filtros
    filtrados = datos.copy()
    if filtro_estado != "Todos":
        filtrados = [p for p in filtrados if p["Estado"] == filtro_estado]
    if filtro_ciudad != "Todas":
        filtrados = [p for p in filtrados if p["Ciudad"] == filtro_ciudad]
    if filtro_texto:
        t = filtro_texto.lower()
        filtrados = [
            p for p in filtrados
            if t in p["Empresa"].lower()
            or t in p["Email"].lower()
            or t in p["Sector"].lower()
        ]

    separador_seccion(f"{len(filtrados)} prospectos")

    if not filtrados:
        st.warning("Ningún prospecto coincide con los filtros aplicados.")
        return

    # ── Tabla de prospectos ────────────────────────────────────────────────────
    for p in filtrados:
        col_info, col_badge, col_btn = st.columns([4, 2, 2])

        with col_info:
            st.markdown(f"**{p['Empresa']}**")
            st.markdown(
                f"<small style='color:#6B7280;'>"
                f"📍 {p['Ciudad']} &nbsp;·&nbsp; 👥 {p['Empleados']} emp. &nbsp;·&nbsp; "
                f"📧 {p['Email']} &nbsp;·&nbsp; 🔗 {p['Fuente']}"
                f"</small>",
                unsafe_allow_html=True,
            )

        with col_badge:
            st.markdown(badge_estado(p["Estado"]), unsafe_allow_html=True)

        with col_btn:
            if p["_tiene_email"]:
                if st.button("📨 Enviar correo", key=f"email_{p['ID']}", use_container_width=True):
                    with st.spinner(f"Enviando a {p['Email']}..."):
                        ok, msg = _enviar_correo(p["ID"])
                    if ok:
                        st.success(msg)
                        st.cache_data.clear()
                    else:
                        # Distinguir entre warning y error según el tipo
                        if "Opt-out" in msg or "Límite" in msg:
                            st.warning(msg)
                        else:
                            st.error(msg)
            else:
                st.button("📨 Sin email", key=f"noemail_{p['ID']}",
                          disabled=True, use_container_width=True)

        st.divider()

    # ── Acción masiva ──────────────────────────────────────────────────────────
    separador_seccion("Acciones masivas")
    nuevos_con_email = [p for p in filtrados if p["Estado"] == "NUEVO" and p["_tiene_email"]]

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if st.button(
            f"🚀 Enviar PRIMER CONTACTO a {len(nuevos_con_email)} prospectos nuevos",
            type="primary",
            use_container_width=True,
            disabled=len(nuevos_con_email) == 0,
        ):
            _disparar_lote(nuevos_con_email)

    with col_m2:
        if st.button("📤 Exportar tabla a CSV", use_container_width=True):
            cols_visibles = ["Empresa", "Ciudad", "Sector", "Empleados", "Email", "Estado", "Fuente", "Registro"]
            df = pd.DataFrame([{k: p[k] for k in cols_visibles} for p in filtrados])
            st.download_button(
                "⬇️ Descargar CSV",
                df.to_csv(index=False).encode("utf-8"),
                "prospectos_crm.csv",
                "text/csv",
            )


def _disparar_lote(prospectos: list[dict]) -> None:
    """Envía correos a un lote de prospectos con barra de progreso y reporte final."""
    enviados, fallidos, rate_stop = 0, 0, False
    errores: list[str] = []

    barra    = st.progress(0, text="Iniciando envío masivo...")
    contador = st.empty()

    for i, p in enumerate(prospectos):
        if rate_stop:
            break

        barra.progress((i + 1) / len(prospectos), text=f"Enviando {i+1}/{len(prospectos)}...")
        contador.markdown(f"✉️ Procesando: **{p['Empresa']}**")

        ok, msg = _enviar_correo(p["ID"])
        if ok:
            enviados += 1
        else:
            if "Límite diario" in msg:
                rate_stop = True
                errores.append(f"⏸ Rate limit alcanzado en empresa #{i+1}. Continúa mañana.")
            else:
                fallidos += 1
                errores.append(f"{p['Empresa']}: {msg}")

    barra.progress(1.0, text="✅ Proceso completado")
    contador.empty()

    # Reporte final
    if enviados:
        st.success(f"✅ {enviados} correos enviados correctamente.")
    if rate_stop:
        st.warning(f"⏸ Proceso detenido: límite diario alcanzado tras {enviados} envíos.")
    if fallidos:
        with st.expander(f"⚠️ {fallidos} envíos con error"):
            for e in errores:
                st.markdown(f"- {e}")

    st.cache_data.clear()


def _render_lista_negra() -> None:
    resultado = _cargar_optout()

    st.markdown("""
    <div style="background:#FEF2F2;border-left:4px solid #EF4444;
                border-radius:6px;padding:14px 18px;margin-bottom:16px;">
        <strong>⚠️ Empresas con Opt-Out activo — Ley 1581 de 2012</strong><br>
        <small style="color:#6B7280;">
        El sistema bloquea automáticamente cualquier intento de comunicación
        hacia estas empresas. Para reactivarlas el titular debe autorizarlo expresamente.
        </small>
    </div>
    """, unsafe_allow_html=True)

    if not resultado["ok"]:
        st.error(f"Error al cargar la lista negra: `{resultado['error']}`")
        return

    datos = resultado["data"]
    tarjeta_kpi("Total excluidas", str(len(datos)), icono="🚫", color="#EF4444")

    if not datos:
        st.success("✅ No hay empresas en la lista negra. Todos los registros están activos.")
    else:
        # Tabla resumen
        df_optout = pd.DataFrame(datos)
        st.dataframe(
            df_optout[["Empresa", "Ciudad", "Sector", "Fecha Opt-Out", "Motivo", "Email"]],
            use_container_width=True,
            hide_index=True,
        )

        # Acciones individuales de reactivación
        separador_seccion("Reactivar empresa (requiere autorización expresa del titular)")
        for p in datos:
            c1, c2 = st.columns([5, 1])
            c1.markdown(
                f"**{p['Empresa']}** — <small style='color:#6B7280;'>"
                f"Opt-out: {p['Fecha Opt-Out']} · {p['Motivo']}</small>",
                unsafe_allow_html=True,
            )
            if c2.button("↩️ Reactivar", key=f"optin_{p['ID']}", use_container_width=True):
                ok, msg = _registrar_optin(p["ID"])
                if ok:
                    st.success(f"✅ {p['Empresa']} reactivada.")
                    st.rerun()
                else:
                    st.error(msg)

    # ── Formulario de registro manual de opt-out ───────────────────────────────
    separador_seccion("Registrar nueva exclusión manual")
    with st.form("form_optout_manual"):
        col_id, col_motivo = st.columns([1, 3])
        empresa_id = col_id.number_input("ID empresa", min_value=1, step=1)
        motivo     = col_motivo.text_input(
            "Motivo", value="Solicitud del titular de los datos",
        )
        enviado = st.form_submit_button("🚫 Registrar Opt-Out", type="primary")

    if enviado:
        ok, msg = _registrar_optout(int(empresa_id), motivo)
        if ok:
            st.success(f"✅ {msg}")
            st.rerun()
        else:
            st.error(f"Error: {msg}")
