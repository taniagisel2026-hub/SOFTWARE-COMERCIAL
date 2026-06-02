"""
Módulo 5 — Fábrica Automatizada de Contenido y Multimedia.
Genera 1 artículo SST diario con Claude + 3 imágenes IA + copys por plataforma.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from ..components.metrics import separador_seccion, tarjeta_kpi

_ROOT = Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_KEY_ARTICULO = "contenido_articulo_hoy"
_KEY_IMAGENES = "contenido_imagenes_hoy"

_PLATAFORMA_ICONO = {
    "LINKEDIN":  "💼",
    "FACEBOOK":  "📘",
    "INSTAGRAM": "📸",
}


# ── Helpers de BD ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def _cargar_estadisticas() -> dict:
    try:
        from src.modules.contenido import SocialSchedulerService
        return SocialSchedulerService().resumen_estadisticas()
    except Exception as exc:
        return {"total": 0, "pendientes": 0, "publicados": 0, "errores": 0,
                "tasa_exito": "N/A", "error": str(exc)}


@st.cache_data(ttl=30)
def _cargar_calendario(dias: int = 14) -> list[dict]:
    try:
        from src.database.connection import get_session
        from src.database.models import ContenidoRedes
        from datetime import datetime

        inicio = date.today() - timedelta(days=dias // 2)
        fin    = date.today() + timedelta(days=dias // 2)

        with get_session() as session:
            rows = (
                session.query(ContenidoRedes)
                .filter(
                    ContenidoRedes.fecha_publicacion >= inicio,
                    ContenidoRedes.fecha_publicacion <= fin,
                )
                .order_by(ContenidoRedes.fecha_publicacion.desc())
                .limit(50)
                .all()
            )
            return [
                {
                    "id":        r.id_contenido,
                    "fecha":     str(r.fecha_publicacion),
                    "plataforma": r.plataforma_destino or "TODAS",
                    "tema":      r.tema_sst or "—",
                    "estado":    r.estado_publicacion,
                    "copy":      (r.texto_publicacion or "")[:120],
                }
                for r in rows
            ]
    except Exception:
        return []


def _marcar_publicado(id_contenido: int) -> tuple[bool, str]:
    try:
        from src.modules.contenido import SocialSchedulerService
        SocialSchedulerService().marcar_publicado(id_contenido)
        st.cache_data.clear()
        return True, "Marcado como publicado."
    except Exception as exc:
        return False, str(exc)


def _guardar_en_calendario(articulo, imagenes) -> tuple[bool, str]:
    try:
        from src.modules.contenido import SocialSchedulerService
        svc = SocialSchedulerService()
        id_c = svc.programar(articulo, imagenes)
        st.cache_data.clear()
        return True, f"Guardado en calendario (ID {id_c})."
    except Exception as exc:
        return False, str(exc)


# ── Render principal ──────────────────────────────────────────────────────────

def render() -> None:
    import os

    col_t, col_r = st.columns([6, 1])
    col_t.title("🎨 Fábrica de Contenido")
    if col_r.button("🔄", help="Actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption("Módulo 5 — Generación automática de artículos SST con Claude + imágenes IA")

    # Verificación de API key
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        st.warning(
            "⚠️ **`ANTHROPIC_API_KEY` no configurada.** "
            "Añádela en `.env` para habilitar la generación de contenido."
        )

    tab_gen, tab_cal, tab_stats = st.tabs([
        "✍️ Generar Artículo",
        "📅 Calendario",
        "📊 Estadísticas",
    ])

    with tab_gen:
        _render_generador()

    with tab_cal:
        _render_calendario()

    with tab_stats:
        _render_estadisticas()


# ── Tab 1: Generador ──────────────────────────────────────────────────────────

def _render_generador() -> None:
    import os
    from src.modules.contenido.topics import obtener_tema_del_dia

    tema_hoy = obtener_tema_del_dia()

    # Mostrar tema del día
    st.markdown(
        f"<div style='background:#EEF2F9;border-left:4px solid #1B3A6B;"
        f"border-radius:8px;padding:14px 20px;margin-bottom:16px;'>"
        f"<b style='color:#1B3A6B;'>📌 Tema del día — {date.today().strftime('%d de %B de %Y')}</b><br>"
        f"<span style='font-size:15px;font-weight:600;'>{tema_hoy.titulo_base}</span><br>"
        f"<small style='color:#6B7280;'>Categoría: {tema_hoy.categoria} &nbsp;·&nbsp; "
        f"Ángulo: {tema_hoy.angulo_narrativo}</small>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Selector de tema alternativo
    tema_manual = None
    with st.expander("🔄 Cambiar tema manualmente"):
        from src.modules.contenido.topics import CATALOGO_TEMAS
        opciones = [f"{t.categoria} — {t.titulo_base}" for t in CATALOGO_TEMAS]
        seleccion = st.selectbox("Selecciona un tema", opciones, key="tema_manual")
        tema_manual = CATALOGO_TEMAS[opciones.index(seleccion)]

    # Selección del generador de imágenes
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        gen_tipo = st.selectbox(
            "Motor de imágenes",
            ["Mock (prompts listos para Midjourney/DALL-E Web)",
             "DALL-E 3 (requiere OPENAI_API_KEY)",
             "Stable Diffusion XL (requiere REPLICATE_API_TOKEN)"],
            key="gen_imagenes_tipo",
        )
    with col_opt2:
        plataforma = st.selectbox(
            "Plataforma principal",
            ["TODAS", "LINKEDIN", "FACEBOOK", "INSTAGRAM"],
            key="plataforma_pub",
        )

    col_btn, col_info = st.columns([2, 3])
    with col_info:
        tiene_key = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
        st.markdown(
            f"<small style='color:{'#10B981' if tiene_key else '#EF4444'};'>"
            f"{'✅ Claude API lista' if tiene_key else '❌ ANTHROPIC_API_KEY no configurada'}"
            f"</small>",
            unsafe_allow_html=True,
        )

    with col_btn:
        generar = st.button(
            "⚡ Generar Artículo de Hoy",
            type="primary",
            use_container_width=True,
            disabled=not tiene_key,
        )

    if generar:
        _ejecutar_generacion(
            tema=tema_manual,
            gen_tipo=gen_tipo,
            plataforma=plataforma,
        )

    # Mostrar resultado si existe en session_state
    if _KEY_ARTICULO in st.session_state:
        _mostrar_articulo(
            st.session_state[_KEY_ARTICULO],
            st.session_state.get(_KEY_IMAGENES, []),
            plataforma,
        )


def _ejecutar_generacion(tema, gen_tipo: str, plataforma: str) -> None:
    try:
        from src.modules.contenido import (
            ContentGeneratorService,
            DalleImageGenerator,
            ImageGeneratorService,
            MockImageGenerator,
            ReplicateImageGenerator,
        )
        import os

        with st.spinner("Claude generando artículo SST..."):
            svc = ContentGeneratorService()
            articulo = svc.generar(tema=tema)

        # Seleccionar generador de imágenes
        if "DALL-E" in gen_tipo and os.getenv("OPENAI_API_KEY"):
            img_gen = ImageGeneratorService(DalleImageGenerator())
            gen_label = "DALL-E 3"
        elif "Stable Diffusion" in gen_tipo and os.getenv("REPLICATE_API_TOKEN"):
            img_gen = ImageGeneratorService(ReplicateImageGenerator())
            gen_label = "Stable Diffusion XL"
        else:
            img_gen = ImageGeneratorService(MockImageGenerator())
            gen_label = "Mock"

        with st.spinner(f"Generando 3 imágenes con {gen_label}..."):
            imagenes = img_gen.generar_para_articulo(
                articulo_titulo=articulo.titulo,
                prompts=articulo.prompts_imagenes,
                tema=articulo.tema,
            )

        st.session_state[_KEY_ARTICULO] = articulo
        st.session_state[_KEY_IMAGENES] = imagenes

        # Métricas de generación
        cache_info = "✅ Cache hit" if articulo.cache_hit else "🔄 Sin cache"
        st.success(
            f"✅ Artículo generado · "
            f"{articulo.tokens_entrada} tokens entrada / "
            f"{articulo.tokens_salida} tokens salida · {cache_info}"
        )

    except Exception as exc:
        st.error(f"Error al generar: {exc}")


def _mostrar_articulo(articulo, imagenes: list, plataforma: str) -> None:
    st.divider()

    # Header del artículo
    separador_seccion("Artículo generado")
    st.markdown(f"## {articulo.titulo}")
    st.markdown(
        f"<small style='color:#6B7280;'>"
        f"📅 {articulo.fecha_generacion} &nbsp;·&nbsp; "
        f"🏷️ {articulo.tema.categoria} &nbsp;·&nbsp; "
        f"🤖 {articulo.modelo_usado}"
        f"</small>",
        unsafe_allow_html=True,
    )

    # Cuerpo del artículo
    with st.expander("📄 Ver artículo completo", expanded=True):
        st.markdown(articulo.cuerpo)

    st.divider()

    # Panel de publicación (manual / automático según OAuth)
    _render_panel_publicacion(articulo, imagenes)

    st.divider()

    # Imágenes
    separador_seccion("Motor gráfico — 3 imágenes por artículo")
    if imagenes:
        cols = st.columns(3)
        for i, (img, col) in enumerate(zip(imagenes, cols), 1):
            with col:
                estado_color = "#10B981" if img.estado == "GENERADA" else "#F59E0B"
                st.markdown(
                    f"<b>Imagen {i}</b> &nbsp;"
                    f"<span style='background:{estado_color};color:white;padding:2px 7px;"
                    f"border-radius:8px;font-size:11px;'>{img.estado}</span>",
                    unsafe_allow_html=True,
                )
                if img.estado == "GENERADA" and Path(img.url_local).exists():
                    st.image(img.url_local, use_column_width=True)
                else:
                    st.code(img.prompt_original[:200], language=None)
                    st.caption(f"Proveedor: {img.proveedor}")
    else:
        st.info("Las imágenes aparecerán aquí tras la generación.")

    st.divider()

    # Acción: guardar en calendario
    col_save, col_clear = st.columns(2)
    with col_save:
        if st.button("💾 Guardar en Calendario", type="primary", use_container_width=True):
            if imagenes:
                ok, msg = _guardar_en_calendario(articulo, imagenes)
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"Error: {msg}")
            else:
                st.warning("Genera las imágenes antes de guardar.")

    with col_clear:
        if st.button("🗑️ Limpiar resultado", use_container_width=True):
            st.session_state.pop(_KEY_ARTICULO, None)
            st.session_state.pop(_KEY_IMAGENES, None)
            st.rerun()


# ── Panel publicación (manual / automático) ───────────────────────────────────

_LIMITE_CHARS = {"LINKEDIN": 3000, "FACEBOOK": 63206, "INSTAGRAM": 2200}
_COLOR_OK     = "#10B981"
_COLOR_NO     = "#94A3B8"


def _render_panel_publicacion(articulo, imagenes: list) -> None:
    from src.modules.contenido.social_publisher import (
        FacebookPublisher, InstagramPublisher, LinkedInPublisher, estado_plataformas,
    )

    separador_seccion("Publicación en Redes Sociales")

    plataformas_cfg = estado_plataformas()
    hay_alguna_cfg  = any(plataformas_cfg.values())

    # Banner de estado global
    if hay_alguna_cfg:
        configuradas = [p for p, ok in plataformas_cfg.items() if ok]
        st.success(
            f"✅ **Publicación automática activa** para: {', '.join(configuradas)}"
        )
    else:
        st.info(
            "📋 **Modo manual activo** — ninguna red social tiene credenciales OAuth. "
            "Copia cada texto y pégalo en tu red. "
            "Cuando tengas los tokens, añádelos en `.env` para activar publicación automática."
        )

    # Una columna por plataforma
    col_li, col_fb, col_ig = st.columns(3)
    plataforma_cols = [
        ("LINKEDIN",  col_li, LinkedInPublisher()),
        ("FACEBOOK",  col_fb, FacebookPublisher()),
        ("INSTAGRAM", col_ig, InstagramPublisher()),
    ]

    hashtags_str = " ".join(articulo.hashtags)
    # URL de primera imagen (para Instagram)
    primera_img_url = ""
    if imagenes:
        primera_img_url = (imagenes[0].url_remota or imagenes[0].url_local) or ""

    for plataforma, col, publisher in plataforma_cols:
        with col:
            icono  = _PLATAFORMA_ICONO.get(plataforma, "📱")
            cfg    = publisher.is_configured()
            limite = _LIMITE_CHARS.get(plataforma, 3000)
            color  = _COLOR_OK if cfg else _COLOR_NO
            estado = "✅ Automático" if cfg else "📋 Manual"

            st.markdown(
                f"**{icono} {plataforma}**&nbsp;&nbsp;"
                f"<span style='background:{color};color:white;padding:2px 8px;"
                f"border-radius:8px;font-size:11px;'>{estado}</span>",
                unsafe_allow_html=True,
            )

            # Construir texto listo
            copy_raw = getattr(articulo, f"copy_{plataforma.lower()}",
                               articulo.copy_linkedin)
            texto = f"{copy_raw}\n\n{hashtags_str}\n\n{articulo.cta}"

            # Indicator de longitud
            n_chars = len(texto)
            pct     = min(n_chars / limite, 1.0)
            color_bar = _COLOR_OK if pct < 0.85 else ("#F59E0B" if pct < 1 else "#EF4444")
            st.markdown(
                f"<small style='color:{color_bar};'>"
                f"{n_chars:,} / {limite:,} caracteres</small>",
                unsafe_allow_html=True,
            )

            # Texto editable
            texto_editado = st.text_area(
                "Copy",
                value=texto,
                height=180,
                key=f"copy_pub_{plataforma}",
                label_visibility="collapsed",
            )

            # Botón de acción
            if cfg:
                if st.button(
                    f"📤 Publicar en {plataforma.capitalize()}",
                    key=f"btn_pub_{plataforma}",
                    use_container_width=True,
                    type="primary",
                ):
                    with st.spinner(f"Publicando en {plataforma}..."):
                        img_url = primera_img_url if plataforma == "INSTAGRAM" else ""
                        result  = publisher.publicar(texto_editado, img_url)
                    if result.ok:
                        st.success(f"✅ {result.mensaje} · ID: `{result.post_id}`")
                        # Registrar en BD
                        try:
                            from src.modules.contenido import SocialSchedulerService
                            from src.database.connection import get_session
                            from src.database.models import ContenidoRedes
                            from datetime import date as _date
                            with get_session() as s:
                                s.add(ContenidoRedes(
                                    tipo_contenido="ARTICULO_DIARIO",
                                    plataforma_destino=plataforma,
                                    texto_publicacion=texto_editado[:3000],
                                    url_imagen_1=primera_img_url,
                                    tema_sst=articulo.tema.categoria,
                                    estado_publicacion="PUBLICADO",
                                    fecha_generacion=articulo.fecha_generacion,
                                    fecha_publicacion=_date.today(),
                                    generado_por_ia=articulo.modelo_usado,
                                ))
                            st.cache_data.clear()
                        except Exception:
                            pass
                    else:
                        st.error(f"❌ {result.mensaje}")
            else:
                st.caption("Configura las credenciales en `.env` para publicar aquí automáticamente.")


# ── Tab 2: Calendario ─────────────────────────────────────────────────────────

def _render_calendario() -> None:
    separador_seccion("Calendario de contenido — próximos y recientes 14 días")

    contenidos = _cargar_calendario(dias=14)

    if not contenidos:
        st.info(
            "📭 No hay contenido programado aún. "
            "Genera un artículo en la pestaña **✍️ Generar Artículo** y guárdalo."
        )
        return

    _COLOR_ESTADO = {
        "PENDIENTE":  "#F59E0B",
        "PUBLICADO":  "#10B981",
        "ERROR":      "#EF4444",
        "BORRADOR":   "#94A3B8",
    }

    hoy = str(date.today())

    for item in contenidos:
        es_hoy = item["fecha"] == hoy
        borde = "4px solid #E65C00" if es_hoy else "1px solid #E2E8F0"
        col_info, col_estado, col_btn = st.columns([4, 1, 1])

        with col_info:
            etiqueta_hoy = " **← HOY**" if es_hoy else ""
            st.markdown(
                f"**{item['fecha']}**{etiqueta_hoy} &nbsp; "
                f"{_PLATAFORMA_ICONO.get(item['plataforma'], '📱')} {item['plataforma']}",
            )
            st.markdown(
                f"<small style='color:#6B7280;'>{item['tema']} &nbsp;·&nbsp; "
                f"{item['copy'][:80]}…</small>",
                unsafe_allow_html=True,
            )

        with col_estado:
            color = _COLOR_ESTADO.get(item["estado"], "#94A3B8")
            st.markdown(
                f"<span style='background:{color};color:white;padding:3px 9px;"
                f"border-radius:10px;font-size:11px;'>{item['estado']}</span>",
                unsafe_allow_html=True,
            )

        with col_btn:
            if item["estado"] == "PENDIENTE":
                if st.button(
                    "✅ Publicado",
                    key=f"pub_{item['id']}",
                    use_container_width=True,
                ):
                    ok, msg = _marcar_publicado(item["id"])
                    if ok:
                        st.success("Marcado.")
                        st.rerun()
                    else:
                        st.error(msg)

        st.markdown(
            "<hr style='margin:4px 0;border:none;border-top:1px solid #F1F5F9;'>",
            unsafe_allow_html=True,
        )


# ── Tab 3: Estadísticas ───────────────────────────────────────────────────────

def _render_estadisticas() -> None:
    stats = _cargar_estadisticas()

    c1, c2, c3, c4 = st.columns(4)
    with c1: tarjeta_kpi("Total Generados",  str(stats.get("total", 0)),     icono="📝", color="#1B3A6B")
    with c2: tarjeta_kpi("Pendientes",       str(stats.get("pendientes", 0)), icono="⏳", color="#F59E0B")
    with c3: tarjeta_kpi("Publicados",       str(stats.get("publicados", 0)), icono="✅", color="#10B981")
    with c4: tarjeta_kpi("Tasa de Éxito",    stats.get("tasa_exito", "N/A"),  icono="📈", color="#E65C00")

    st.divider()
    separador_seccion("Configuración del motor gráfico")

    import os
    col1, col2, col3 = st.columns(3)

    def _badge(cond):
        return ("✅ Activo" if cond else "❌ Requiere configuración")

    with col1:
        st.markdown("**🤖 DALL-E 3**")
        tiene_openai = bool(os.getenv("OPENAI_API_KEY", "").strip())
        st.markdown(_badge(tiene_openai))
        if not tiene_openai:
            st.caption("Añade `OPENAI_API_KEY=sk-...` en `.env`")

    with col2:
        st.markdown("**🎨 Stable Diffusion XL**")
        tiene_replicate = bool(os.getenv("REPLICATE_API_TOKEN", "").strip())
        st.markdown(_badge(tiene_replicate))
        if not tiene_replicate:
            st.caption("Añade `REPLICATE_API_TOKEN=r8_...` en `.env`")

    with col3:
        st.markdown("**🤖 Claude (artículos)**")
        tiene_claude = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
        st.markdown(_badge(tiene_claude))
        if not tiene_claude:
            st.caption("Añade `ANTHROPIC_API_KEY=sk-ant-...` en `.env`")

    st.divider()
    separador_seccion("Publicación en redes sociales")
    st.info(
        "**Publicación automática** en LinkedIn, Facebook e Instagram requiere configurar "
        "las APIs de cada plataforma (OAuth2). Por ahora, el flujo es:\n\n"
        "1. Genera el artículo → copia el **copy** de la plataforma\n"
        "2. Publica manualmente en tu cuenta\n"
        "3. Haz clic en **✅ Publicado** en el Calendario para registrarlo\n\n"
        "La integración directa con APIs de redes sociales está en hoja de ruta."
    )
