import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from ..components.metrics import separador_seccion, tarjeta_kpi

_ROOT = Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_CIUDADES = [
    # Principales
    "Bogotá D.C.", "Medellín", "Cali", "Barranquilla", "Bucaramanga",
    "Cartagena", "Soacha", "Tunja", "Ibagué", "Santa Marta",
    # Cundinamarca / Clúster Bogotá
    "Chía", "Cota", "Facatativá", "Fusagasugá", "Zipaquirá",
    "Villeta", "Girardot", "Mosquera", "La Vega", "Cajicá",
    "Sopó", "La Calera", "Guaduas", "Flandes", "Tocancipá",
    "Madrid", "Sibaté",
    # Otras ciudades de cobertura
    "Cúcuta", "Pereira", "Manizales", "Valledupar", "Floridablanca",
    "Barrancabermeja", "Lebrija", "Melgar",
]

_REGIONES: dict[str, list[str]] = {
    "Bogotá + Cundinamarca": [
        "Bogotá D.C.", "Soacha", "Chía", "Cota", "Facatativá", "Fusagasugá",
        "Zipaquirá", "Villeta", "Girardot", "Mosquera", "La Vega", "Cajicá",
        "Sopó", "La Calera", "Guaduas", "Flandes", "Tocancipá", "Madrid", "Sibaté",
    ],
    "Antioquia": ["Medellín"],
    "Valle del Cauca": ["Cali"],
    "Costa Caribe": ["Barranquilla", "Cartagena", "Valledupar", "Santa Marta"],
    "Santander": ["Bucaramanga", "Floridablanca", "Lebrija", "Barrancabermeja"],
    "Eje Cafetero": ["Pereira", "Manizales"],
    "Boyacá / Tolima": ["Tunja", "Ibagué", "Melgar", "Flandes"],
    "Norte de Santander": ["Cúcuta"],
    "Todo el país": _CIUDADES,
}

_SECTORES = [
    "Construcción", "Manufactura / Industria", "Transporte y Logística",
    "Comercio y Retail", "Servicios Empresariales", "Salud y Clínicas",
    "Minería y Energía", "Tecnología y Software", "Alimentos y Bebidas",
    "Seguridad Privada", "Hotelería y Turismo", "Petróleo y Gas",
    "Ingeniería y Consultoría", "Farmacéutico y Químico", "Telecomunicaciones",
    "Entretenimiento y Eventos",
]

_CLAVE_RESULTADO = "scraper_ultimo_resultado"


