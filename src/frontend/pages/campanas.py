import sys
from datetime import date
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
                .order_by(
                    EmpresaProspecto.fecha_registro.desc(),
                    EmpresaProspecto.id_empresa.desc(),
                )
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


@st.cache_data(ttl=15)
def _cargar_clientes_firmados() -> dict:
    try:
        from src.database.connection import get_session
        from src.database.models import EmpresaProspecto, HistorialInteracciones

        with get_session() as session:
            rows = (
                session.query(EmpresaProspecto)
                .filter(EmpresaProspecto.estado_prospecto == "CERRADO_GANADO")
                .order_by(EmpresaProspecto.fecha_ultima_actualizacion.desc())
                .all()
            )
            resultado = []
            for r in rows:
                # Buscar el registro de cierre en el historial
                cierre = (
                    session.query(HistorialInteracciones)
                    .filter(
                        HistorialInteracciones.id_empresa == r.id_empresa,
                        HistorialInteracciones.tipo_interaccion == "CLIENTE_FIRMADO",
                    )
                    .order_by(HistorialInteracciones.fecha_interaccion.desc())
                    .first()
                )
                resultado.append({
                    "ID":           r.id_empresa,
                    "Empresa":      r.razon_social,
                    "Ciudad":       r.ciudad,
                    "Sector":       r.sector_economico or "—",
                    "Email":        r.email_contacto or "—",
                    "Teléfono":     r.telefono or "—",
                    "Contacto":     r.nombre_contacto or "—",
                    "Fuente":       r.fuente_origen or "—",
                    "Fecha cierre": str(r.fecha_ultima_actualizacion),
                    "Canal":        cierre.canal if cierre else "—",
                    "Notas":        cierre.notas_seguimiento if cierre else "—",
                })
            return {"ok": True, "data": resultado}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "data": []}


def _marcar_cliente_firmado(id_empresa: int, canal: str, notas: str) -> tuple[bool, str]:
    try:
        from datetime import datetime
        from src.database.connection import get_session
        from src.database.models import EmpresaProspecto, HistorialInteracciones

        with get_session() as session:
            empresa = session.get(EmpresaProspecto, id_empresa)
            if not empresa:
                return False, "Empresa no encontrada."
            if empresa.estado_prospecto == "CERRADO_GANADO":
                return False, f"{empresa.razon_social} ya está marcada como cliente firmado."

            empresa.estado_prospecto = "CERRADO_GANADO"
            empresa.fecha_ultima_actualizacion = date.today()

            session.add(HistorialInteracciones(
                id_empresa=id_empresa,
                tipo_interaccion="CLIENTE_FIRMADO",
                canal=canal,
                asunto="Cliente firmó contrato",
                notas_seguimiento=notas or "Sin notas adicionales.",
                fecha_interaccion=datetime.now(),
                responsable="Panel Web",
            ))
            nombre = empresa.razon_social

        st.cache_data.clear()
        return True, nombre
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


# ── Ficha Centralizada del Cliente ────────────────────────────────────────────

