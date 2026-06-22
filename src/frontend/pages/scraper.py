import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from ..components.metrics import separador_seccion, tarjeta_kpi

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
]

_CLAVE_RESULTADO = "scraper_ultimo_resultado"


def render() -> None:
    st.title("🕵️ Motor de Prospección")
    st.caption("Extracción automatizada de prospectos · Google Maps · LinkedIn · WebScraper")

    col_config, col_resultado = st.columns([1, 1], gap="large")

    # ── Panel de configuración ────────────────────────────────────────────────
    with col_config:
        separador_seccion("Parámetros de extracción")

        ciudad = st.selectbox("📍 Ciudad objetivo", _CIUDADES, key="sc_ciudad")
        sector = st.selectbox("🏭 Sector económico", _SECTORES, key="sc_sector")
        max_empresas = st.slider(
            "📊 Máximo de empresas por fuente",
            min_value=5, max_value=100, value=30, step=5,
        )

        st.markdown("**Fuentes activas:**")
        usar_gmaps = st.checkbox("📒 Páginas Amarillas Colombia",      value=True)
        usar_li    = st.checkbox("🔗 LinkedIn (búsqueda pública)",    value=True)
        usar_web   = st.checkbox("🌐 WebScraper (extracción emails)", value=True)

        st.divider()
        disparar_emails = st.checkbox(
            "📨 Disparar correos automáticos a nuevos prospectos",
            value=False,
            help=(
                "Invoca EmailService tras la extracción, respetando el rate limit "
                "diario y el control de Habeas Data (Ley 1581)."
            ),
        )

        if not (usar_gmaps or usar_li or usar_web):
            st.warning("Activa al menos una fuente de datos.")

        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
            _pw_ok = True
        except ImportError:
            _pw_ok = False

        if _pw_ok:
            st.success("✅ Playwright instalado — extracción real activa.")
        else:
            st.info(
                "ℹ️ Sin Playwright instalado el extractor opera en **modo mock** "
                "con datos representativos de empresas colombianas.\n\n"
                "Para extracción real: `playwright install chromium`"
            )

        # ── Estado sesión LinkedIn ─────────────────────────────────────────
        try:
            from src.modules.scraper.linkedin_auto import LinkedInAutoScraper
            _li_sesion = LinkedInAutoScraper.sesion_existe()
        except Exception:
            _li_sesion = False

        if _li_sesion:
            st.success("🔗 LinkedIn: sesión activa — extracción directa habilitada.")
        else:
            st.warning(
                "🔗 LinkedIn: sin sesión configurada.\n\n"
                "Para habilitarlo, corre **una sola vez** en cmd:\n\n"
                "```\npython scrape_linkedin_auto.py --solo-login\n```"
            )

        iniciar = st.button(
            "🚀 Iniciar Extracción",
            type="primary",
            use_container_width=True,
            disabled=not (usar_gmaps or usar_li or usar_web),
        )

    # ── Resultado / Log ───────────────────────────────────────────────────────
    with col_resultado:
        separador_seccion("Resultado de la sesión")

        if iniciar:
            _ejecutar_pipeline(ciudad, sector, max_empresas, disparar_emails)

        # Mostrar último resultado almacenado en session_state
        if _CLAVE_RESULTADO in st.session_state:
            _mostrar_resultado(st.session_state[_CLAVE_RESULTADO])
        elif not iniciar:
            _mostrar_historial()


def _ejecutar_pipeline(ciudad: str, sector: str, max_por_fuente: int, disparar_emails: bool) -> None:
    """
    Llama a ProspectionPipeline.ejecutar() con st.spinner().
    Almacena el resultado en session_state para persistencia entre reruns.
    """
    # Limpiar resultado previo
    st.session_state.pop(_CLAVE_RESULTADO, None)

    try:
        from src.modules.scraper import ProspectionPipeline
        from src.modules.scraper.google_maps import GoogleMapsScraper
        from src.modules.scraper.linkedin import LinkedInScraper
        from src.modules.scraper.engine import ScraperEngineService

        pipeline = ProspectionPipeline()

        msg_spinner = (
            f"Extrayendo prospectos en **{ciudad}** / **{sector}**... "
            "Esto puede tardar unos minutos en modo real."
        )
        with st.spinner(msg_spinner):
            resultado = pipeline.ejecutar(
                ciudad=ciudad,
                sector=sector,
                max_por_fuente=max_por_fuente,
                disparar_emails=disparar_emails,
            )

        # Serializar para session_state (solo primitivos)
        st.session_state[_CLAVE_RESULTADO] = {
            "ciudad":        resultado.ciudad,
            "sector":        resultado.sector,
            "encontradas":   resultado.empresas_encontradas,
            "nuevas":        resultado.empresas_nuevas,
            "existentes":    resultado.empresas_existentes,
            "emails":        resultado.emails_enviados,
            "sin_contacto":  resultado.emails_sin_contacto,
            "fallidos":      resultado.emails_fallidos,
            "rate_limit":    resultado.rate_limit_alcanzado,
            "duracion":      round(resultado.duracion_s, 1),
            "errores":       resultado.errores[:10],
        }
        # Invalidar caché del dashboard y campañas
        st.cache_data.clear()
        st.rerun()

    except Exception as exc:
        tipo = type(exc).__name__
        if "RateLimitExceeded" in tipo:
            st.warning(f"⏸ Límite diario de correos alcanzado durante el pipeline: {exc}")
        elif "GmailAuth" in tipo:
            st.warning(
                "🔑 Gmail no autenticado. El scraping continuó pero los correos "
                "no se enviaron. Configura `credentials/gmail_credentials.json`."
            )
        else:
            st.error(f"❌ Error en el pipeline: `{tipo}: {exc}`")