def render() -> None:
    st.title("🕵️ Motor de Prospección")
    st.caption("Extracción automatizada de prospectos · Google Maps · LinkedIn · WebScraper")

    col_config, col_resultado = st.columns([1, 1], gap="large")

    # ── Panel de configuración ────────────────────────────────────────────────
    with col_config:
        separador_seccion("Parámetros de extracción")

        region = st.selectbox("🗺️ Región", list(_REGIONES.keys()), key="sc_region")
        ciudades_region = _REGIONES[region]
        ciudad = st.selectbox("📍 Ciudad objetivo", ciudades_region, key="sc_ciudad")
        sector = st.selectbox("🏭 Sector económico", _SECTORES, key="sc_sector")
        max_empresas = st.slider(
            "📊 Máximo de empresas por fuente",
            min_value=5, max_value=100, value=30, step=5,
        )

        st.markdown("**Fuentes activas:**")
        usar_gmaps = st.checkbox("🗺️ Google Maps (búsqueda + fichas)",  value=True)
        usar_li    = False
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

        if not usar_gmaps:
            st.warning("Activa Google Maps para iniciar la extracción.")

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

        iniciar = st.button(
            "🚀 Iniciar Extracción",
            type="primary",
            use_container_width=True,
            disabled=not usar_gmaps,
        )

    # ── Resultado / Log ───────────────────────────────────────────────────────
    with col_resultado:
        separador_seccion("Resultado de la sesión")

        if iniciar:
            _ejecutar_pipeline(ciudad, sector, max_empresas, disparar_emails, usar_gmaps, usar_li, usar_web)

        # Mostrar último resultado almacenado en session_state
        if _CLAVE_RESULTADO in st.session_state:
            _mostrar_resultado(st.session_state[_CLAVE_RESULTADO])
        elif not iniciar:
            _mostrar_historial()

    # ── Extracción en lote (ancho completo) ──────────────────────────────────
    st.divider()
    separador_seccion("Extracción en lote")
    st.caption("Extrae todos los sectores de una ciudad de forma automática.")

    col_lote1, col_lote2, col_lote3 = st.columns([2, 3, 1])
    with col_lote1:
        ciudad_lote = st.selectbox("📍 Ciudad", ciudades_region, key="sc_ciudad_lote")
    with col_lote2:
        sectores_lote = st.multiselect(
            "Sectores a extraer",
            _SECTORES,
            default=_SECTORES,
            key="sc_sectores_lote",
        )
    with col_lote3:
        max_lote = st.slider("Máximo por sector", 5, 100, 30, 5, key="sc_max_lote")

    iniciar_lote = st.button(
        "🚀 Iniciar extracción en lote",
        type="secondary",
        use_container_width=True,
        disabled=not sectores_lote,
    )

    if iniciar_lote and sectores_lote:
        _ejecutar_lote(ciudad_lote, sectores_lote, max_lote)

    if "_lote_resultado" in st.session_state:
        r = st.session_state["_lote_resultado"]
        correos_txt = f" · **{r['correos']} correos encontrados**" if r.get("correos") else ""
        st.success(
            f"**Última extracción en lote** — {r['ciudad']} · {r['sectores']} sectores · "
            f"**{r['nuevas']} empresas nuevas**{correos_txt} · {r['fecha']}"
        )


def _ejecutar_pipeline(ciudad: str, sector: str, max_por_fuente: int, disparar_emails: bool,
                       usar_gmaps: bool = True, usar_li: bool = True, usar_web: bool = True) -> None:
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
                usar_gmaps=usar_gmaps,
                usar_linkedin=usar_li,
                usar_webscraper=usar_web,
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
        # Guardar última sesión en archivo para persistir entre recargas
        import json as _json
        from datetime import date as _date
        _log_path = Path(__file__).parent.parent.parent.parent / "data" / "ultima_extraccion.json"
        _log_path.parent.mkdir(parents=True, exist_ok=True)
        _log_path.write_text(_json.dumps({
            "fecha":    str(_date.today()),
            "ciudad":   resultado.ciudad,
            "sector":   resultado.sector,
            "nuevas":   resultado.empresas_nuevas,
        }), encoding="utf-8")
        # Invalidar caché del dashboard y campañas
        st.cache_data.clear()
        st.rerun()

    except Exception as exc:
        import traceback
        tipo = type(exc).__name__
        detalle = traceback.format_exc()
        print(f"[PIPELINE ERROR] {tipo}: {exc}\n{detalle}")
        if "RateLimitExceeded" in tipo:
            st.session_state[_CLAVE_RESULTADO] = {"_error": f"⏸ Límite diario de correos: {exc}"}
        elif "GmailAuth" in tipo:
            st.session_state[_CLAVE_RESULTADO] = {"_error": "🔑 Gmail no autenticado. Configura `credentials/gmail_credentials.json`."}
        else:
            st.session_state[_CLAVE_RESULTADO] = {"_error": f"❌ Error en el pipeline:\n\n`{tipo}: {exc}`\n\n```\n{detalle[-800:]}\n```"}
        st.rerun()