@st.cache_data(ttl=30)
def _cargar_ficha_empresa(id_empresa: int) -> dict:
    """Carga datos completos de una empresa para la Ficha Centralizada."""
    try:
        from src.database.connection import get_session
        from src.database.models import (
            Cotizacion,
            EmpresaProspecto,
            HistorialInteracciones,
        )

        with get_session() as session:
            emp = session.get(EmpresaProspecto, id_empresa)
            if not emp:
                return {"ok": False, "error": "Empresa no encontrada"}

            interacciones = (
                session.query(HistorialInteracciones)
                .filter(HistorialInteracciones.id_empresa == id_empresa)
                .order_by(HistorialInteracciones.fecha_interaccion.desc())
                .all()
            )
            cotizaciones = (
                session.query(Cotizacion)
                .filter(Cotizacion.id_empresa == id_empresa)
                .order_by(Cotizacion.fecha_emision.desc())
                .all()
            )

            return {
                "ok": True,
                "empresa": {
                    "razon_social":     emp.razon_social,
                    "nit":              emp.nit,
                    "ciudad":           emp.ciudad,
                    "departamento":     emp.departamento,
                    "nivel_riesgo_arl": emp.nivel_riesgo_arl,
                    "sector_economico": emp.sector_economico or "—",
                    "email_contacto":   emp.email_contacto or "—",
                    "telefono":         emp.telefono or "—",
                    "nombre_contacto":  emp.nombre_contacto or "—",
                    "cargo_contacto":   emp.cargo_contacto or "—",
                    "num_empleados":    emp.num_empleados,
                    "estado_prospecto": emp.estado_prospecto,
                    "fuente_origen":    emp.fuente_origen or "—",
                    "fecha_registro":   str(emp.fecha_registro),
                },
                "interacciones": [
                    {
                        "fecha":       str(i.fecha_interaccion)[:16],
                        "canal":       (i.canal or "—").upper(),
                        "tipo":        i.tipo_interaccion,
                        "asunto":      i.asunto or "—",
                        "estado":      i.estado_respuesta or "—",
                        "responsable": i.responsable or "—",
                    }
                    for i in interacciones
                ],
                "cotizaciones": [
                    {
                        "id":            c.id_cotizacion,
                        "codigo":        c.codigo_cotizacion,
                        "fecha":         str(c.fecha_emision),
                        "nivel":         c.nivel_estandares,
                        "empleados":     c.num_empleados_cotizados,
                        "total_proyecto": float(c.valor_total_proyecto),
                        "total_mensual": float(c.valor_total_mensual),
                        "estado":        c.estado_cotizacion,
                        "url_pdf":       c.url_documento_pdf or "",
                    }
                    for c in cotizaciones
                ],
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@st.cache_data(ttl=3600)
def _regenerar_pdf_bytes(id_cotizacion: int) -> bytes | None:
    """Reconstruye la cotización desde BD y genera el PDF en memoria."""
    try:
        import tempfile
        from decimal import Decimal
        from pathlib import Path as _Path

        from src.database.connection import get_session
        from src.database.models import (
            Cotizacion as ORM_C,
            EmpresaProspecto as ORM_E,
        )
        from src.domain.entities import (
            Cotizacion as DomCotizacion,
            EmpresaProspecto as DomEmpresa,
            EstadoCotizacion,
            EstadoProspecto,
            NivelEstandares,
            NivelRiesgo,
            ServicioCotizado,
        )
        from src.modules.cotizador.pdf_exporter import exportar_pdf

        with get_session() as session:
            c = session.get(ORM_C, id_cotizacion)
            if not c:
                return None
            e = session.get(ORM_E, c.id_empresa)
            if not e:
                return None

            servicios = [
                ServicioCotizado(
                    nombre=svc.get("nombre", ""),
                    descripcion=svc.get("descripcion", ""),
                    cantidad_horas=int(svc.get("cantidad_horas", 0)),
                    valor_unitario=Decimal(str(svc.get("valor_unitario", "0"))),
                )
                for svc in (c.servicios_incluidos or [])
            ]

            cot_dom = DomCotizacion(
                id_cotizacion=c.id_cotizacion,
                id_empresa=c.id_empresa,
                codigo_cotizacion=c.codigo_cotizacion,
                version=c.version,
                nivel_estandares=NivelEstandares(c.nivel_estandares),
                num_empleados_cotizados=c.num_empleados_cotizados,
                nivel_riesgo=NivelRiesgo(c.nivel_riesgo),
                servicios_incluidos=servicios,
                valor_viaticos=Decimal(str(c.valor_viaticos)),
                moneda=c.moneda,
                estado_cotizacion=EstadoCotizacion(c.estado_cotizacion),
                fecha_emision=c.fecha_emision,
                fecha_vencimiento=c.fecha_vencimiento,
                url_documento_pdf=c.url_documento_pdf or "",
                creado_por=c.creado_por,
            )

            emp_dom = DomEmpresa(
                id_empresa=e.id_empresa,
                razon_social=e.razon_social,
                nit=e.nit,
                ciudad=e.ciudad,
                departamento=e.departamento,
                num_empleados=e.num_empleados,
                nivel_riesgo_arl=NivelRiesgo(e.nivel_riesgo_arl),
                sector_economico=e.sector_economico or "",
                direccion=e.direccion or "",
                telefono=e.telefono or "",
                email_contacto=e.email_contacto or "",
                nombre_contacto=e.nombre_contacto or "",
                cargo_contacto=e.cargo_contacto or "",
                estado_prospecto=EstadoProspecto(e.estado_prospecto),
                fuente_origen=e.fuente_origen or "",
                fecha_registro=e.fecha_registro,
                fecha_ultima_actualizacion=e.fecha_ultima_actualizacion,
            )

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = _Path(tmp.name)
        exportar_pdf(cot_dom, emp_dom, output_path=tmp_path)
        data = tmp_path.read_bytes()
        tmp_path.unlink(missing_ok=True)
        return data

    except Exception:
        return None


def _render_ficha_cliente(id_empresa: int) -> None:
    """Renderiza la Ficha Centralizada del Cliente."""
    ficha = _cargar_ficha_empresa(id_empresa)

    if not ficha["ok"]:
        st.error(f"Error al cargar ficha: {ficha['error']}")
        return

    emp = ficha["empresa"]

    st.markdown(
        "<div style='background:#EEF2F9;border-left:4px solid #1B3A6B;"
        "border-radius:8px;padding:14px 22px 10px;margin:10px 0 4px;'>"
        "<span style='font-size:17px;font-weight:700;color:#1B3A6B;'>"
        "🗂️ Ficha Centralizada del Cliente</span></div>",
        unsafe_allow_html=True,
    )

    # ── Datos generales y contacto ────────────────────────────────────────────
    col_gen, col_ctc = st.columns(2)

    with col_gen:
        separador_seccion("Datos generales")
        st.markdown(
            f"<b style='font-size:15px;color:#1B3A6B;'>{emp['razon_social']}</b>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"📋 **NIT:** `{emp['nit']}`  \n"
            f"📍 **Ciudad:** {emp['ciudad']}, {emp['departamento']}  \n"
            f"⚠️ **Riesgo ARL:** Clase {emp['nivel_riesgo_arl']}  \n"
            f"🏭 **Sector:** {emp['sector_economico']}  \n"
            f"👥 **Empleados:** {emp['num_empleados']}  \n"
            f"🔗 **Fuente:** {emp['fuente_origen']}  \n"
            f"📅 **Registro:** {emp['fecha_registro']}"
        )

    with col_ctc:
        separador_seccion("Contacto y estado CRM")
        st.markdown(
            f"👤 **{emp['nombre_contacto']}** — {emp['cargo_contacto']}  \n"
            f"📧 {emp['email_contacto']}  \n"
            f"📞 {emp['telefono']}"
        )
        _COLOR_ESTADO = {
            "NUEVO":              "#1D4ED8",
            "EN_SEGUIMIENTO":     "#7C3AED",
            "COTIZACION_ENVIADA": "#D97706",
            "NEGOCIACION":        "#EA580C",
            "CERRADO_GANADO":     "#10B981",
            "CERRADO_PERDIDO":    "#EF4444",
        }
        estado = emp["estado_prospecto"]
        color  = _COLOR_ESTADO.get(estado, "#6B7280")
        st.markdown(
            f"**Estado en embudo:**&nbsp;"
            f"<span style='background:{color};color:white;padding:3px 10px;"
            f"border-radius:12px;font-size:12px;font-weight:600;'>{estado}</span>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Historial de interacciones ────────────────────────────────────────────
    separador_seccion("Historial de interacciones — Email y WhatsApp")
    hist_canal = [
        i for i in ficha["interacciones"]
        if i["canal"] in ("EMAIL", "WHATSAPP")
    ]

    if not hist_canal:
        st.info("Sin interacciones por Email o WhatsApp registradas aún.")
    else:
        df_hist = pd.DataFrame(hist_canal).rename(columns={
            "fecha": "Fecha", "canal": "Canal", "tipo": "Tipo",
            "asunto": "Asunto", "estado": "Respuesta",
        })
        st.dataframe(
            df_hist[["Fecha", "Canal", "Tipo", "Asunto", "Respuesta"]],
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # ── Cotizaciones históricas ───────────────────────────────────────────────
    separador_seccion("Cotizaciones históricas")
    cotizaciones = ficha["cotizaciones"]

    if not cotizaciones:
        st.info("No hay cotizaciones generadas para esta empresa.")
    else:
        _COLOR_COT = {
            "BORRADOR":  "#94A3B8",
            "ENVIADA":   "#3B82F6",
            "ACEPTADA":  "#10B981",
            "RECHAZADA": "#EF4444",
            "VENCIDA":   "#F59E0B",
        }
        for cot in cotizaciones:
            col_cot, col_dl = st.columns([5, 1])

            with col_cot:
                est_c = cot["estado"]
                col_c = _COLOR_COT.get(est_c, "#94A3B8")
                total_fmt   = f"$ {cot['total_proyecto']:,.0f}".replace(",", ".")
                mensual_fmt = f"$ {cot['total_mensual']:,.0f}".replace(",", ".")
                st.markdown(
                    f"**{cot['codigo']}** &nbsp;"
                    f"<span style='background:{col_c};color:white;padding:2px 9px;"
                    f"border-radius:10px;font-size:11px;'>{est_c}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<small style='color:#6B7280;'>"
                    f"📅 {cot['fecha']} &nbsp;·&nbsp; 📊 {cot['nivel']} "
                    f"&nbsp;·&nbsp; 👥 {cot['empleados']} emp. "
                    f"&nbsp;·&nbsp; 💰 {total_fmt} COP/año "
                    f"&nbsp;·&nbsp; 📆 {mensual_fmt} COP/mes"
                    f"</small>",
                    unsafe_allow_html=True,
                )

            with col_dl:
                # Leer PDF guardado en disco; si no existe, regenerar desde BD
                pdf_bytes: bytes | None = None
                url = cot["url_pdf"]
                if url:
                    from pathlib import Path as _P
                    p = _P(url)
                    if p.exists():
                        pdf_bytes = p.read_bytes()
                if pdf_bytes is None:
                    with st.spinner(""):
                        pdf_bytes = _regenerar_pdf_bytes(cot["id"])

                if pdf_bytes:
                    st.download_button(
                        "⬇️ PDF",
                        data=pdf_bytes,
                        file_name=f"{cot['codigo']}.pdf",
                        mime="application/pdf",
                        key=f"pdf_dl_{cot['id']}",
                        use_container_width=True,
                    )
                else:
                    st.button(
                        "📄 Sin PDF",
                        key=f"nopdf_{cot['id']}",
                        disabled=True,
                        use_container_width=True,
                    )

            st.markdown(
                "<hr style='margin:6px 0;border:none;border-top:1px solid #E2E8F0;'>",
                unsafe_allow_html=True,
            )

    st.divider()


# ── Página principal ──────────────────────────────────────────────────────────

def _auto_cadencia() -> None:
    """Ejecuta la cadencia automáticamente una vez al día al abrir el software."""
    # PAUSADO — pendiente configurar nuevo correo y datos
    return

    hoy = str(date.today())
    if st.session_state.get("_cadencia_ejecutada") == hoy:
        return
    st.session_state["_cadencia_ejecutada"] = hoy
    try:
        from src.modules.outreach.sequence_orchestrator import SequenceOrchestrator
        resultados = SequenceOrchestrator().procesar_pendientes(creado_por="Auto")
        enviados = [r for r in resultados if r.ok and r.accion in ("DIA_4", "DIA_8")]
        dia4 = [r for r in enviados if r.accion == "DIA_4"]
        dia8 = [r for r in enviados if r.accion == "DIA_8"]
        st.session_state["_cadencia_resultado_hoy"] = {
            "dia4": [r.razon_social for r in dia4],
            "dia8": [r.razon_social for r in dia8],
        }
    except Exception:
        pass


def _render_resumen_cadencia() -> None:
    """Muestra qué correos de cadencia se enviaron hoy."""
    resultado = st.session_state.get("_cadencia_resultado_hoy")
    hoy = str(date.today())

    # También consulta la BD para mostrar todo lo enviado hoy
    try:
        from src.database.connection import get_session
        from src.database.models import HistorialInteracciones, EmpresaProspecto as _EmpORM
        from src.modules.outreach.sequence_orchestrator import TAG_DIA_1, TAG_DIA_4, TAG_DIA_8
        from datetime import datetime

        with get_session() as s:
            def _contar(tag):
                return (
                    s.query(HistorialInteracciones)
                    .filter(
                        HistorialInteracciones.tipo_interaccion == "SECUENCIA_CADENCIA",
                        HistorialInteracciones.notas_seguimiento.like(f"{tag}%"),
                        HistorialInteracciones.fecha_interaccion >= datetime.strptime(hoy, "%Y-%m-%d"),
                    )
                    .count()
                )
            n1 = _contar(TAG_DIA_1)
            n4 = _contar(TAG_DIA_4)
            n8 = _contar(TAG_DIA_8)
    except Exception:
        n1 = n4 = n8 = 0

    separador_seccion(f"Cadencia de hoy — {hoy}")
    c1, c2, c3 = st.columns(3)
    with c1: tarjeta_kpi("Día 1 enviados hoy", str(n1), icono="📨", color="#1D4ED8")
    with c2: tarjeta_kpi("Día 4 enviados hoy", str(n4), icono="📨", color="#7C3AED")
    with c3: tarjeta_kpi("Día 8 enviados hoy", str(n8), icono="📨", color="#059669")

    if n4 == 0 and n8 == 0:
        st.info("Hoy no había empresas pendientes de Día 4 o Día 8.")


def render() -> None:
    _auto_cadencia()

    col_t, col_r = st.columns([6, 1])
    col_t.title("✉️ Campañas y Habeas Data")
    if col_r.button("🔄", help="Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption("Gestión de prospectos, secuencias de correo y control Ley 1581/2012")
    _render_resumen_cadencia()

    tab_prospectos, tab_firmados, tab_optout = st.tabs([
        "📋 Prospectos en CRM",
        "✅ Clientes Firmados",
        "🚫 Lista Negra (Opt-Out)",
    ])

    with tab_prospectos:
        _render_prospectos()

    with tab_firmados:
        _render_clientes_firmados()

    with tab_optout:
        _render_lista_negra()


def _render_clientes_firmados() -> None:
    separador_seccion("Registrar nuevo cliente firmado")
    st.caption("Cuando tu jefe te confirme que un prospecto firmó, búscalo aquí y márcalo.")

    resultado_todos = _cargar_prospectos()
    prospectos_activos = [
        p for p in resultado_todos.get("data", [])
        if p["Estado"] != "CERRADO_GANADO"
    ]

    with st.form("form_cliente_firmado"):
        col_emp, col_canal = st.columns([3, 2])
        nombres = ["— Selecciona una empresa —"] + [p["Empresa"] for p in prospectos_activos]
        empresa_sel = col_emp.selectbox("Empresa", options=nombres)
        canal = col_canal.selectbox(
            "¿Cómo te contactó?",
            ["Correo electrónico", "WhatsApp", "Redes sociales", "Llamada telefónica", "Otro"],
        )
        notas = st.text_input("Notas (opcional)", placeholder="Ej: Me escribió el martes después del correo del Día 8")
        confirmar = st.form_submit_button("✅ Marcar como cliente firmado", type="primary")

    if confirmar:
        if empresa_sel == "— Selecciona una empresa —":
            st.warning("Selecciona una empresa primero.")
        else:
            id_emp = next(p["ID"] for p in prospectos_activos if p["Empresa"] == empresa_sel)
            ok, msg = _marcar_cliente_firmado(id_emp, canal, notas)
            if ok:
                st.success(f"✅ **{msg}** registrada como cliente firmado.")
                st.rerun()
            else:
                st.error(msg)

    st.divider()
    separador_seccion("Mis clientes firmados")

    resultado = _cargar_clientes_firmados()
    if not resultado["ok"]:
        st.error(f"Error: {resultado['error']}")
        return

    clientes = resultado["data"]
    tarjeta_kpi("Total clientes firmados", str(len(clientes)), icono="✅", color="#10B981")

    if not clientes:
        st.info("Aún no hay clientes firmados registrados.")
        return

    st.divider()
    for c in clientes:
        col_info, col_canal = st.columns([5, 2])
        with col_info:
            st.markdown(f"**{c['Empresa']}**")
            st.markdown(
                f"<small style='color:#6B7280;'>"
                f"📍 {c['Ciudad']} &nbsp;·&nbsp; 📧 {c['Email']} &nbsp;·&nbsp; "
                f"👤 {c['Contacto']} &nbsp;·&nbsp; 🔗 Origen: {c['Fuente']} &nbsp;·&nbsp; "
                f"📅 Firmó: {c['Fecha cierre']}"
                f"</small>",
                unsafe_allow_html=True,
            )
            if c["Notas"] and c["Notas"] != "—":
                st.markdown(
                    f"<small style='color:#475569;'>📝 {c['Notas']}</small>",
                    unsafe_allow_html=True,
                )
        with col_canal:
            st.markdown(
                f"<span style='background:#10B981;color:white;padding:3px 10px;"
                f"border-radius:12px;font-size:12px;font-weight:600;'>{c['Canal']}</span>",
                unsafe_allow_html=True,
            )
        st.divider()


def _registrar_prospecto_manual(
    razon_social: str, email: str, nombre_contacto: str,
    telefono: str, ciudad: str, sector: str, num_empleados: int, nivel_riesgo: str,
) -> tuple[bool, str]:
    try:
        import uuid
        from datetime import datetime
        from src.database.connection import get_session
        from src.database.models import EmpresaProspecto

        nit_temp = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        with get_session() as session:
            emp = EmpresaProspecto(
                razon_social=razon_social,
                nit=nit_temp,
                sector_economico=sector,
                ciudad=ciudad,
                departamento="Cundinamarca",
                telefono=telefono,
                email_contacto=email,
                nombre_contacto=nombre_contacto,
                nivel_riesgo_arl=nivel_riesgo,
                num_empleados=num_empleados,
                estado_prospecto="NUEVO",
                fuente_origen="Manual",
                fecha_registro=date.today(),
                fecha_ultima_actualizacion=date.today(),
            )
            session.add(emp)
        st.cache_data.clear()
        return True, razon_social
    except Exception as exc:
        return False, str(exc)


def _render_prospectos() -> None:
    resultado = _cargar_prospectos()

    if not resultado["ok"]:
        st.error(f"Error al cargar prospectos: `{resultado['error']}`")
        st.info("Ejecuta `python -m src.database.init_db` para inicializar el esquema.")
        return

    datos = resultado["data"]

    # ── Banner de confirmación persistente ────────────────────────────────────
    if st.session_state.get("_msg_crm"):
        tipo_msg, texto_msg = st.session_state.pop("_msg_crm")
        if tipo_msg == "ok":
            st.success(texto_msg)
        else:
            st.error(texto_msg)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    estados = [p["Estado"] for p in datos]
    c1, c2, c3, c4 = st.columns(4)
    with c1: tarjeta_kpi("Total en CRM", str(len(datos)), icono="🏢", color="#1B3A6B")
    with c2: tarjeta_kpi("Nuevos", str(estados.count("NUEVO")), icono="🔵", color="#1D4ED8")
    with c3: tarjeta_kpi("Con email", str(sum(1 for p in datos if p["_tiene_email"])), icono="📧", color="#7C3AED")
    with c4: tarjeta_kpi("Cierres", str(estados.count("CERRADO_GANADO")), icono="✅", color="#10B981")

    # ── Envío de correo de prueba ─────────────────────────────────────────────
    with st.expander("🧪 Enviar correo de prueba a mi correo"):
        st.caption("Elige una empresa real del CRM, selecciona la plantilla y recibe el correo en tu propio correo para revisar cómo queda.")
        with st.form("form_correo_prueba"):
            nombres_prueba = [p["Empresa"] for p in datos if p["_tiene_email"]]
            empresa_prueba = st.selectbox(
                "Empresa (datos reales del CRM)",
                options=["— Selecciona —"] + nombres_prueba,
            )
            col_p1, col_p2 = st.columns(2)
            email_prueba = col_p1.text_input(
                "Enviar a este correo",
                value="taniagisel2026@gmail.com",
                placeholder="tucorreo@gmail.com",
            )
            plantilla_prueba = col_p2.selectbox(
                "Plantilla",
                options=[
                    ("PRIMER_CONTACTO",         "Día 1 — Primer contacto"),
                    ("RECORDATORIO_VENCIMIENTO", "Día 4 — Recordatorio"),
                    ("ULTIMO_CONTACTO",          "Día 8 — Último contacto"),
                ],
                format_func=lambda x: x[1],
            )
            enviar_prueba = st.form_submit_button("Enviar correo de prueba", type="primary")

        if enviar_prueba:
            if empresa_prueba == "— Selecciona —" or not email_prueba:
                st.warning("Selecciona una empresa e ingresa un correo destino.")
            else:
                id_emp_prueba = next(p["ID"] for p in datos if p["Empresa"] == empresa_prueba)
                tipo_sel = plantilla_prueba[0]
                with st.spinner(f"Enviando a {email_prueba}..."):
                    try:
                        from src.database.connection import get_session
                        from src.database.models import EmpresaProspecto as _ORM
                        from src.domain.resolution_0312 import ESPECIFICACIONES, clasificar_nivel_estandares
                        from src.modules.email.gmail_client import GmailClient
                        from src.modules.email.templates import EmailTemplateEngine, EmailContext
                        from src.config import get_config

                        with get_session() as _s:
                            _e = _s.get(_ORM, id_emp_prueba)
                            nivel = clasificar_nivel_estandares(_e.num_empleados, _e.nivel_riesgo_arl)
                            spec  = ESPECIFICACIONES[nivel]
                            cfg   = get_config()
                            ctx_prueba = EmailContext(
                                razon_social=_e.razon_social,
                                nombre_contacto=_e.nombre_contacto or "",
                                ciudad=_e.ciudad,
                                departamento=_e.departamento,
                                num_estandares=spec.num_estandares,
                                nivel_riesgo=_e.nivel_riesgo_arl,
                                articulo_resolucion=spec.articulo_resolucion,
                                empresa_remitente=cfg.empresa_nombre,
                                email_remitente=cfg.empresa_email,
                                opt_out_url=f"mailto:{cfg.empresa_email}?subject=Exclusión Base de Datos - {_e.razon_social}",
                                sector_economico=_e.sector_economico or "",
                                num_empleados=_e.num_empleados,
                                nombre_asesora=cfg.asesora_nombre,
                            )

                        engine = EmailTemplateEngine()
                        asunto, html = engine.renderizar(tipo_sel, ctx_prueba)
                        gmail = GmailClient.from_config()
                        gmail.send(
                            to=email_prueba,
                            subject=f"[PRUEBA] {asunto}",
                            html_body=html,
                        )
                        st.success(f"Correo de prueba enviado a **{email_prueba}** con datos de **{empresa_prueba}**.")
                    except Exception as exc:
                        st.error(f"Error al enviar: {exc}")

    # ── Agregar prospecto manual ───────────────────────────────────────────────
    with st.expander("➕ Agregar prospecto manualmente"):
        with st.form("form_prospecto_manual"):
            col1, col2 = st.columns(2)
            razon_social = col1.text_input("Empresa *", placeholder="Ej: Mi Empresa SAS")
            email        = col2.text_input("Correo electrónico *", placeholder="contacto@empresa.com")
            col3, col4  = st.columns(2)
            nombre_ctc   = col3.text_input("Nombre contacto", placeholder="Ej: María García")
            telefono     = col4.text_input("Teléfono", placeholder="3001234567")
            col5, col6, col7, col8 = st.columns(4)
            ciudad       = col5.text_input("Ciudad", value="Bogotá D.C.")
            sector       = col6.text_input("Sector", placeholder="Construcción")
            num_emp      = col7.number_input("N° empleados", min_value=1, value=10)
            nivel_riesgo = col8.selectbox("Riesgo ARL", ["I", "II", "III", "IV", "V"])
            guardar      = st.form_submit_button("Guardar prospecto", type="primary")

        if guardar:
            if not razon_social or not email:
                st.warning("⚠️ Empresa y correo electrónico son obligatorios.")
            else:
                ok, msg = _registrar_prospecto_manual(
                    razon_social, email, nombre_ctc, telefono,
                    ciudad, sector, int(num_emp), nivel_riesgo,
                )
                if ok:
                    st.session_state["_msg_crm"] = ("ok", f"✅ {msg} creado correctamente en el CRM.")
                    st.rerun()
                else:
                    st.error(f"❌ Error al crear el prospecto: {msg}")

    # ── Eliminar prospecto ────────────────────────────────────────────────────
    with st.expander("🗑️ Eliminar prospecto"):
        if datos:
            nombres_para_borrar = [f"{p['Empresa']} (ID {p['ID']})" for p in datos]
            sel_borrar = st.selectbox("Selecciona el prospecto a eliminar", nombres_para_borrar, key="sel_borrar")
            nombre_a_borrar = sel_borrar.split(" (ID")[0]
            st.warning(f"⚠️ Esto eliminará **{nombre_a_borrar}** y todo su historial. Esta acción no se puede deshacer.")
            if st.button(f"Sí, eliminar {nombre_a_borrar}", type="secondary", key="btn_borrar"):
                id_borrar = int(sel_borrar.split("ID ")[-1].rstrip(")"))
                from ...database.connection import get_session
                from ...database.models import EmpresaProspecto as _EmpModel, HistorialInteracciones as _HistModel
                with get_session() as _s:
                    _s.query(_HistModel).filter(_HistModel.id_empresa == id_borrar).delete()
                    _s.query(_EmpModel).filter(_EmpModel.id_empresa == id_borrar).delete()
                    _s.commit()
                st.session_state["_msg_crm"] = ("ok", f"🗑️ {nombre_a_borrar} eliminado correctamente.")
                st.rerun()
        else:
            st.info("No hay prospectos para eliminar.")

    if not datos:
        st.info("📭 No hay prospectos registrados aún. Usa el **Motor de Prospección** o agrega uno manualmente arriba.")
        return

    # ── Ficha Centralizada ────────────────────────────────────────────────────
    st.divider()
    separador_seccion("Ficha Centralizada del Cliente")
    _nombres_emp = [p["Empresa"] for p in datos]
    _sel_empresa = st.selectbox(
        "Selecciona una empresa para ver su ficha completa",
        options=["— Ninguna seleccionada —"] + _nombres_emp,
        key="selectbox_ficha_cliente",
    )
    if _sel_empresa != "— Ninguna seleccionada —":
        _id_ficha = next(p["ID"] for p in datos if p["Empresa"] == _sel_empresa)
        _render_ficha_cliente(_id_ficha)

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

    # Mapeo estado → plantilla de correo
    _TIPO_POR_ESTADO = {
        "NUEVO":               "PRIMER_CONTACTO",
        "EN_SEGUIMIENTO":      "SEGUIMIENTO_COTIZACION",
        "COTIZACION_ENVIADA":  "RECORDATORIO_VENCIMIENTO",
        "NEGOCIACION":         "SEGUIMIENTO_COTIZACION",
    }
    _ESTADOS_OPCIONES = ["NUEVO", "EN_SEGUIMIENTO", "COTIZACION_ENVIADA", "NEGOCIACION", "CERRADO_GANADO", "CERRADO_PERDIDO"]

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
            estado_actual = p["Estado"]
            idx_actual = _ESTADOS_OPCIONES.index(estado_actual) if estado_actual in _ESTADOS_OPCIONES else 0
            nuevo_estado = st.selectbox(
                "Estado", _ESTADOS_OPCIONES,
                index=idx_actual,
                key=f"estado_{p['ID']}",
                label_visibility="collapsed",
            )
            if nuevo_estado != estado_actual:
                if st.button("Guardar", key=f"save_estado_{p['ID']}", use_container_width=True):
                    from src.database.connection import get_session
                    from src.database.models import EmpresaProspecto as _EmpMod
                    with get_session() as _s:
                        _e = _s.get(_EmpMod, p["ID"])
                        if _e:
                            _e.estado_prospecto = nuevo_estado
                            _e.fecha_ultima_actualizacion = date.today()
                            _s.commit()
                    st.session_state["_msg_crm"] = ("ok", f"✅ Estado de {p['Empresa']} actualizado a {nuevo_estado}.")
                    st.rerun()

        with col_btn:
            tipo_correo = _TIPO_POR_ESTADO.get(p["Estado"], "PRIMER_CONTACTO")
            _etiquetas = {
                "PRIMER_CONTACTO":        "📨 Día 1 — Primer contacto",
                "SEGUIMIENTO_COTIZACION": "📨 Día 4 — Seguimiento",
                "RECORDATORIO_VENCIMIENTO": "📨 Día 8 — Recordatorio",
            }
            etiqueta_btn = _etiquetas.get(tipo_correo, "📨 Enviar correo")
            if p["_tiene_email"]:
                if st.button(etiqueta_btn, key=f"email_{p['ID']}", use_container_width=True):
                    with st.spinner(f"Enviando a {p['Email']}..."):
                        ok, msg = _enviar_correo(p["ID"], tipo=tipo_correo)
                    if ok:
                        st.success(msg)
                        st.cache_data.clear()
                    else:
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

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.markdown(
            "<small style='color:#6B7280;'>Envía el correo de presentación a todas las empresas que aún no lo han recibido e inicia su cadencia Día 4 / Día 8.</small>",
            unsafe_allow_html=True,
        )
        if st.button("🚀 Enviar Día 1 a todos los pendientes", type="primary", use_container_width=True):
            _enviar_dia1_masivo()

    with col_m2:
        st.markdown(
            "<small style='color:#6B7280;'>Ejecutar una vez al día — envía Día 4 y Día 8 a quien corresponda según la cadencia.</small>",
            unsafe_allow_html=True,
        )
        if st.button("⚙️ Ejecutar cadencia (Día 4 y Día 8)", use_container_width=True):
            _ejecutar_cadencia()

    with col_m3:
        if st.button("📤 Exportar tabla a CSV", use_container_width=True):
            cols_visibles = ["Empresa", "Ciudad", "Sector", "Empleados", "Email", "Estado", "Fuente", "Registro"]
            df = pd.DataFrame([{k: p[k] for k in cols_visibles} for p in filtrados])
            st.download_button(
                "⬇️ Descargar CSV",
                df.to_csv(index=False).encode("utf-8"),
                "prospectos_crm.csv",
                "text/csv",
            )


def _enviar_dia1_masivo() -> None:
    """Envía el correo Día 1 a todas las empresas pendientes con barra de progreso."""
    from src.database.connection import get_session
    from src.modules.email.rate_limiter import RateLimiter
    from src.modules.email.email_service import EmailService
    from src.modules.outreach.sequence_orchestrator import SequenceOrchestrator

    # Obtener lista de pendientes antes de empezar
    orq = SequenceOrchestrator(
        email_svc=EmailService(
            rate_limiter=RateLimiter(delay_min_s=3, delay_max_s=8)
        )
    )
    with get_session() as s:
        ids_pendientes = SequenceOrchestrator._ids_sin_dia_1(s)

    total = len(ids_pendientes)
    if total == 0:
        st.info("Todas las empresas ya recibieron el primer correo.")
        return

    st.info(f"Enviando a **{total}** empresas — esto puede tardar unos minutos...")
    barra    = st.progress(0, text="Iniciando...")
    contador = st.empty()
    enviados, fallidos_lst, rate_stop = 0, [], False

    for i, id_emp in enumerate(ids_pendientes):
        if rate_stop:
            break
        try:
            empresa = SequenceOrchestrator._cargar_dominio(id_emp)
            barra.progress((i + 1) / total, text=f"Enviando {i+1}/{total}: {empresa.razon_social[:40]}...")
            r = orq.iniciar_secuencia(empresa, creado_por="Panel Web")
            if r.ok:
                enviados += 1
                contador.markdown(f"✅ {enviados} enviados de {total}")
            else:
                fallidos_lst.append(r)
                if "Límite" in r.mensaje or "rate" in r.mensaje.lower():
                    rate_stop = True
        except Exception as exc:
            fallidos_lst.append(type("R", (), {"razon_social": f"ID {id_emp}", "mensaje": str(exc)})())

    barra.empty()
    contador.empty()

    if enviados:
        st.success(f"✅ Primer correo enviado a **{enviados}** empresa(s).")
    if rate_stop:
        st.warning(f"⏸ Límite diario alcanzado. Quedan {total - enviados} empresas — se enviarán mañana.")
    if fallidos_lst and not rate_stop:
        with st.expander(f"⚠️ {len(fallidos_lst)} error(es)"):
            for r in fallidos_lst:
                st.markdown(f"- **{r.razon_social}**: {r.mensaje}")

    st.cache_data.clear()


def _ejecutar_cadencia() -> None:
    """Procesa todos los prospectos activos y avanza la cadencia (Día 4 / Día 8)."""
    from src.modules.outreach.sequence_orchestrator import SequenceOrchestrator
    with st.spinner("Procesando cadencia automática..."):
        resultados = SequenceOrchestrator().procesar_pendientes(creado_por="Panel Web")

    if not resultados:
        st.info("No hay prospectos pendientes de cadencia en este momento.")
        return

    enviados = [r for r in resultados if r.ok and r.accion in ("DIA_4", "DIA_8")]
    en_espera = [r for r in resultados if r.accion == "EN_ESPERA"]
    errores   = [r for r in resultados if not r.ok]

    if enviados:
        st.success(f"✅ {len(enviados)} mensaje(s) enviados en la cadencia.")
        for r in enviados:
            st.markdown(f"- **{r.razon_social}** — {r.accion}: {r.mensaje}")
    if en_espera:
        st.info(f"⏳ {len(en_espera)} prospecto(s) en espera (aún no corresponde el siguiente paso).")
    if errores:
        st.warning(f"⚠️ {len(errores)} error(es):")
        for r in errores:
            st.markdown(f"- {r.razon_social}: {r.mensaje}")


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
    prospectos_activos = _cargar_prospectos().get("data", [])
    nombres_optout = ["— Selecciona una empresa —"] + [p["Empresa"] for p in prospectos_activos]

    with st.form("form_optout_manual"):
        empresa_sel_optout = st.selectbox("Empresa", options=nombres_optout)
        motivo = st.text_input("Motivo", value="Solicitud del titular de los datos")
        enviado = st.form_submit_button("🚫 Registrar Opt-Out", type="primary")

    if enviado:
        if empresa_sel_optout == "— Selecciona una empresa —":
            st.warning("Selecciona una empresa primero.")
        else:
            id_emp = next(p["ID"] for p in prospectos_activos if p["Empresa"] == empresa_sel_optout)
            ok, msg = _registrar_optout(id_emp, motivo)
            if ok:
                st.success(f"✅ {msg}")
                st.rerun()
            else:
                st.error(f"Error: {msg}")