def _mostrar_resultado(r: dict) -> None:
    """Muestra métricas y tabla del último resultado guardado en session_state."""
    st.success(f"✅ Extracción completada en **{r['duracion']}s** — {r['ciudad']} / {r['sector']}")

    c1, c2, c3 = st.columns(3)
    with c1: tarjeta_kpi("Empresas encontradas", str(r["encontradas"]), icono="🏢", color="#1B3A6B")
    with c2: tarjeta_kpi("Nuevas en CRM",        str(r["nuevas"]),      icono="✅", color="#10B981")
    with c3: tarjeta_kpi("Ya existían",           str(r["existentes"]),  icono="🔁", color="#6B7280")

    if r["emails"] > 0:
        st.info(f"📨 **{r['emails']}** correos enviados · {r['sin_contacto']} sin email · {r['fallidos']} fallidos")
    if r["rate_limit"]:
        st.warning("⏸ Envío de correos detenido: límite diario alcanzado.")

    if r["errores"]:
        with st.expander(f"⚠️ {len(r['errores'])} advertencias durante la ejecución"):
            for e in r["errores"]:
                st.markdown(f"- `{e}`")

    if st.button("🗑 Limpiar resultado", use_container_width=True):
        st.session_state.pop(_CLAVE_RESULTADO, None)
        st.rerun()


@st.cache_data(ttl=60)
def _cargar_historial() -> dict:
    """Carga historial de sesiones de scraping desde HISTORIAL_INTERACCIONES."""
    try:
        from sqlalchemy import func
        from src.database.connection import get_session
        from src.database.models import EmpresaProspecto, HistorialInteracciones

        with get_session() as session:
            # Prospectos por fuente de origen como proxy del historial de scraping
            por_fuente = (
                session.query(
                    EmpresaProspecto.fuente_origen,
                    func.count(EmpresaProspecto.id_empresa),
                )
                .group_by(EmpresaProspecto.fuente_origen)
                .all()
            )
            por_ciudad = (
                session.query(
                    EmpresaProspecto.ciudad,
                    EmpresaProspecto.fuente_origen,
                    func.count(EmpresaProspecto.id_empresa),
                )
                .group_by(EmpresaProspecto.ciudad, EmpresaProspecto.fuente_origen)
                .order_by(func.count(EmpresaProspecto.id_empresa).desc())
                .limit(12)
                .all()
            )
        return {
            "ok": True,
            "fuentes": [{"Fuente": f or "Desconocida", "Total": n} for f, n in por_fuente],
            "detalle": [{"Ciudad": c, "Fuente": f or "—", "Prospectos": n} for c, f, n in por_ciudad],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "fuentes": [], "detalle": []}


def _mostrar_historial() -> None:
    """Muestra estadísticas históricas mientras no hay sesión activa."""
    hist = _cargar_historial()

    if not hist["ok"]:
        st.info("⬅️ Configura los parámetros y presiona **Iniciar Extracción**.")
        return

    if not hist["fuentes"]:
        st.info(
            "⬅️ Configura los parámetros y presiona **Iniciar Extracción**.\n\n"
            "Los resultados de extracciones anteriores aparecerán aquí."
        )
        return

    separador_seccion("Historial de prospectos por fuente")
    df_f = pd.DataFrame(hist["fuentes"])
    st.dataframe(df_f, use_container_width=True, hide_index=True)

    if hist["detalle"]:
        separador_seccion("Detalle por ciudad y fuente")
        df_d = pd.DataFrame(hist["detalle"])
        st.dataframe(df_d, use_container_width=True, hide_index=True)