def _mostrar_resultado(r: dict) -> None:
    """Muestra métricas y tabla del último resultado guardado en session_state."""
    # Mostrar error persistente si el pipeline falló
    if "_error" in r:
        st.error(r["_error"])
        if st.button("🗑 Limpiar error", use_container_width=True):
            st.session_state.pop(_CLAVE_RESULTADO, None)
            st.rerun()
        return

    st.success(f"✅ Extracción completada en **{r['duracion']}s** — {r['ciudad']} / {r['sector']}")

    c1, c2, c3 = st.columns(3)
    with c1: tarjeta_kpi("Encontradas",   str(r["encontradas"]), icono="🏢", color="#1B3A6B")
    with c2: tarjeta_kpi("Nuevas en CRM", str(r["nuevas"]),      icono="✅", color="#10B981")
    with c3: tarjeta_kpi("Ya existían",   str(r["existentes"]),  icono="🔁", color="#6B7280")

    if r["emails"] > 0:
        st.info(f"📨 **{r['emails']}** correos enviados · {r['sin_contacto']} sin email · {r['fallidos']} fallidos")
    if r["rate_limit"]:
        st.warning("⏸ Envío de correos detenido: límite diario alcanzado.")

    if r["errores"]:
        with st.expander(f"⚠️ {len(r['errores'])} advertencias"):
            for e in r["errores"]:
                st.markdown(f"- `{e}`")

    # Mostrar empresas recién guardadas hoy para este sector/ciudad
    try:
        from datetime import date as _date
        from src.database.connection import get_session
        from src.database.models import EmpresaProspecto

        with get_session() as session:
            recientes = (
                session.query(EmpresaProspecto)
                .filter(
                    EmpresaProspecto.fecha_registro == _date.today(),
                    EmpresaProspecto.ciudad == r["ciudad"],
                    EmpresaProspecto.sector_economico == r["sector"],
                )
                .order_by(EmpresaProspecto.id_empresa.desc())
                .all()
            )

        if recientes:
            from collections import defaultdict
            grupos: dict = defaultdict(list)
            for e in recientes:
                grupos[e.razon_social].append(e)

            filas = []
            for razon, empresas in grupos.items():
                emails = [e.email_contacto for e in empresas if e.email_contacto]
                primer = empresas[0]
                filas.append({
                    "Empresa":  razon,
                    "Correos":  len(emails),
                    "Email":    emails[0] if emails else "—",
                    "WhatsApp": primer.whatsapp or "—",
                    "Teléfono": primer.telefono or "—",
                })

            total_correos = sum(f["Correos"] for f in filas)
            st.markdown(
                f"**Empresas guardadas hoy ({len(grupos)}) — "
                f"{total_correos} correo(s) encontrado(s):**"
            )
            st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)
        elif r["encontradas"] == 0:
            st.warning("Google Maps no encontró empresas. Intenta con otro sector o ciudad.")
        else:
            st.info("Las empresas encontradas ya existían en el CRM o no tenían email.")
    except Exception:
        pass

    if st.button("🗑 Limpiar resultado", use_container_width=True):
        st.session_state.pop(_CLAVE_RESULTADO, None)
        st.rerun()


@st.cache_data(ttl=60)
def _cargar_historial() -> dict:
    """Carga historial de extracciones agrupado por fecha, ciudad y sector."""
    try:
        from sqlalchemy import func
        from src.database.connection import get_session
        from src.database.models import EmpresaProspecto

        with get_session() as session:
            sesiones = (
                session.query(
                    EmpresaProspecto.fecha_registro,
                    EmpresaProspecto.ciudad,
                    EmpresaProspecto.sector_economico,
                    func.count(EmpresaProspecto.id_empresa),
                )
                .group_by(
                    EmpresaProspecto.fecha_registro,
                    EmpresaProspecto.ciudad,
                    EmpresaProspecto.sector_economico,
                )
                .order_by(EmpresaProspecto.fecha_registro.desc())
                .all()
            )
            total = session.query(func.count(EmpresaProspecto.id_empresa)).scalar() or 0

        return {
            "ok": True,
            "total": total,
            "sesiones": [
                {
                    "Fecha": str(fecha),
                    "Ciudad": ciudad or "—",
                    "Sector": sector or "—",
                    "Extraídas": n,
                }
                for fecha, ciudad, sector, n in sesiones
            ],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "total": 0, "sesiones": []}


