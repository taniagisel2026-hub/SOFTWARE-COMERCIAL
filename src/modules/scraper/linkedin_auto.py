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


class LinkedInSinSesionError(Exception):
    """Se lanza cuando no existe linkedin_session.json."""
    pass


class LinkedInAutoScraper(BaseScraperAdapter):
    SOURCE = "LinkedIn"

    def __init__(self, max_paginas: int = 5, delay: float = 2.0):
        self._max_paginas = max_paginas
        self._delay = delay

    @staticmethod
    def sesion_existe() -> bool:
        return SESSION_FILE.exists()

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
        query = f"{keyword} {ciudad} Colombia"
        search_url = (
            "https://www.linkedin.com/search/results/companies/"
            f"?keywords={quote(query)}&origin=GLOBAL_SEARCH_HEADER"
        )

        prospectos: list[ProspectoExtraido] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=False,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
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

            # Verificar que la sesión sigue activa
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20_000)
            time.sleep(2)
            if "login" in page.url or "authwall" in page.url:
                browser.close()
                SESSION_FILE.unlink(missing_ok=True)
                raise LinkedInSinSesionError(
                    "Sesión expirada. Corre: python scrape_linkedin_auto.py --solo-login"
                )

            # Buscar empresas
            page.goto(search_url, wait_until="domcontentloaded", timeout=20_000)
            time.sleep(3)

            empresas_raw: list[dict] = []
            pagina = 1
            max_pag = min(self._max_paginas, max_resultados // 10 + 1)

            while pagina <= max_pag and len(empresas_raw) < max_resultados:
                time.sleep(self._delay)

                cards = page.locator("li.reusable-search__result-container").all()
                if not cards:
                    cards = page.locator("li[class*='result']").all()
                if not cards:
                    break

                for card in cards:
                    if len(empresas_raw) >= max_resultados:
                        break
                    try:
                        nombre = self._extraer_nombre(card)
                        if not nombre:
                            continue
                        link = self._extraer_link(card)
                        num_emp = self._extraer_empleados(card)
                        empresas_raw.append({
                            "nombre": nombre,
                            "link": link,
                            "num_emp": num_emp,
                        })
                    except Exception:
                        continue

                # Siguiente página
                try:
                    next_btn = page.locator("button[aria-label='Siguiente']").first
                    if next_btn.is_visible(timeout=2000) and next_btn.is_enabled(timeout=2000):
                        next_btn.click()
                        pagina += 1
                        time.sleep(self._delay)
                    else:
                        break
                except Exception:
                    break

            # Obtener sitio web de cada empresa
            for emp in empresas_raw:
                sitio_web = ""
                if emp["link"]:
                    try:
                        about_url = emp["link"].rstrip("/") + "/about/"
                        page.goto(about_url, wait_until="domcontentloaded", timeout=12_000)
                        time.sleep(1.5)
                        links = page.locator("a[href^='http']").all()
                        for lnk in links:
                            try:
                                href = lnk.get_attribute("href") or ""
                                if href.startswith("http") and "linkedin" not in href:
                                    sitio_web = href.split("?")[0]
                                    break
                            except Exception:
                                pass
                    except Exception:
                        pass

                prospectos.append(ProspectoExtraido(
                    razon_social=emp["nombre"],
                    ciudad=ciudad,
                    departamento=depto,
                    fuente=self.SOURCE,
                    sector_economico=sector,
                    sitio_web=sitio_web,
                    num_empleados=emp["num_emp"],
                    nivel_riesgo_arl=nivel_riesgo,
                    confianza=0.8,
                ))

            browser.close()

        return prospectos

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extraer_nombre(card) -> str:
        for sel in ["span[aria-hidden='true']", "span.entity-result__title-text",
                    "a span[aria-hidden='true']"]:
            try:
                el = card.locator(sel).first
                if el.count() > 0:
                    txt = (el.text_content(timeout=500) or "").strip()
                    if txt and len(txt) > 2 and txt.lower() not in ["linkedin", "ver perfil"]:
                        return txt
            except Exception:
                pass
        return ""

    @staticmethod
    def _extraer_link(card) -> str:
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
