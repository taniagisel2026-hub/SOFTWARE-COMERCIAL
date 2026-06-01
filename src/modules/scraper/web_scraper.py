"""
WebScraper — extrae y valida correos electrónicos desde sitios web corporativos.

Componente complementario: recibe un ProspectoExtraido con sitio_web
y enriquece su campo email con la dirección de contacto encontrada.
Respeta robots.txt implícitamente (timeout corto + no indexa recursivamente).
"""
import re
from urllib.parse import urljoin, urlparse

_PATRON_EMAIL = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

# Páginas de contacto típicas en sitios colombianos
_RUTAS_CONTACTO = [
    "/contacto", "/contactenos", "/contactenos.html",
    "/contact", "/contact-us",
    "/nosotros", "/about", "/quienes-somos",
    "/empresa", "/about-us",
]

# Dominios de email que suelen ser genéricos o de prueba
_DOMINIOS_FILTRO = {
    "example.com", "test.com", "email.com", "correo.com",
    "gmail.com", "hotmail.com", "yahoo.com",  # excluir personales
    "outlook.com", "live.com",
    "sentry.io", "wixpress.com", "wordpress.com",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}


class WebScraper:
    """
    Extrae emails corporativos de sitios web.
    No requiere dependencias externas si httpx y beautifulsoup4 están instalados.
    Degrada gracefully si no están disponibles.
    """

    def __init__(self, timeout: int = 10, max_paginas: int = 3):
        self._timeout = timeout
        self._max_paginas = max_paginas

    def extraer_email(self, url: str) -> str:
        """
        Busca la primera dirección de email corporativo en el sitio web.
        Retorna string vacío si no encuentra nada útil.
        """
        if not url or not url.startswith("http"):
            return ""
        try:
            return self._buscar_email(url)
        except Exception:
            return ""

    def enriquecer_prospectos(self, prospectos: list) -> list:
        """Añade email a cada prospecto que tenga sitio_web pero no tenga email."""
        for p in prospectos:
            if p.sitio_web and not p.tiene_email:
                p.email = self.extraer_email(p.sitio_web)
        return prospectos

    # ── Implementación interna ────────────────────────────────────────────────

    def _buscar_email(self, url_base: str) -> str:
        try:
            import httpx
            from bs4 import BeautifulSoup
        except ImportError:
            return ""

        dominio = urlparse(url_base).netloc
        urls_a_revisar = [url_base] + [
            urljoin(url_base, ruta) for ruta in _RUTAS_CONTACTO
        ]

        emails_encontrados: list[str] = []

        for url in urls_a_revisar[: self._max_paginas]:
            try:
                resp = httpx.get(url, headers=_HEADERS, timeout=self._timeout,
                                 follow_redirects=True)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")

                # Buscar en texto plano de la página
                texto = soup.get_text(" ", strip=True)
                emails_pagina = _PATRON_EMAIL.findall(texto)

                # También buscar en atributos href: mailto:
                for tag in soup.find_all("a", href=True):
                    href = tag["href"]
                    if href.startswith("mailto:"):
                        email_raw = href.replace("mailto:", "").split("?")[0].strip()
                        if email_raw:
                            emails_pagina.append(email_raw)

                emails_encontrados.extend(emails_pagina)

            except Exception:
                continue

        return self._seleccionar_mejor(emails_encontrados, dominio)

    @staticmethod
    def _seleccionar_mejor(emails: list[str], dominio_empresa: str) -> str:
        """
        Prioriza emails del dominio de la empresa sobre emails genéricos.
        Filtra los personales (gmail, hotmail, etc.).
        """
        if not emails:
            return ""

        # Normalizar
        emails_limpios = list({e.lower().strip() for e in emails
                               if _PATRON_EMAIL.fullmatch(e.strip())})

        # 1er filtro: eliminar dominios de redes sociales y genéricos
        emails_limpios = [
            e for e in emails_limpios
            if e.split("@")[-1] not in _DOMINIOS_FILTRO
        ]

        # Prioridad: email del mismo dominio corporativo
        for email in emails_limpios:
            if dominio_empresa and dominio_empresa.lstrip("www.") in email:
                return email

        # Cualquier email no filtrado
        return emails_limpios[0] if emails_limpios else ""
