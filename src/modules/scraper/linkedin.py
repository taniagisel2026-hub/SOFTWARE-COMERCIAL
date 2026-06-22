"""
LinkedInScraper — mapea perfiles corporativos y roles de decisión.

Estrategia: búsqueda Google site:linkedin.com/company + páginas públicas.
No requiere autenticación en LinkedIn (solo datos visibles sin login).
Si Playwright no está disponible, activa modo mock automáticamente.
"""
import random
import re
import time
from urllib.parse import quote

from .base import BaseScraperAdapter, ProspectoExtraido, _normalizar_texto

# Roles de decisión relevantes para venta SST
_CARGOS_HSEQ = [
    "Director HSEQ", "Gerente SST", "Coordinador SST", "Jefe de SST",
    "Gerente de RRHH", "Director de Talento Humano", "Gerente General",
    "Subgerente Administrativo", "Gerente de Operaciones",
]

_MOCK_EMPRESAS_LI: list[dict] = [
    {"razon_social": "Grupo Empresarial Pacífico SAS", "cargo": "Director HSEQ",
     "contacto": "Carlos Moreno", "empleados": 120, "sector": "Manufactura"},
    {"razon_social": "Servicios Integrados del Caribe LTDA", "cargo": "Coordinador SST",
     "contacto": "Ana Ruiz", "empleados": 55, "sector": "Servicios"},
    {"razon_social": "Constructora Horizonte SAS", "cargo": "Gerente de Operaciones",
     "contacto": "Javier Pérez", "empleados": 200, "sector": "Construcción"},
    {"razon_social": "Transporte Rápido Andino SA", "cargo": "Gerente de RRHH",
     "contacto": "María López", "empleados": 180, "sector": "Transporte"},
    {"razon_social": "Alimentos Frescos del Valle LTDA", "cargo": "Gerente General",
     "contacto": "Pedro Gómez", "empleados": 65, "sector": "Alimentos"},
    {"razon_social": "Ingeniería Eléctrica Especializada SAS", "cargo": "Director HSEQ",
     "contacto": "Sandra Castro", "empleados": 38, "sector": "Ingeniería"},
    {"razon_social": "Plásticos Industriales de Colombia", "cargo": "Subgerente Administrativo",
     "contacto": "Luis Herrera", "empleados": 95, "sector": "Manufactura"},
    {"razon_social": "Clínica Especializada del Norte SAS", "cargo": "Jefe de SST",
     "contacto": "Claudia Vargas", "empleados": 150, "sector": "Salud"},
]


class LinkedInScraper(BaseScraperAdapter):

    SOURCE = "LinkedIn"
    # Google busca páginas públicas de LinkedIn sin requerir login
    _GOOGLE_TPL = "site:linkedin.com/company {sector} {ciudad} Colombia"

    def __init__(self, headless: bool = True, delay_min: float = 2.0, delay_max: float = 5.0):
        self._headless = headless
        self._delay_min = delay_min
        self._delay_max = delay_max

    def extraer(self, ciudad: str, sector: str, max_resultados: int = 20) -> list[ProspectoExtraido]:
        try:
            from playwright.sync_api import sync_playwright
            return self._extraer_via_google(ciudad, sector, max_resultados)
        except ImportError:
            print(f"  [LinkedIn] Playwright no instalado → modo mock activo")
            return self._extraer_mock(ciudad, sector, max_resultados)

    # ── Búsqueda vía Google site: (sin login LinkedIn) ────────────────────────

    def _extraer_via_google(self, ciudad: str, sector: str, max_resultados: int) -> list[ProspectoExtraido]:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        query = self._GOOGLE_TPL.format(sector=sector, ciudad=ciudad)
        url = f"https://www.google.com/search?q={quote(query)}&num={min(max_resultados, 20)}"
        prospectos: list[ProspectoExtraido] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=self._headless,
                args=["--no-sandbox", "--lang=es-CO"],
            )
            page = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            ).new_page()

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                self._delay()

                # Esperar resultados de búsqueda
                try:
                    page.wait_for_selector("h3", timeout=10_000)
                except Exception:
                    print(f"  [LinkedIn] Sin resultados de Google")
                    return prospectos

                # Selectores compatibles con el diseño actual de Google Search
                resultados = page.locator("div.g, div.MjjYud div[data-hveid]").all()
                if not resultados:
                    resultados = page.locator("div[data-sokoban-container]").all()
                for resultado in resultados[:max_resultados]:
                    prospecto = self._parsear_resultado_google(resultado, ciudad, sector)
                    if prospecto:
                        prospectos.append(prospecto)

            except PWTimeout:
                print(f"  [LinkedIn] Timeout en búsqueda Google")
            finally:
                browser.close()

        return prospectos

    def _parsear_resultado_google(self, resultado, ciudad: str, sector: str):
        try:
            titulo = resultado.locator("h3").first.text_content(timeout=2000) or ""
            snippet = resultado.locator("div.VwiC3b").first.text_content(timeout=2000) or ""
            href = resultado.locator("a").first.get_attribute("href") or ""

            if "linkedin.com/company" not in href:
                return None

            # Limpiar nombre: "Empresa XYZ | LinkedIn" → "Empresa XYZ"
            nombre = re.sub(r"\s*[|\-–]\s*(LinkedIn|empresa|compañía).*", "", titulo, flags=re.IGNORECASE).strip()
            if not nombre:
                return None

            # Extraer tamaño de empleados del snippet si está disponible
            num_empleados = 0
            match_emp = re.search(r"(\d[\d.,]+)\s*(empleados|employees|colaboradores)", snippet, re.I)
            if match_emp:
                num_empleados = int(re.sub(r"[.,]", "", match_emp.group(1)))

            # Detectar cargo de decisión mencionado en snippet
            cargo = ""
            for c in _CARGOS_HSEQ:
                if c.lower() in snippet.lower():
                    cargo = c
                    break

            return ProspectoExtraido(
                razon_social=nombre,
                ciudad=ciudad,
                departamento="",
                fuente=self.SOURCE,
                sector_economico=sector,
                num_empleados=num_empleados,
                cargo_contacto=cargo,
                sitio_web=href,
                confianza=0.65,
                raw_data={"snippet": snippet[:300], "url": href},
            )
        except Exception:
            return None

    # ── Mock ──────────────────────────────────────────────────────────────────

    def _extraer_mock(self, ciudad: str, sector: str, max_resultados: int) -> list[ProspectoExtraido]:
        seleccionados = random.sample(
            _MOCK_EMPRESAS_LI, min(max_resultados, len(_MOCK_EMPRESAS_LI))
        )
        return [
            ProspectoExtraido(
                razon_social=emp["razon_social"],
                ciudad=ciudad,
                departamento="",
                fuente=self.SOURCE,
                sector_economico=emp.get("sector", sector),
                nombre_contacto=emp.get("contacto", ""),
                cargo_contacto=emp.get("cargo", ""),
                num_empleados=emp.get("empleados", 0),
                confianza=0.55,
            )
            for emp in seleccionados
        ]

    def _delay(self) -> None:
        time.sleep(random.uniform(self._delay_min, self._delay_max))
