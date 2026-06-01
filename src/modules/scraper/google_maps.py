"""
GoogleMapsScraper — extrae datos públicos de empresas desde Google Maps.

Modo real  : requiere `playwright install chromium` (ver requirements.txt)
Modo mock  : activo automáticamente si Playwright no está instalado;
             genera datos representativos de empresas colombianas para pruebas.
"""
import random
import time
from urllib.parse import quote

from .base import BaseScraperAdapter, ProspectoExtraido, _normalizar_texto

# Selectores CSS de Google Maps (pueden requerir actualización si Google cambia el DOM)
_SEL_FEED = "div[role='feed']"
_SEL_CARD = "a.hfpxzc"
_SEL_NAME = "div.qBF1Pd"
_SEL_ADDR = "div.W4Etob"
_SEL_PHONE = "button[data-item-id^='phone']"
_SEL_WEB = "a[data-item-id='authority']"

# Ciudades de Colombia con su departamento para enriquecer datos
_CIUDAD_DEPARTAMENTO: dict[str, str] = {
    "bogotá": "Cundinamarca",    "bogota": "Cundinamarca",
    "medellín": "Antioquia",     "medellin": "Antioquia",
    "cali": "Valle del Cauca",
    "barranquilla": "Atlántico",
    "bucaramanga": "Santander",
    "pereira": "Risaralda",
    "manizales": "Caldas",
    "cúcuta": "Norte de Santander",   "cucuta": "Norte de Santander",
    "ibagué": "Tolima",               "ibague": "Tolima",
    "cartagena": "Bolívar",
    "santa marta": "Magdalena",
    "villavicencio": "Meta",
    "pasto": "Nariño",
}

# Datos mock representativos por sector para modo sin Playwright
_MOCK_EMPRESAS: list[dict] = [
    {"razon_social": "Constructora Andina SAS", "sector": "Construcción",
     "telefono": "+57 601 555-0101", "direccion": "Cra 15 # 93-75"},
    {"razon_social": "Logística Colombiana LTDA", "sector": "Transporte y Logística",
     "telefono": "+57 601 555-0202", "direccion": "Av. Dorado # 69-76"},
    {"razon_social": "Industrias Metálicas del Norte SAS", "sector": "Manufactura",
     "telefono": "+57 601 555-0303", "direccion": "Zona Industrial Calle 13"},
    {"razon_social": "Servicios de Ingeniería ABC", "sector": "Ingeniería",
     "telefono": "+57 601 555-0404", "direccion": "Calle 80 # 69-76"},
    {"razon_social": "Distribuidora de Alimentos XYZ LTDA", "sector": "Alimentos",
     "telefono": "+57 601 555-0505", "direccion": "Calle 40 Sur # 50-20"},
    {"razon_social": "Empresa de Seguridad Vigilar SAS", "sector": "Seguridad",
     "telefono": "+57 601 555-0606", "direccion": "Carrera 7 # 32-29"},
    {"razon_social": "Clínica Médica Integral", "sector": "Salud",
     "telefono": "+57 601 555-0707", "direccion": "Av. 19 # 103-37"},
    {"razon_social": "Taller Automotriz Torres e Hijos", "sector": "Manufactura",
     "telefono": "+57 601 555-0808", "direccion": "Calle 6 # 30-12, Puente Aranda"},
    {"razon_social": "Panadería Industrial La Cosecha", "sector": "Alimentos",
     "telefono": "+57 601 555-0909", "direccion": "Transversal 93 # 52-56"},
    {"razon_social": "Carpintería Artesanal del Llano SAS", "sector": "Manufactura",
     "telefono": "+57 601 555-1010", "direccion": "Calle 24 # 42-11"},
]


