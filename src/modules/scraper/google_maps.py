"""
GoogleMapsScraper — extrae datos públicos de empresas desde Google Maps.

Estrategias implementadas (según análisis del equipo):
  1. Google Search → URLs de Maps (más estable que el feed visual)
  2. Ficha individual → datos completos por empresa
  3. Selectores múltiples → resistente a cambios de interfaz de Google
  4. Detección automática de CAPTCHA → mensajes claros, no "0 empresas"
  5. Comportamiento humano → delays aleatorios, scroll gradual

Modo mock: activo automáticamente si Playwright no está instalado.
"""
import random
import re
import time
from urllib.parse import quote

from .base import BaseScraperAdapter, ProspectoExtraido, _normalizar_texto

# ── Variaciones de búsqueda por sector ───────────────────────────────────────
# Términos que usan las empresas colombianas que necesitan SG-SST (Res. 0312/2019)
_VARIACIONES_SECTOR: dict[str, list[str]] = {
    "Construcción": [
        "constructora", "obras civiles", "ingeniería civil", "empresa constructora",
        "contratista de obras", "edificaciones", "infraestructura", "obra negra",
        "acabados de construcción", "interventoría de obras",
    ],
    "Manufactura / Industria": [
        "fábrica", "planta industrial", "industria manufacturera", "taller industrial",
        "metalmecánica", "ensamblaje", "planta de producción", "manufactura",
        "empresa industrial", "taller metalmecánico",
    ],
    "Transporte y Logística": [
        "empresa de transporte", "transportadora", "logística", "flota de camiones",
        "empresa de carga", "mensajería y paquetería", "operador logístico",
        "transporte de mercancías", "courier", "empresa de mudanzas",
    ],
    "Comercio y Retail": [
        "distribuidora", "almacén mayorista", "empresa comercial", "bodega comercial",
        "importadora", "exportadora", "comercializadora", "mayorista",
        "tienda por departamentos", "supermercado",
    ],
    "Servicios Empresariales": [
        "empresa de servicios", "outsourcing", "servicios corporativos", "consultoría empresarial",
        "call center", "empresa de aseo y mantenimiento", "servicios generales",
        "empresa de limpieza", "vigilancia y aseo", "facilities",
    ],
    "Salud y Clínicas": [
        "clínica", "hospital", "centro médico", "IPS", "laboratorio clínico",
        "consultorio médico", "centro de diagnóstico", "clínica odontológica",
        "centro de rehabilitación", "hogar geriátrico",
    ],
    "Hotelería y Turismo": [
        "hotel", "hostal", "resort", "agencia de viajes", "operador turístico",
        "restaurante de cadena", "club campestre", "spa y bienestar",
        "empresa de eventos", "alojamiento turístico",
    ],
    "Petróleo y Gas": [
        "empresa petrolera", "empresa de gas", "refinería", "estación de servicio industrial",
        "empresa de perforación", "servicios petroleros", "empresa de hidrocarburos",
        "ductos y oleoductos", "planta de gas natural", "empresa de combustibles",
    ],
    "Ingeniería y Consultoría": [
        "firma de ingeniería", "consultoría técnica", "empresa de ingeniería",
        "interventoría", "supervisión de proyectos", "ingeniería eléctrica",
        "ingeniería mecánica", "diseño estructural", "gerencia de proyectos",
        "empresa de topografía",
    ],
    "Farmacéutico y Químico": [
        "laboratorio farmacéutico", "empresa química", "droguería mayorista",
        "distribuidora de medicamentos", "empresa de cosméticos", "laboratorio de análisis",
        "empresa de plaguicidas", "industria química", "empresa de pinturas", "planta química",
    ],
    "Telecomunicaciones": [
        "empresa de telecomunicaciones", "proveedor de internet", "empresa de cable",
        "torre de comunicaciones", "empresa de fibra óptica", "call center",
        "empresa de radiocomunicaciones", "proveedor ISP", "empresa de antenas",
        "soluciones de conectividad",
    ],
    "Entretenimiento y Eventos": [
        "empresa de eventos", "productora de eventos", "empresa de espectáculos",
        "empresa de audio y video", "empresa de iluminación", "organizadora de eventos",
        "empresa de logística de eventos", "empresa de catering", "empresa de decoración",
        "parque de diversiones",
    ],
    "Minería y Energía": [
        "empresa minera", "explotación minera", "empresa energética", "planta eléctrica",
        "energía solar", "empresa petrolera", "carbón", "cantera",
        "planta de gas", "empresa de energía",
    ],
    "Tecnología y Software": [
        "empresa de tecnología", "desarrollo de software", "empresa TI",
        "soluciones tecnológicas", "sistemas informáticos", "empresa de telecomunicaciones",
        "data center", "soporte técnico empresarial", "empresa de ciberseguridad",
        "integradora tecnológica",
    ],
    "Alimentos y Bebidas": [
        "empresa de alimentos", "procesadora de alimentos", "planta de alimentos",
        "empresa de bebidas", "panadería industrial", "lácteos",
        "cárnica", "empresa de confitería", "planta de jugos", "catering industrial",
    ],
    "Seguridad Privada": [
        "empresa de vigilancia", "seguridad privada", "vigilancia y seguridad",
        "empresa de guardas", "seguridad electrónica", "monitoreo de alarmas",
        "empresa de escoltas", "vigilancia industrial", "control de acceso",
        "empresa de seguridad física",
    ],
}