def _mostrar_historial() -> None:
    """Muestra historial de extracciones por fecha, ciudad y sector."""
    hist = _cargar_historial()

    if not hist["ok"]:
        st.info("⬅️ Configura los parámetros y presiona **Iniciar Extracción**.")
        return

    if not hist["sesiones"]:
        st.info(
            "⬅️ Configura los parámetros y presiona **Iniciar Extracción**.\n\n"
            "El historial de extracciones aparecerá aquí."
        )
        return

    # Tarjeta con la última extracción — archivo persistente o respaldo del historial
    import json as _json
    _log_path = Path(__file__).parent.parent.parent.parent / "data" / "ultima_extraccion.json"
    if _log_path.exists():
        try:
            _ult = _json.loads(_log_path.read_text(encoding="utf-8"))
            st.info(
                f"**Última extracción:** {_ult['ciudad']} · {_ult['sector']} · "
                f"**{_ult['nuevas']} empresas nuevas** · {_ult['fecha']}"
            )
        except Exception:
            pass
    else:
        # Respaldo: usar la fila más reciente del historial
        ultima = hist["sesiones"][0]
        ultima_fecha = ultima["Fecha"]
        ultima_ciudad = ultima["Ciudad"]
        total_ultima = sum(s["Extraídas"] for s in hist["sesiones"] if s["Fecha"] == ultima_fecha and s["Ciudad"] == ultima_ciudad)
        st.info(
            f"**Última extracción:** {ultima_ciudad} · "
            f"**{total_ultima} empresas** · {ultima_fecha}"
        )

    separador_seccion(f"Historial de extracciones — {hist['total']} prospectos en total")
    df = pd.DataFrame(hist["sesiones"])
    st.dataframe(df, use_container_width=True, hide_index=True)


def _ejecutar_lote(ciudad: str, sectores: list[str], max_por_sector: int) -> None:
    """Corre el pipeline para cada sector de forma secuencial mostrando progreso."""
    total_nuevas = 0
    with st.status(f"Extrayendo {len(sectores)} sectores en {ciudad}...", expanded=True) as status:
        for i, sector in enumerate(sectores, 1):
            st.write(f"**{i}/{len(sectores)}** — {sector}...")
            try:
                from src.modules.scraper.pipeline import ProspectionPipeline
                resultado = ProspectionPipeline().ejecutar(
                    ciudad=ciudad,
                    sector=sector,
                    max_por_fuente=max_por_sector,
                    disparar_emails=False,
                    usar_gmaps=True,
                    usar_linkedin=False,
                    usar_webscraper=True,
                )
                total_nuevas += resultado.empresas_nuevas
                st.write(f"  ✅ {resultado.empresas_nuevas} nuevas · {resultado.empresas_existentes} ya existían")
            except Exception as exc:
                st.write(f"  ⚠️ Error: {exc}")

        import json as _json
        from datetime import date as _date
        from src.database.connection import get_session as _get_session
        from src.database.models import EmpresaProspecto as _EP
        from sqlalchemy import func as _func

        with _get_session() as _s:
            total_correos = _s.query(_func.count(_EP.id_empresa)).filter(
                _EP.fecha_registro == _date.today(),
                _EP.ciudad == ciudad,
                _EP.email_contacto.isnot(None),
                _EP.email_contacto != "",
            ).scalar() or 0

        _log_path = Path(__file__).parent.parent.parent.parent / "data" / "ultima_extraccion.json"
        _log_path.parent.mkdir(parents=True, exist_ok=True)
        _log_path.write_text(_json.dumps({
            "fecha":           str(_date.today()),
            "ciudad":          ciudad,
            "sector":          f"{len(sectores)} sectores",
            "nuevas":   total_nuevas,
            "correos":  total_correos,
        }), encoding="utf-8")

        st.cache_data.clear()
        status.update(
            label=f"Lote completado — {total_nuevas} empresas nuevas · {total_correos} correos encontrados",
            state="complete",
        )
        st.session_state["_lote_resultado"] = {
            "ciudad":   ciudad,
            "sectores": len(sectores),
            "nuevas":   total_nuevas,
            "correos":  total_correos,
            "fecha":    str(_date.today()),
        }
