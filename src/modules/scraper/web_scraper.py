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

_PATRON_TELEFONO = re.compile(
    r'\b(?:\+57[\s\-]?)?(?:60[1-9]|3[0-9]{2})[\s\-]?\d{3}[\s\-]?\d{4}\b'
)

# Páginas de contacto típicas en sitios colombianos
_RUTAS_CONTACTO = [
    "/contacto", "/contactenos", "/contactenos.html",
    "/contact", "/contact-us",
    "/nosotros", "/about", "/quienes-somos",
    "/empresa", "/about-us",
]

# Dominios técnicos/falsos a ignorar (NO incluir gmail/hotmail — PyMEs colombianas los usan)
_DOMINIOS_FILTRO = {
    "example.com", "test.com", "email.com", "correo.com",
    "sentry.io", "wixpress.com", "wordpress.com",
    "schemas.org", "w3.org", "jquery.com",
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

    def extraer_telefono(self, url: str) -> str:
        """Busca teléfono colombiano en el sitio web."""
        if not url or not url.startswith("http"):
            return ""
        try:
            import httpx
            dominio = urlparse(url).netloc
            urls = [url] + [urljoin(url, r) for r in _RUTAS_CONTACTO]
            for u in urls[:self._max_paginas]:
                try:
                    resp = httpx.get(u, headers=_HEADERS, timeout=self._timeout, follow_redirects=True)
                    if resp.status_code != 200:
                        continue
                    # Buscar en tel: links primero
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        if a["href"].startswith("tel:"):
                            tel = a["href"].replace("tel:", "").strip()
                            if tel:
                                return tel
                    # Buscar patrón colombiano en texto
                    tels = _PATRON_TELEFONO.findall(resp.text)
                    if tels:
                        return tels[0].strip()
                except Exception:
                    continue
        except Exception:
            pass
        return ""

    def enriquecer_prospectos(self, prospectos: list) -> list:
        """Visita el sitio web de cada prospecto y añade email y/o teléfono si faltan."""
        for p in prospectos:
            if not p.sitio_web:
                continue
            necesita_email = not p.tiene_email
            necesita_tel   = not p.telefono
            if not necesita_email and not necesita_tel:
                continue
            # Una sola pasada al sitio para extraer ambos
            email, tel = self._buscar_email_y_telefono(p.sitio_web)
            if necesita_email and email:
                p.email = email
            if necesita_tel and tel:
                p.telefono = tel
        return prospectos

    # ── Implementación interna ────────────────────────────────────────────────

    def _buscar_email(self, url_base: str) -> str:
        email, _ = self._buscar_email_y_telefono(url_base)
        return email

    def _buscar_email_y_telefono(self, url_base: str) -> tuple[str, str]:
        try:
            import httpx
            from bs4 import BeautifulSoup
        except ImportError:
            return "", ""

        dominio = urlparse(url_base).netloc
        urls_a_revisar = [url_base] + [
            urljoin(url_base, ruta) for ruta in _RUTAS_CONTACTO
        ]

        emails_encontrados: list[str] = []
        tel_encontrado = ""

        for url in urls_a_revisar[: self._max_paginas]:
            try:
                resp = httpx.get(url, headers=_HEADERS, timeout=self._timeout,
                                 follow_redirects=True)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")

                # ── Emails ────────────────────────────────────────────────
                texto = soup.get_text(" ", strip=True)
                emails_pagina = _PATRON_EMAIL.findall(texto)
                for tag in soup.find_all("a", href=True):
                    href = tag["href"]
                    if href.startswith("mailto:"):
                        email_raw = href.replace("mailto:", "").split("?")[0].strip()
                        if email_raw:
                            emails_pagina.append(email_raw)
                emails_encontrados.extend(emails_pagina)

                # ── Teléfono ──────────────────────────────────────────────
                if not tel_encontrado:
                    for tag in soup.find_all("a", href=True):
                        if tag["href"].startswith("tel:"):
                            tel_encontrado = tag["href"].replace("tel:", "").strip()
                            break
                    if not tel_encontrado:
                        tels = _PATRON_TELEFONO.findall(resp.text)
                        if tels:
                            tel_encontrado = tels[0].strip()

            except Exception:
                continue

        return self._seleccionar_mejor(emails_encontrados, dominio), tel_encontrado

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