# ── Selectores con fallback múltiple (Estrategia 3) ──────────────────────────
_SEL_FEED   = "div[role='feed']"
_SEL_CARD   = "a[href*='/maps/place/']"

# Teléfono — de más específico a más general
_SELS_PHONE = [
    "button[data-item-id^='phone']",
    "a[href^='tel:']",
    "[aria-label*='teléfono']",
    "[aria-label*='Teléfono']",
    "[aria-label*='phone']",
    "[data-tooltip*='teléfono']",
    "span[aria-label*='teléfono']",
]

# Sitio web — de más específico a más general
_SELS_WEB = [
    "a[data-item-id='authority']",
    "a[href^='http'][aria-label*='sitio web']",
    "a[href^='http'][aria-label*='web']",
    "a[href^='http'][aria-label*='website']",
    "button[data-item-id='authority']",
]

# Nombre del lugar en ficha individual
_SELS_NOMBRE = [
    "h1.DUwDvf",
    "h1[class*='fontHeadlineLarge']",
    "h1",
    "[data-item-id='title']",
    "[role='main'] h1",
]

# Dirección — para extraer ciudad real
_SELS_ADDR = [
    "button[data-item-id='address']",
    "[data-item-id='address']",
    "button[aria-label*='dirección']",
    "button[aria-label*='Dirección']",
    "[data-tooltip='Copiar dirección']",
]

# Señales de bloqueo / CAPTCHA (Estrategia 4)
_CAPTCHA_SIGNALS = [
    "captcha", "unusual traffic", "verify you are human",
    "not a robot", "unusual activity", "google.com/sorry",
    "nuestros sistemas han detectado",
]

# Nombres de departamento (normalizados) — usados para detectar si el último
# segmento de una dirección de Maps es un departamento o ya es la ciudad.
_DEPARTAMENTOS_COLOMBIA: set[str] = {
    _normalizar_texto(d) for d in [
        "Amazonas", "Antioquia", "Arauca", "Atlántico", "Bogotá D.C.", "Bogota D.C.",
        "Bolívar", "Boyacá", "Caldas", "Caquetá", "Casanare", "Cauca", "Cesar",
        "Chocó", "Córdoba", "Cundinamarca", "Guainía", "Guaviare", "Huila",
        "La Guajira", "Magdalena", "Meta", "Nariño", "Norte de Santander",
        "Putumayo", "Quindío", "Risaralda", "San Andrés y Providencia",
        "Santander", "Sucre", "Tolima", "Valle del Cauca", "Vaupés", "Vichada",
    ]
}