class GoogleMapsScraper(BaseScraperAdapter):

    SOURCE = "Google Maps"

    def __init__(self, headless: bool = True, delay_min: float = 1.5, delay_max: float = 4.0):
        self._headless = headless
        self._delay_min = delay_min
        self._delay_max = delay_max

    def extraer(self, ciudad: str, sector: str, max_resultados: int = 30) -> list[ProspectoExtraido]:
        try:
            from playwright.sync_api import sync_playwright
            return self._extraer_playwright(ciudad, sector, max_resultados)
        except ImportError:
            print(f"  [GoogleMaps] Playwright no instalado → modo mock activo")
            return self._extraer_mock(ciudad, sector, max_resultados)

    # ── Implementación real con Playwright ────────────────────────────────────

    def _extraer_playwright(self, ciudad: str, sector: str, max_resultados: int) -> list[ProspectoExtraido]:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        query = f"{sector} en {ciudad} Colombia"
        url = f"https://www.google.com/maps/search/{quote(query)}"
        prospectos: list[ProspectoExtraido] = []
        depto = self._inferir_departamento(ciudad)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=self._headless,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--lang=es-CO"],
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="es-CO",
            )
            page = ctx.new_page()

            try:
                page.goto(url, wait_until="networkidle", timeout=30_000)
                self._delay()

                # Scroll del sidebar para cargar más resultados
                for _ in range(max(3, max_resultados // 8)):
                    page.evaluate(
                        f"document.querySelector('{_SEL_FEED}')?.scrollBy(0, 600)"
                    )
                    self._delay()

                cards = page.locator(_SEL_CARD).all()
                for card in cards[:max_resultados]:
                    prospecto = self._extraer_card(card, ciudad, depto, sector)
                    if prospecto:
                        prospectos.append(prospecto)

            except PWTimeout:
                print(f"  [GoogleMaps] Timeout cargando {url}")
            finally:
                browser.close()

        return prospectos

    def _extraer_card(self, card, ciudad: str, depto: str, sector: str):
        try:
            nombre = card.locator(_SEL_NAME).first.text_content(timeout=3000) or ""
            if not nombre.strip():
                return None
            return ProspectoExtraido(
                razon_social=nombre.strip(),
                ciudad=ciudad,
                departamento=depto,
                fuente=self.SOURCE,
                sector_economico=sector,
                confianza=0.75,
            )
        except Exception:
            return None

    # ── Enriquecimiento de detalle por empresa (clic en card) ─────────────────

    def enriquecer_detalle(self, page, prospecto: ProspectoExtraido) -> ProspectoExtraido:
        """Enriquece un prospecto con teléfono y web desde la ficha de Maps."""
        try:
            telefono_el = page.locator(_SEL_PHONE).first
            if telefono_el.is_visible(timeout=2000):
                prospecto.telefono = telefono_el.get_attribute("data-value") or ""

            web_el = page.locator(_SEL_WEB).first
            if web_el.is_visible(timeout=2000):
                prospecto.sitio_web = web_el.get_attribute("href") or ""
        except Exception:
            pass
        return prospecto

    # ── Mock ──────────────────────────────────────────────────────────────────

    def _extraer_mock(self, ciudad: str, sector: str, max_resultados: int) -> list[ProspectoExtraido]:
        depto = self._inferir_departamento(ciudad)
        seleccionados = random.sample(
            _MOCK_EMPRESAS, min(max_resultados, len(_MOCK_EMPRESAS))
        )
        return [
            ProspectoExtraido(
                razon_social=emp["razon_social"],
                ciudad=ciudad,
                departamento=depto,
                fuente=self.SOURCE,
                sector_economico=emp.get("sector", sector),
                telefono=emp.get("telefono", ""),
                direccion=emp.get("direccion", ""),
                num_empleados=random.randint(5, 80),
                confianza=0.6,
            )
            for emp in seleccionados
        ]

    # ── Utilidades ────────────────────────────────────────────────────────────

    def _delay(self) -> None:
        time.sleep(random.uniform(self._delay_min, self._delay_max))

    @staticmethod
    def _inferir_departamento(ciudad: str) -> str:
        return _CIUDAD_DEPARTAMENTO.get(_normalizar_texto(ciudad), "Colombia")
