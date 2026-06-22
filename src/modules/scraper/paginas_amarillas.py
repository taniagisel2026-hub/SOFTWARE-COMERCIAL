"""
PaginasAmarillasScraper — extrae empresas desde paginasamarillas.com.co

Directorio público colombiano sin CAPTCHA. Devuelve nombre, teléfono,
dirección y sitio web de empresas por sector y ciudad.
"""
import re
import time
import random
from urllib.parse import quote

from .base import BaseScraperAdapter, ProspectoExtraido, _normalizar_texto

_CIUDAD_DEPARTAMENTO: dict[str, str] = {
    "bogotá": "Bogotá D.C.",       "bogota": "Bogotá D.C.",
    "bogotá d.c.": "Bogotá D.C.",
    "medellín": "Antioquia",        "medellin": "Antioquia",
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
}

# Mapeo sector del sistema → término de búsqueda en Páginas Amarillas
_SECTOR_QUERY: dict[str, str] = {
    "Construcción":             "empresas de construccion",
    "Manufactura / Industria":  "industria manufactura",
    "Transporte y Logística":   "transporte logistica",
    "Comercio y Retail":        "comercio retail",
    "Servicios Empresariales":  "servicios empresariales",
    "Salud y Clínicas":         "clinicas salud",
    "Educación":                "educacion colegios",
    "Agricultura y Ganadería":  "agricultura ganaderia",
    "Minería y Energía":        "mineria energia",
    "Tecnología y Software":    "tecnologia software",
    "Alimentos y Bebidas":      "alimentos bebidas",
    "Seguridad Privada":        "seguridad privada vigilancia",
    "Ingeniería y Consultoría": "ingenieria consultoria",
    "Petróleo y Gas":           "petroleo gas",
}


class PaginasAmarillasScraper(BaseScraperAdapter):

    SOURCE = "Páginas Amarillas"

    def __init__(self, delay_min: float = 1.0, delay_max: float = 3.0):
        self._delay_min = delay_min
        self._delay_max = delay_max

    def extraer(self, ciudad: str, sector: str, max_resultados: int = 30) -> list[ProspectoExtraido]:
        try:
            import requests
            from bs4 import BeautifulSoup
            return self._extraer_requests(ciudad, sector, max_resultados, requests, BeautifulSoup)
        except ImportError:
            pass
        try:
            from playwright.sync_api import sync_playwright
            return self._extraer_playwright(ciudad, sector, max_resultados)
        except ImportError:
            return []

    # ── Extracción con requests + BeautifulSoup (más liviana) ────────────────

    def _extraer_requests(self, ciudad: str, sector: str, max_resultados: int,
                          requests, BeautifulSoup) -> list[ProspectoExtraido]:
        query = _SECTOR_QUERY.get(sector, sector.lower())
        ciudad_norm = _normalizar_texto(ciudad)
        depto = _CIUDAD_DEPARTAMENTO.get(ciudad_norm, "Colombia")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "es-CO,es;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        prospectos: list[ProspectoExtraido] = []
        pagina = 1

        while len(prospectos) < max_resultados:
            url = (
                f"https://www.paginasamarillas.com.co/busqueda/"
                f"?que={quote(query)}&donde={quote(ciudad)}&pagina={pagina}"
            )
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    break
                soup = BeautifulSoup(resp.text, "html.parser")
                nuevos = self._parsear_pagina(soup, ciudad, depto, sector)
                if not nuevos:
                    break
                prospectos.extend(nuevos)
                pagina += 1
                time.sleep(random.uniform(self._delay_min, self._delay_max))
            except Exception as e:
                print(f"  [PaginasAmarillas] Error página {pagina}: {e}")
                break

        return prospectos[:max_resultados]

    def _parsear_pagina(self, soup, ciudad: str, depto: str, sector: str) -> list[ProspectoExtraido]:
        prospectos = []
        # Los listados están en elementos article o div con clase de empresa
        items = (
            soup.select("article.business-card") or
            soup.select("div.listing-item") or
            soup.select("div.result-item") or
            soup.select("li.result") or
            soup.select("div[class*='business']") or
            soup.select("div[class*='empresa']")
        )
        for item in items:
            nombre = self._texto(item, ["h2", "h3", "h4", ".business-name", ".name", ".title"])
            if not nombre or len(nombre) < 3:
                continue
            telefono = self._texto(item, [".phone", ".telefono", "[itemprop='telephone']", "span[class*='phone']"])
            direccion = self._texto(item, [".address", ".direccion", "[itemprop='address']"])
            web = ""
            link = item.select_one("a[href*='http']")
            if link:
                href = link.get("href", "")
                if "paginasamarillas" not in href and href.startswith("http"):
                    web = href

            prospectos.append(ProspectoExtraido(
                razon_social=nombre,
                ciudad=ciudad,
                departamento=depto,
                fuente=self.SOURCE,
                sector_economico=sector,
                telefono=telefono or "",
                direccion=direccion or "",
                sitio_web=web,
                confianza=0.70,
            ))
        return prospectos

    @staticmethod
    def _texto(item, selectores: list[str]) -> str:
        for sel in selectores:
            el = item.select_one(sel)
            if el:
                return el.get_text(strip=True)
        return ""

    # ── Fallback con Playwright si requests no funciona ──────────────────────

    def _extraer_playwright(self, ciudad: str, sector: str, max_resultados: int) -> list[ProspectoExtraido]:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        query = _SECTOR_QUERY.get(sector, sector.lower())
        ciudad_norm = _normalizar_texto(ciudad)
        depto = _CIUDAD_DEPARTAMENTO.get(ciudad_norm, "Colombia")
        url = f"https://www.paginasamarillas.com.co/busqueda/?que={quote(query)}&donde={quote(ciudad)}"
        prospectos: list[ProspectoExtraido] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            page = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="es-CO",
            ).new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(3000)

                items = page.locator("article, div[class*='business'], div[class*='result'], li[class*='result']").all()
                for item in items[:max_resultados]:
                    try:
                        nombre = item.locator("h2,h3,h4").first.text_content(timeout=1000) or ""
                        nombre = nombre.strip()
                        if not nombre:
                            continue
                        prospectos.append(ProspectoExtraido(
                            razon_social=nombre,
                            ciudad=ciudad,
                            departamento=depto,
                            fuente=self.SOURCE,
                            sector_economico=sector,
                            confianza=0.65,
                        ))
                    except Exception:
                        continue
            except PWTimeout:
                print(f"  [PaginasAmarillas] Timeout")
            finally:
                browser.close()

        return prospectos