# Mapa ciudad → departamento
_CIUDAD_DEPARTAMENTO: dict[str, str] = {
    "bogotá": "Cundinamarca",    "bogota": "Cundinamarca",
    "bogotá d.c.": "Cundinamarca", "bogota d.c.": "Cundinamarca",
    "medellín": "Antioquia",     "medellin": "Antioquia",
    "cali": "Valle del Cauca",
    "barranquilla": "Atlántico",
    "bucaramanga": "Santander",
    "pereira": "Risaralda",
    "manizales": "Caldas",
    "cúcuta": "Norte de Santander", "cucuta": "Norte de Santander",
    "ibagué": "Tolima",             "ibague": "Tolima",
    "cartagena": "Bolívar",
    "santa marta": "Magdalena",
    "villavicencio": "Meta",
    "pasto": "Nariño",
    # Municipios del clúster Bogotá + Cundinamarca
    "soacha": "Cundinamarca", "chia": "Cundinamarca", "cota": "Cundinamarca",
    "facatativa": "Cundinamarca", "fusagasuga": "Cundinamarca", "zipaquira": "Cundinamarca",
    "villeta": "Cundinamarca", "girardot": "Cundinamarca", "mosquera": "Cundinamarca",
    "la vega": "Cundinamarca", "cajica": "Cundinamarca", "sopo": "Cundinamarca",
    "la calera": "Cundinamarca", "guaduas": "Cundinamarca", "tocancipa": "Cundinamarca",
    "madrid": "Cundinamarca", "sibate": "Cundinamarca", "funza": "Cundinamarca",
    "tausa": "Cundinamarca", "ricaurte": "Cundinamarca", "cogua": "Cundinamarca",
    "gachancipa": "Cundinamarca", "nemocon": "Cundinamarca", "tabio": "Cundinamarca",
    "tenjo": "Cundinamarca", "bojaca": "Cundinamarca", "el rosal": "Cundinamarca",
    "subachoque": "Cundinamarca", "zipacon": "Cundinamarca", "agua de dios": "Cundinamarca",
    "nilo": "Cundinamarca", "tocaima": "Cundinamarca", "silvania": "Cundinamarca",
    "arbelaez": "Cundinamarca", "granada": "Cundinamarca",
}

_MOCK_EMPRESAS: list[dict] = [
    {"razon_social": "Constructora Andina SAS",         "telefono": "+57 601 555-0101", "direccion": "Cra 15 # 93-75"},
    {"razon_social": "Logística Colombiana LTDA",        "telefono": "+57 601 555-0202", "direccion": "Av. Dorado # 69-76"},
    {"razon_social": "Industrias Metálicas del Norte",   "telefono": "+57 601 555-0303", "direccion": "Zona Industrial Calle 13"},
    {"razon_social": "Servicios de Ingeniería ABC",      "telefono": "+57 601 555-0404", "direccion": "Calle 80 # 69-76"},
    {"razon_social": "Distribuidora de Alimentos XYZ",   "telefono": "+57 601 555-0505", "direccion": "Calle 40 Sur # 50-20"},
    {"razon_social": "Empresa de Seguridad Vigilar SAS", "telefono": "+57 601 555-0606", "direccion": "Carrera 7 # 32-29"},
    {"razon_social": "Clínica Médica Integral",          "telefono": "+57 601 555-0707", "direccion": "Av. 19 # 103-37"},
    {"razon_social": "Taller Automotriz Torres e Hijos", "telefono": "+57 601 555-0808", "direccion": "Calle 6 # 30-12"},
    {"razon_social": "Panadería Industrial La Cosecha",  "telefono": "+57 601 555-0909", "direccion": "Transversal 93 # 52-56"},
    {"razon_social": "Carpintería Artesanal del Llano",  "telefono": "+57 601 555-1010", "direccion": "Calle 24 # 42-11"},
]


