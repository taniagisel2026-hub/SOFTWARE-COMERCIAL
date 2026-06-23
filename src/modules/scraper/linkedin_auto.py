"""
LinkedInAutoScraper — adaptador que usa sesión guardada (no requiere input()).

Flujo:
  1. Lee linkedin_session.json (raíz del proyecto)
  2. Carga cookies en Playwright
  3. Busca empresas en LinkedIn por sector/ciudad automáticamente
  4. Visita el perfil /about/ de cada empresa para obtener su web
  5. Retorna lista de ProspectoExtraido

Si no existe linkedin_session.json, lanza LinkedInSinSesionError.
Para crear la sesión: python scrape_linkedin_auto.py --solo-login
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path

from .base import BaseScraperAdapter, ProspectoExtraido, estimar_nivel_riesgo

_ROOT = Path(__file__).parent.parent.parent.parent
SESSION_FILE = _ROOT / "linkedin_session.json"

_SECTOR_KEYWORD: dict[str, str] = {
    "construcción":             "construcción",
    "construccion":             "construcción",
    "manufactura / industria":  "manufactura industria",
    "manufactura":              "manufactura",
    "transporte y logística":   "transporte logística",
    "transporte":               "transporte",
    "comercio y retail":        "comercio",
    "comercio":                 "comercio",
    "servicios empresariales":  "servicios empresariales",
    "salud y clínicas":         "salud clínica",
    "salud":                    "salud",
    "educación":                "educación",
    "alimentos y bebidas":      "alimentos bebidas",
    "seguridad privada":        "seguridad vigilancia",
    "ingeniería y consultoría": "ingeniería consultoría",
    "tecnología y software":    "tecnología software",
    "tecnología":               "tecnología",
    "minería y energía":        "minería energía",
    "minería":                  "minería",
}

_CIUDAD_DEPARTAMENTO: dict[str, str] = {
    "bogotá d.c.": "Bogotá D.C.", "bogotá": "Bogotá D.C.", "bogota": "Bogotá D.C.",
    "medellín": "Antioquia",      "medellin": "Antioquia",
    "cali": "Valle del Cauca",
    "barranquilla": "Atlántico",
    "bucaramanga": "Santander",
    "pereira": "Risaralda",
    "cartagena": "Bolívar",
    "cúcuta": "Norte de Santander", "cucuta": "Norte de Santander",
    "ibagué": "Tolima",            "ibague": "Tolima",
    "villavicencio": "Meta",
}

# IDs geográficos de LinkedIn para ciudades colombianas
# (se usan como filtro companyHqGeo en la URL de búsqueda)
_CIUDAD_GEO_ID: dict[str, str] = {
    "bogotá d.c.": "102364368", "bogotá": "102364368", "bogota": "102364368",
    "medellín":    "100996579", "medellin": "100996579",
    "cali":        "106057199",
    "barranquilla":"104421764",
    "bucaramanga": "105255724",
    "pereira":     "105303307",
    "cartagena":   "100550483",
    "cúcuta":      "105302813", "cucuta": "105302813",
    "ibagué":      "105305387", "ibague": "105305387",
    "villavicencio":"105303044",
}


class LinkedInSinSesionError(Exception):
    """Se lanza cuando no existe linkedin_session.json."""
    pass


class LinkedInAutoScraper(BaseScraperAdapter):
    SOURCE = "LinkedIn"

    def __init__(self, max_paginas: int = 10, delay: float = 2.0):
        self._max_paginas = max_paginas
        self._delay = delay

    @staticmethod
    def sesion_existe() -> bool:
        return SESSION_FILE.exists()

    # ── JS de extracción de tarjetas (lista de resultados) ────────────────────

    _JS_LISTA = """
    () => {
        function limpiarNombre(raw) {
            let s = raw.replace(/\\s*(Seguir|Follow|Ver perfil|View profile)[\\s\\S]*$/i, '').trim();
            for (let k = 5; k <= Math.floor(s.length / 2); k++) {
                if (s.substring(k, 2 * k) === s.substring(0, k)) { s = s.substring(0, k).trim(); break; }
            }
            return s.replace(/[·\\-\\u2013|]+$/, '').trim();
        }
        const COLOMBIA = ['Bogotá','Bogota','Medellín','Medellin','Cali','Barranquilla',
            'Bucaramanga','Pereira','Cartagena','Cúcuta','Cucuta','Ibagué','Ibague',
            'Villavicencio','Manizales','Pasto','Armenia','Neiva','Montería','Colombia',
            'Cundinamarca','Antioquia','Valle','Santander','Atlántico','Bolivar'];
        const seen = new Set();
        const results = [];
        document.querySelectorAll('a[href*="/company/"]').forEach(a => {
            const href = a.href.split('?')[0].replace(/\\/+$/, '');
            if (!href || seen.has(href)) return;
            if (['/people','/jobs','/posts','/videos','/about','/services'].some(p => href.includes('/company' + p))) return;
            if (href.match(/\\/company\\/?$/)) return;
            let name = a.getAttribute('aria-label') || '';
            if (!name) {
                const spans = a.querySelectorAll('span[aria-hidden="true"]');
                if (spans.length > 0) {
                    const nodes = Array.from(spans[0].childNodes).filter(n => n.nodeType === 3).map(n => n.textContent.trim()).filter(t => t);
                    name = nodes.length > 0 ? nodes[0] : spans[0].textContent.trim();
                }
            }
            if (!name) name = (a.textContent || '').trim().split('\\n')[0].trim();
            name = limpiarNombre(name);
            if (!name || name.length < 2 || ['LinkedIn','Ver perfil','Seguir','Follow','Inicio'].includes(name)) return;
            // Detectar si la tarjeta menciona alguna ciudad/dpto colombiano
            const li = a.closest('li') || a.parentElement;
            const cardText = li ? (li.textContent || '') : '';
            const esColombia = COLOMBIA.some(c => cardText.includes(c));
            seen.add(href);
            results.push({ href, name, esColombia });
        });
        return results;
    }
    """

    # ── JS de extracción de página "Acerca de" ────────────────────────────────

    _JS_ABOUT = """
    () => {
        const data = { web: '', telefono: '', empleados: 0 };
        // Sitio web: primer link externo
        document.querySelectorAll('a[href^="http"]').forEach(a => {
            if (!data.web && !a.href.includes('linkedin')) data.web = a.href.split('?')[0];
        });
        // Teléfono: link tel: o texto junto a etiqueta
        const telLink = document.querySelector('a[href^="tel:"]');
        if (telLink) data.telefono = telLink.href.replace('tel:','').trim();
        // Empleados: buscar patrón "X-Y empleados" o "X empleados"
        const bodyTxt = document.body.innerText || '';
        let m = bodyTxt.match(/(\\d+)\\s*[\\-–]\\s*(\\d+)\\s*empleados/i);
        if (m) data.empleados = parseInt(m[2]);
        else { m = bodyTxt.match(/(\\d+)\\s*empleados/i); if (m) data.empleados = parseInt(m[1]); }
        return data;
    }
    """

    def extraer(
        self,
        ciudad: str,
        sector: str,
        max_resultados: int = 30,
    ) -> list[ProspectoExtraido]:
        if not SESSION_FILE.exists():
            raise LinkedInSinSesionError(
                "Sesión LinkedIn no configurada. "
                "Corre: python scrape_linkedin_auto.py --solo-login"
            )

        from playwright.sync_api import sync_playwright
        from urllib.parse import quote

        ciudad_norm = ciudad.lower().strip()
        depto = _CIUDAD_DEPARTAMENTO.get(ciudad_norm, "Colombia")
        nivel_riesgo = estimar_nivel_riesgo(sector)
        keyword = _SECTOR_KEYWORD.get(sector.lower().strip(), sector)

        prospectos: list[ProspectoExtraido] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=False,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 900},
                locale="es-CO",
            )
            ctx.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            try:
                cookies = json.loads(SESSION_FILE.read_text())
                ctx.add_cookies(cookies)
            except Exception as exc:
                browser.close()
                raise LinkedInSinSesionError(f"Error cargando sesión: {exc}") from exc

            page = ctx.new_page()

            # Verificar sesión activa
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20_000)
            time.sleep(2)
            if "login" in page.url or "authwall" in page.url:
                browser.close()
                SESSION_FILE.unlink(missing_ok=True)
                raise LinkedInSinSesionError(
                    "Sesión expirada. Corre: python scrape_linkedin_auto.py --solo-login"
                )

            # ── Paso 1: Buscar con keyword ──────────────────────────────────
            search_url = (
                "https://www.linkedin.com/search/results/companies/"
                f"?keywords={quote(keyword)}&origin=GLOBAL_SEARCH_HEADER"
            )
            page.goto(search_url, wait_until="domcontentloaded", timeout=20_000)
            time.sleep(3)

            # ── Paso 2: Aplicar filtro de ciudad ────────────────────────────
            self._aplicar_filtro_ciudad(page, ciudad)

            # ── Paso 3: Recolectar links de empresas (hasta 10 páginas) ─────
            empresas_raw: list[dict] = []
            max_pag = min(10, max(1, max_resultados // 10 + 1))

            for pagina in range(1, max_pag + 1):
                print(f"  Página {pagina}...")
                try:
                    page.wait_for_selector("a[href*='/company/']", timeout=10_000)
                    time.sleep(1.5)
                except Exception:
                    break

                items: list[dict] = page.evaluate(self._JS_LISTA) or []
                nuevos = 0
                for item in items:
                    if len(empresas_raw) >= max_resultados:
                        break
                    nombre = item.get("name", "").strip()
                    link   = item.get("href", "").strip()
                    es_colombia = item.get("esColombia", True)  # duda → incluir
                    if not es_colombia:
                        print(f"    [SKIP no Colombia] {nombre}")
                        continue
                    if nombre and link and not any(e["link"] == link for e in empresas_raw):
                        empresas_raw.append({"nombre": nombre, "link": link})
                        nuevos += 1
                        print(f"    [{len(empresas_raw):03d}] {nombre}")

                if len(empresas_raw) >= max_resultados:
                    break

                # Siguiente página
                avanzado = False
                for sel in ["button[aria-label='Siguiente']", "button[aria-label='Next']"]:
                    try:
                        btn = page.locator(sel).first
                        if btn.is_visible(timeout=2000) and btn.is_enabled(timeout=1000):
                            btn.click()
                            time.sleep(2.5)
                            avanzado = True
                            break
                    except Exception:
                        pass
                if not avanzado or not nuevos:
                    break

            print(f"  Total empresas encontradas: {len(empresas_raw)}")

            # ── Paso 4: Visitar Acerca de de cada empresa ───────────────────
            for i, emp in enumerate(empresas_raw):
                web, telefono, empleados = "", "", 0
                about_url = emp["link"].rstrip("/") + "/about/"
                try:
                    page.goto(about_url, wait_until="domcontentloaded", timeout=15_000)
                    time.sleep(1.8)
                    data = page.evaluate(self._JS_ABOUT) or {}
                    web      = data.get("web", "")
                    telefono = data.get("telefono", "")
                    empleados = data.get("empleados", 0) or 0
                    tag = f"{'✉️' if web else '·'}"
                    print(f"    [{i+1:03d}] {emp['nombre'][:40]} {tag} tel={telefono or '—'} emp={empleados or '—'}")
                except Exception:
                    pass

                prospectos.append(ProspectoExtraido(
                    razon_social=emp["nombre"],
                    ciudad=ciudad,
                    departamento=depto,
                    fuente=self.SOURCE,
                    sector_economico=sector,
                    sitio_web=web,
                    telefono=telefono,
                    num_empleados=empleados,
                    nivel_riesgo_arl=nivel_riesgo,
                    confianza=0.8,
                ))

            browser.close()

        return prospectos

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _aplicar_filtro_ciudad(page, ciudad: str) -> None:
        """Aplica el filtro de ciudad en LinkedIn usando la UI. Falla silenciosamente."""
        try:
            time.sleep(1.5)
            # ── 1. Abrir panel "Todos los filtros" ────────────────────────
            abierto = False
            for txt in ["Todos los filtros", "All filters", "Filtros"]:
                try:
                    btn = page.locator(f"button:has-text('{txt}')").first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        time.sleep(2.5)
                        abierto = True
                        break
                except Exception:
                    pass
            if not abierto:
                print("  [filtro ciudad] no se encontró el botón de filtros")
                return

            # ── 2. Encontrar el input de ubicación ─────────────────────────
            loc_input = None
            # Selectores de mayor a menor especificidad
            selectores = [
                "input[placeholder*='iudad']",
                "input[placeholder*='ubica']",
                "input[placeholder*='ocation']",
                "input[placeholder*='City']",
                "input[placeholder*='Where']",
                "input[placeholder*='Dónde']",
                "input[aria-label*='iudad']",
                "input[aria-label*='ocation']",
            ]
            for sel in selectores:
                try:
                    inp = page.locator(sel).first
                    if inp.is_visible(timeout=1500):
                        loc_input = inp
                        break
                except Exception:
                    pass

            if loc_input is None:
                print("  [filtro ciudad] no se encontró input de ubicación")
                return

            # ── 3. Escribir ciudad letra a letra para activar autocompletado ──
            loc_input.click()
            time.sleep(0.5)
            loc_input.press_sequentially(ciudad, delay=80)  # 80 ms entre caracteres
            time.sleep(2.5)

            # ── 4. Seleccionar la primera sugerencia que contenga Colombia ──
            seleccionado = False
            for sel in ["div[role='option']", "li[role='option']",
                        "[role='listbox'] [role='option']", "[role='listbox'] li"]:
                try:
                    opciones = page.locator(sel).all()
                    if not opciones:
                        continue
                    for opcion in opciones[:6]:
                        texto_op = (opcion.text_content() or "").strip()
                        # Preferir sugerencia que mencione Colombia
                        if "Colombia" in texto_op or ciudad[:5].lower() in texto_op.lower():
                            opcion.click()
                            seleccionado = True
                            break
                    if not seleccionado and opciones:
                        opciones[0].click()
                        seleccionado = True
                    if seleccionado:
                        time.sleep(1.5)
                        break
                except Exception:
                    pass

            if not seleccionado:
                print("  [filtro ciudad] no aparecieron sugerencias")
                return

            # ── 5. Confirmar / Mostrar resultados ──────────────────────────
            for txt in ["Mostrar resultados", "Show results", "Aplicar", "Apply", "Ver resultados"]:
                try:
                    ok = page.locator(f"button:has-text('{txt}')").first
                    if ok.is_visible(timeout=2000):
                        ok.click()
                        time.sleep(3)
                        print(f"  [filtro ciudad] ✅ {ciudad} aplicado")
                        break
                except Exception:
                    pass

        except Exception as e:
            print(f"  [filtro ciudad] error: {e}")

    @staticmethod
    def _extraer_link(card) -> str:  # kept for compatibility
        try:
            a = card.locator("a[href*='/company/']").first
            if a.count() > 0:
                href = a.get_attribute("href") or ""
                if not href.startswith("http"):
                    href = "https://www.linkedin.com" + href
                return href.split("?")[0].rstrip("/")
        except Exception:
            pass
        return ""

    @staticmethod
    def _extraer_empleados(card) -> int:
        try:
            snippet = card.text_content(timeout=500) or ""
            m = re.search(r'(\d[\d.,]+)\s*(?:empleados|seguidores)', snippet, re.I)
            if m:
                return int(re.sub(r"[.,]", "", m.group(1)))
        except Exception:
            pass
        return 0
