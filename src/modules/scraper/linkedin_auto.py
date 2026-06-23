"""
LinkedInAutoScraper — usa sesión guardada, extrae datos completos de empresas.
Para crear sesión: python scrape_linkedin_auto.py --solo-login
"""
import json
import re
import time
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

# Palabras que identifican que la tarjeta es de Colombia
_PALABRAS_COLOMBIA = [
    "Bogotá","Bogota","Medellín","Medellin","Cali","Barranquilla",
    "Bucaramanga","Pereira","Cartagena","Cúcuta","Cucuta","Ibagué","Ibague",
    "Villavicencio","Manizales","Pasto","Armenia","Neiva","Montería",
    "Colombia","Cundinamarca","Antioquia","Atlántico","Santander",
]


class LinkedInSinSesionError(Exception):
    pass


class LinkedInAutoScraper(BaseScraperAdapter):
    SOURCE = "LinkedIn"

    def __init__(self, max_paginas: int = 10, delay: float = 2.0):
        self._max_paginas = max_paginas
        self._delay = delay

    @staticmethod
    def sesion_existe() -> bool:
        return SESSION_FILE.exists()

    # ── JavaScript: extrae tarjetas de la página de resultados ───────────────

    _JS_LISTA = r"""
    () => {
        const COLOMBIA = """ + str(_PALABRAS_COLOMBIA).replace("'", '"') + r""";
        const seen = new Set();
        const results = [];

        // Iterar sobre cada <li> de resultado (no sobre <a> directamente)
        document.querySelectorAll('li').forEach(li => {
            // Buscar primer link a /company/ dentro de este li
            const a = li.querySelector('a[href*="/company/"]');
            if (!a) return;

            const href = a.href.split('?')[0].replace(/\/+$/, '');
            if (!href || seen.has(href)) return;
            // Ignorar sub-páginas
            if (/\/company\/(people|jobs|posts|videos|about|services|life)\b/.test(href)) return;
            if (/\/company\/?$/.test(href)) return;

            // ── Nombre: buscar en heading (h3/h4) dentro del li ──────────
            let name = '';
            const heading = li.querySelector('h3, h4, [role="heading"]');
            if (heading) {
                // Tomar solo el span con aria-hidden="true" o el primer span
                const sp = heading.querySelector('span[aria-hidden="true"]');
                name = sp ? sp.textContent.trim() : heading.textContent.trim();
                // Cortar en primera nueva línea
                name = name.split('\n')[0].trim();
            }

            // Si no hay heading, usar aria-label del link
            if (!name) name = (a.getAttribute('aria-label') || '').trim();
            // Limpiar prefijos de accesibilidad
            name = name.replace(/^(Ver página de empresa para|View company page for)\s*/i, '');
            // Cortar en "Seguir" / separadores
            name = name.replace(/\s*(Seguir|Follow|Ver perfil|View profile)[\s\S]*$/i, '').trim();
            // Eliminar trailing separadores
            name = name.replace(/[\s·\-–|,]+$/, '').trim();

            if (!name || name.length < 2) return;
            if (['LinkedIn','Ver perfil','Seguir','Follow','Inicio'].includes(name)) return;

            // ── Detectar si es Colombia ───────────────────────────────────
            const cardText = li.textContent || '';
            const esColombia = COLOMBIA.some(c => cardText.includes(c));

            seen.add(href);
            results.push({ href, name, esColombia });
        });
        return results;
    }
    """

    # ── JavaScript: extrae datos de la página "Acerca de" ────────────────────

    _JS_ABOUT = r"""
    () => {
        const data = { web: '', telefono: '', empleados: 0 };

        // Sitio web: primer link externo (no linkedin)
        for (const a of document.querySelectorAll('a[href^="http"]')) {
            if (!a.href.includes('linkedin.com') && !a.href.includes('javascript')) {
                data.web = a.href.split('?')[0];
                break;
            }
        }

        // Teléfono: link tel: primero
        const telLink = document.querySelector('a[href^="tel:"]');
        if (telLink) {
            data.telefono = telLink.href.replace('tel:', '').replace(/\s/g, '').trim();
        }
        // Si no hay tel: link, buscar en texto
        if (!data.telefono) {
            const body = document.body.innerText || '';
            const m = body.match(/\(?\+?57[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{4}|\b[36]\d{9}\b|\(\d{3}\)\s?\d{7}/);
            if (m) data.telefono = m[0].trim();
        }

        // Empleados: patrón "X-Y empleados" o "X empleados"
        const bodyTxt = document.body.innerText || '';
        let m = bodyTxt.match(/(\d[\d.,]*)\s*[\-–]\s*(\d[\d.,]*)\s*empleados/i);
        if (m) {
            data.empleados = parseInt(m[2].replace(/[.,]/g, ''));
        } else {
            m = bodyTxt.match(/(\d[\d.,]+)\s*empleados/i);
            if (m) data.empleados = parseInt(m[1].replace(/[.,]/g, ''));
        }

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

            # Cargar sesión guardada
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

            # ── Paso 1: Buscar ──────────────────────────────────────────────
            search_url = (
                "https://www.linkedin.com/search/results/companies/"
                f"?keywords={quote(keyword + ' Colombia')}&origin=GLOBAL_SEARCH_HEADER"
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
                    page.wait_for_selector("li a[href*='/company/']", timeout=10_000)
                    time.sleep(1.5)
                except Exception:
                    print(f"  No cargaron resultados en página {pagina}.")
                    break

                items: list[dict] = page.evaluate(self._JS_LISTA) or []
                nuevos = 0
                for item in items:
                    if len(empresas_raw) >= max_resultados:
                        break
                    nombre = item.get("name", "").strip()
                    link   = item.get("href", "").strip()
                    es_colombia = item.get("esColombia", True)

                    if not es_colombia:
                        print(f"    [omitir - no es Colombia] {nombre}")
                        continue
                    if not nombre or not link:
                        continue
                    if any(e["link"] == link for e in empresas_raw):
                        continue

                    empresas_raw.append({"nombre": nombre, "link": link})
                    nuevos += 1
                    print(f"    [{len(empresas_raw):03d}] {nombre}")

                if len(empresas_raw) >= max_resultados:
                    break

                # Siguiente página
                avanzado = False
                for sel in [
                    "button[aria-label='Siguiente']",
                    "button[aria-label='Next']",
                    "button.artdeco-pagination__button--next",
                    "li.artdeco-pagination__button--next button",
                ]:
                    try:
                        btn = page.locator(sel).first
                        if btn.is_visible(timeout=2000) and btn.is_enabled(timeout=1000):
                            btn.click()
                            time.sleep(2.5)
                            avanzado = True
                            break
                    except Exception:
                        pass

                if not avanzado:
                    # Intentar clic en el número de página siguiente
                    try:
                        btn = page.locator(f"button[aria-label='{pagina + 1}'], button:has-text('{pagina + 1}')").first
                        if btn.is_visible(timeout=1500):
                            btn.click()
                            time.sleep(2.5)
                            avanzado = True
                    except Exception:
                        pass

                if not avanzado:
                    print(f"  No hay más páginas.")
                    break

            print(f"  Total empresas encontradas: {len(empresas_raw)}")

            # ── Paso 4: Visitar Acerca de y extraer web, tel, empleados ─────
            for i, emp in enumerate(empresas_raw):
                web, telefono, empleados = "", "", 0
                about_url = emp["link"].rstrip("/") + "/about/"
                try:
                    page.goto(about_url, wait_until="domcontentloaded", timeout=15_000)
                    # Esperar que cargue el contenido real (LinkedIn es SPA)
                    try:
                        page.wait_for_selector("section, main", timeout=5_000)
                    except Exception:
                        pass
                    time.sleep(2)

                    data = page.evaluate(self._JS_ABOUT) or {}
                    web      = data.get("web", "") or ""
                    telefono = data.get("telefono", "") or ""
                    empleados = int(data.get("empleados", 0) or 0)

                    tag = "✅" if (web or telefono) else "·"
                    print(f"    [{i+1:03d}] {emp['nombre'][:45]} {tag} web={bool(web)} tel={telefono or '—'}")
                except Exception as e:
                    print(f"    [{i+1:03d}] {emp['nombre'][:45]} ERROR about: {e}")

                # Solo agregar si tiene algún dato de contacto útil
                if not web and not telefono:
                    print(f"    [{i+1:03d}] OMITIDO — sin web ni teléfono")
                    continue

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

    # ── Aplicar filtro de ciudad ──────────────────────────────────────────────

    @staticmethod
    def _aplicar_filtro_ciudad(page, ciudad: str) -> None:
        try:
            time.sleep(1.5)
            # Abrir panel "Todos los filtros"
            abierto = False
            for txt in ["Todos los filtros", "All filters"]:
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
                return

            # Buscar input de ubicación
            loc_input = None
            for sel in [
                "input[placeholder*='iudad']",
                "input[placeholder*='ubica']",
                "input[placeholder*='ocation']",
                "input[placeholder*='City']",
                "input[aria-label*='iudad']",
                "input[aria-label*='ocation']",
            ]:
                try:
                    inp = page.locator(sel).first
                    if inp.is_visible(timeout=1500):
                        loc_input = inp
                        break
                except Exception:
                    pass

            if loc_input is None:
                return

            # Escribir letra a letra para activar autocompletado
            loc_input.click()
            time.sleep(0.5)
            loc_input.press_sequentially(ciudad, delay=80)
            time.sleep(2.5)

            # Seleccionar sugerencia con "Colombia"
            for sel in ["div[role='option']", "li[role='option']", "[role='listbox'] [role='option']"]:
                try:
                    opciones = page.locator(sel).all()
                    if not opciones:
                        continue
                    seleccionado = False
                    for op in opciones[:6]:
                        txt = op.text_content() or ""
                        if "Colombia" in txt:
                            op.click()
                            seleccionado = True
                            break
                    if not seleccionado and opciones:
                        opciones[0].click()
                    time.sleep(1.5)
                    break
                except Exception:
                    pass

            # Confirmar
            for txt in ["Mostrar resultados", "Show results", "Aplicar"]:
                try:
                    ok = page.locator(f"button:has-text('{txt}')").first
                    if ok.is_visible(timeout=2000):
                        ok.click()
                        time.sleep(3)
                        print(f"  [filtro ciudad] ✅ {ciudad} aplicado")
                        return
                except Exception:
                    pass

        except Exception as e:
            print(f"  [filtro ciudad] {e}")