class GoogleMapsScraper(BaseScraperAdapter):

    SOURCE = "Google Maps"

    def __init__(self, headless: bool = True, delay_min: float = 0.5, delay_max: float = 1.2):
        self._headless = headless
        self._delay_min = delay_min
        self._delay_max = delay_max

    def extraer(self, ciudad: str, sector: str, max_resultados: int = 30) -> list[ProspectoExtraido]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("  [GoogleMaps] Playwright no instalado → modo mock activo")
            return self._extraer_mock(ciudad, sector, max_resultados)

        terminos = [sector] + _VARIACIONES_SECTOR.get(sector, [])
        todos: list[ProspectoExtraido] = []
        vistos: set[str] = set()
        por_termino = max(25, max_resultados // 3)
        depto = self._inferir_departamento(ciudad)

        # Un solo Chrome para todas las variaciones — más eficiente y menos sospechoso
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=self._headless,
                args=[
                    "--no-sandbox", "--disable-dev-shm-usage", "--lang=es-CO",
                    "--disable-blink-features=AutomationControlled",
                    "--window-size=1280,800",
                ],
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="es-CO",
            )
            ctx.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = ctx.new_page()

            try:
                for termino in terminos:
                    if len(todos) >= max_resultados:
                        break
                    print(f"  [GoogleMaps] Buscando: '{termino}' en {ciudad}")
                    parcial = self._buscar_en_maps_directo(page, ciudad, termino, depto, por_termino)
                    nuevas = 0
                    for p in parcial:
                        clave = p.razon_social.lower().strip()[:30]
                        if clave not in vistos:
                            vistos.add(clave)
                            todos.append(p)
                            nuevas += 1
                    print(f"    → {nuevas} nuevas (total: {len(todos)})")
                    if len(todos) >= max_resultados:
                        break
                    # Pausa entre búsquedas para no levantar sospechas
                    time.sleep(random.uniform(1.5, 3.0))
            except Exception as exc:
                # No perder lo ya extraído si el navegador se cae a mitad de camino.
                print(f"  [GoogleMaps] ⚠ Interrumpido ({exc}); se conservan {len(todos)} ya extraídos")

            try:
                browser.close()
            except Exception:
                pass  # el navegador ya pudo haberse cerrado/caído por su cuenta

        print(f"  [GoogleMaps] Total combinado: {len(todos)} empresas únicas")
        return todos[:max_resultados]


    # ── Estrategia 1: Google Search → URLs de Maps ────────────────────────────

    def _buscar_urls_google_search(self, page, sector: str, ciudad: str, max_resultados: int) -> list[str]:
        """
        Busca en Google con site:google.com/maps para obtener URLs directas.
        Más estable que el feed de Maps porque los resultados de búsqueda cambian menos.
        """
        from playwright.sync_api import TimeoutError as PWTimeout

        query = f"{sector} {ciudad} Colombia site:google.com/maps"
        search_url = f"https://www.google.com/search?q={quote(query)}&num=20&hl=es"

        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=25_000)
            self._aceptar_cookies(page)
            self._delay()

            # Detectar bloqueo (Estrategia 4)
            if self._detectar_bloqueo(page):
                print("  [GoogleMaps] ⛔ Google detectó actividad inusual en Search. Intenta más tarde.")
                return []

            # Extraer URLs de Maps de los resultados
            urls: list[str] = page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a[href*="google.com/maps"]'));
                const urls = links
                    .map(l => l.href)
                    .filter(h => h.includes('/maps/place/'));
                return [...new Set(urls)];
            }""")

            # También intentar segunda página si hay pocos resultados
            if len(urls) < 5:
                try:
                    next_btn = page.locator("a[aria-label='Página siguiente'], a#pnnext").first
                    if next_btn.count() > 0 and next_btn.is_visible(timeout=2000):
                        next_btn.click()
                        self._delay()
                        urls2: list[str] = page.evaluate("""() => {
                            const links = Array.from(document.querySelectorAll('a[href*="google.com/maps"]'));
                            return [...new Set(links.map(l => l.href).filter(h => h.includes('/maps/place/')))];
                        }""")
                        urls = list(dict.fromkeys(urls + urls2))
                except Exception:
                    pass

            return urls[:max_resultados]

        except PWTimeout:
            print("  [GoogleMaps] Timeout en Google Search")
            return []
        except Exception as e:
            print(f"  [GoogleMaps] Error en Google Search: {e}")
            return []

    # ── Estrategia 2: ficha individual de Maps (por URL directa) ─────────────

    def _extraer_ficha_individual(self, page, url: str, ciudad: str, depto: str, sector: str) -> ProspectoExtraido | None:
        """
        Visita la URL directa de un lugar en Maps.
        Las fichas individuales son mucho más estables que el feed de resultados.
        """
        from playwright.sync_api import TimeoutError as PWTimeout
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            time.sleep(random.uniform(0.8, 1.8))

            if self._detectar_bloqueo(page):
                return None

            # Nombre con múltiples selectores (Estrategia 3)
            nombre = self._obtener_texto_con_fallback(page, _SELS_NOMBRE)
            if not nombre or len(nombre) < 3:
                return None

            # Teléfono con múltiples selectores (Estrategia 3)
            telefono = self._obtener_atributo_con_fallback(page, _SELS_PHONE, ["data-value", "href", "innerText"])
            if telefono.startswith("tel:"):
                telefono = telefono[4:]

            # Sitio web con múltiples selectores (Estrategia 3)
            web = self._obtener_atributo_con_fallback(page, _SELS_WEB, ["href"])
            if "google.com" in web or "maps.google" in web:
                web = ""

            return ProspectoExtraido(
                razon_social=nombre,
                ciudad=ciudad,
                departamento=depto,
                fuente=self.SOURCE,
                sector_economico=sector,
                telefono=telefono,
                sitio_web=web,
                confianza=0.85,
            )
        except PWTimeout:
            return None
        except Exception:
            return None

    # ── Estrategia 2B: feed directo de Maps (fallback) ────────────────────────

    def _buscar_en_maps_directo(self, page, ciudad: str, sector: str, depto: str, max_resultados: int) -> list[ProspectoExtraido]:
        """Búsqueda directa en Google Maps — más frágil pero funciona sin Google Search."""
        from playwright.sync_api import TimeoutError as PWTimeout

        query = f"{sector} en {ciudad} Colombia"
        url = f"https://www.google.com/maps/search/{quote(query)}"
        prospectos: list[ProspectoExtraido] = []

        try:
            print(f"  [GoogleMaps] Abriendo: {url[:80]}")
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            print(f"  [GoogleMaps] URL actual: {page.url[:80]}")
            self._aceptar_cookies(page)
            time.sleep(2)

            # Detectar bloqueo (Estrategia 4)
            if self._detectar_bloqueo(page):
                print("  [GoogleMaps] ⛔ Google Maps solicitó verificación. Extracción detenida.")
                return prospectos

            print(f"  [GoogleMaps] Esperando feed div[role='feed']...")
            try:
                page.wait_for_selector(_SEL_FEED, timeout=30_000)
                print(f"  [GoogleMaps] ✅ Feed encontrado")
            except PWTimeout:
                # Intentar selector alternativo
                print(f"  [GoogleMaps] Feed principal no encontrado, probando alternativo...")
                try:
                    page.wait_for_selector("div[role='main']", timeout=10_000)
                    print(f"  [GoogleMaps] ✅ div[role='main'] encontrado (Maps cargó diferente)")
                except PWTimeout:
                    print("  [GoogleMaps] ⛔ Maps no cargó ningún contenido en 30s")
                    return prospectos

            # Scroll gradual (Estrategia 5)
            self._scroll_gradual(page, max_resultados)

            # Intentar varios selectores de cards
            cards = page.locator(_SEL_CARD).all()
            print(f"  [GoogleMaps] Cards con selector '{_SEL_CARD}': {len(cards)}")
            if not cards:
                cards = page.locator("a[href*='maps/place']").all()
                print(f"  [GoogleMaps] Cards alternativo: {len(cards)}")

            for i, card in enumerate(cards[:max_resultados]):
                nombre = (card.get_attribute("aria-label") or "").strip().split(",")[0].strip()
                if not nombre or len(nombre) < 3:
                    continue

                p = ProspectoExtraido(
                    razon_social=nombre,
                    ciudad=ciudad,
                    departamento=depto,
                    fuente=self.SOURCE,
                    sector_economico=sector,
                    confianza=0.70,
                )

                # Enriquecer con clic en la ficha (Estrategia 2)
                try:
                    card.click(timeout=3000)
                    time.sleep(random.uniform(0.5, 1.0))
                    telefono = self._obtener_atributo_con_fallback(page, _SELS_PHONE, ["data-value", "href"])
                    web = self._obtener_atributo_con_fallback(page, _SELS_WEB, ["href"])
                    direccion_raw = self._obtener_atributo_con_fallback(page, _SELS_ADDR, ["aria-label", "data-value"])
                    if telefono.startswith("tel:"):
                        telefono = telefono[4:]
                    if web and "google.com" not in web:
                        p.sitio_web = web
                    if telefono:
                        p.telefono = telefono
                    if direccion_raw:
                        ciudad_real, depto_real = self._parsear_ciudad_de_direccion(direccion_raw, ciudad, depto)
                        p.ciudad = ciudad_real
                        p.departamento = depto_real
                    p.confianza = 0.80
                except Exception:
                    pass

                prospectos.append(p)
                print(f"    [{i+1:03d}] {nombre[:55]} | tel={p.telefono or '—'}")
                self._delay()

        except PWTimeout:
            print("  [GoogleMaps] Timeout cargando Maps")

        return prospectos

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _detectar_bloqueo(self, page) -> bool:
        """Estrategia 4: detecta CAPTCHA o bloqueo real de Google."""
        try:
            url_actual = page.url.lower()
            # Solo verificar URL — el HTML normal de Maps contiene "captcha" en su JS
            if "google.com/sorry" in url_actual or "sorry/index" in url_actual:
                return True
            # Verificar si hay un iframe de reCAPTCHA visible (bloqueo real)
            tiene_captcha = page.evaluate("""() => {
                const iframes = Array.from(document.querySelectorAll('iframe'));
                return iframes.some(f => (f.src || '').includes('recaptcha') ||
                                        (f.src || '').includes('captcha'));
            }""")
            return bool(tiene_captcha)
        except Exception:
            return False

    def _aceptar_cookies(self, page) -> None:
        for texto in ["Aceptar todo", "Accept all", "Acepto", "I agree"]:
            try:
                btn = page.get_by_text(texto, exact=True)
                if btn.is_visible(timeout=2000):
                    btn.click()
                    page.wait_for_timeout(1000)
                    break
            except Exception:
                pass

    def _obtener_texto_con_fallback(self, page, selectores: list[str]) -> str:
        """Estrategia 3: prueba cada selector hasta obtener texto."""
        for sel in selectores:
            try:
                el = page.locator(sel).first
                if el.count() > 0 and el.is_visible(timeout=1000):
                    texto = (el.text_content(timeout=1000) or "").strip()
                    if texto:
                        return texto
            except Exception:
                pass
        return ""

    def _obtener_atributo_con_fallback(self, page, selectores: list[str], atributos: list[str]) -> str:
        """Estrategia 3: prueba cada selector y atributo hasta obtener un valor."""
        for sel in selectores:
            try:
                el = page.locator(sel).first
                if el.count() > 0 and el.is_visible(timeout=1000):
                    for attr in atributos:
                        if attr == "innerText":
                            valor = (el.text_content(timeout=500) or "").strip()
                        else:
                            valor = (el.get_attribute(attr) or "").strip()
                        if valor:
                            return valor
            except Exception:
                pass
        return ""

    def _scroll_gradual(self, page, max_resultados: int) -> None:
        """Estrategia 5: scroll con pasos y tiempos aleatorios, imita comportamiento humano."""
        pasos = max(8, max_resultados // 3)
        for _ in range(pasos):
            pixels = random.randint(400, 900)
            # Comillas dobles en el selector para evitar conflicto con las simples de role='feed'
            page.evaluate(f'document.querySelector("{_SEL_FEED}")?.scrollBy(0, {pixels})')
            time.sleep(random.uniform(0.3, 0.8))

    def _delay(self) -> None:
        """Estrategia 5: pausa aleatoria entre acciones."""
        time.sleep(random.uniform(self._delay_min, self._delay_max))

    @staticmethod
    def _inferir_departamento(ciudad: str) -> str:
        return _CIUDAD_DEPARTAMENTO.get(_normalizar_texto(ciudad), "Colombia")

    @staticmethod
    def _parsear_ciudad_de_direccion(direccion: str, ciudad_default: str, depto_default: str) -> tuple[str, str]:
        """
        Extrae la ciudad real de una dirección de Google Maps.
        Google Maps normalmente devuelve solo 2 segmentos: "Calle 80 #47-21, Medellín"
        (sin departamento). A veces sí incluye 3: "Calle 80 #47-21, Medellín, Antioquia".
        Se distingue mirando si el último segmento es un nombre de departamento conocido;
        si no lo es, el último segmento ES la ciudad (no la calle).
        """
        # Limpiar prefijos como "Dirección: "
        texto = re.sub(r"^[Dd]irección[:\s]+", "", direccion).strip()
        partes = [p.strip() for p in texto.split(",")]

        # Quitar "Colombia" al final y el código postal si hay
        partes = [p for p in partes if p.lower() not in ("colombia", "") and not p.strip().isdigit()]

        if len(partes) < 2:
            return ciudad_default, depto_default

        ultimo = partes[-1].strip()
        if len(partes) >= 3 and _normalizar_texto(ultimo) in _DEPARTAMENTOS_COLOMBIA:
            # Formato de 3 segmentos: "calle, ciudad, departamento"
            ciudad_real = partes[-2].strip()
            depto_real = ultimo
        else:
            # Formato de 2 segmentos (el más común): "calle, ciudad"
            ciudad_real = ultimo
            depto_real = GoogleMapsScraper._inferir_departamento(ciudad_real)
            if depto_real == "Colombia":
                depto_real = depto_default

        if ciudad_real and not ciudad_real.isdigit() and len(ciudad_real) > 2:
            return ciudad_real, depto_real

        return ciudad_default, depto_default

    # ── Mock (sin Playwright) ─────────────────────────────────────────────────

    def _extraer_mock(self, ciudad: str, sector: str, max_resultados: int) -> list[ProspectoExtraido]:
        depto = self._inferir_departamento(ciudad)
        seleccionados = random.sample(_MOCK_EMPRESAS, min(max_resultados, len(_MOCK_EMPRESAS)))
        return [
            ProspectoExtraido(
                razon_social=emp["razon_social"],
                ciudad=ciudad,
                departamento=depto,
                fuente=self.SOURCE,
                sector_economico=sector,
                telefono=emp.get("telefono", ""),
                direccion=emp.get("direccion", ""),
                num_empleados=random.randint(5, 80),
                confianza=0.6,
            )
            for emp in seleccionados
        ]
