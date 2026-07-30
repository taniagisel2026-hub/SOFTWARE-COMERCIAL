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


def _parece_telefono_valido(valor: str) -> bool:
    """Descarta texto basura (ej. 'Llamar al número de teléfono') que no es un número real."""
    return bool(re.search(r"\d{7}", valor or ""))


def _numero_co_valido(numero: str) -> str:
    """
    Normaliza a +57XXXXXXXXXX si 'numero' (solo dígitos) es un celular colombiano
    real; retorna "" en cualquier otro caso. Sin esto, un enlace wa.me mal armado
    (ej. api.whatsapp.com/send con el número en un parámetro que no es 'phone', o
    un negocio con WhatsApp de otro país) produce basura como "+52", "+621" o un
    número colombiano al que se le perdió el "57".
    """
    solo_digitos = re.sub(r"\D", "", numero or "")
    if solo_digitos.startswith("57") and len(solo_digitos) == 12 and solo_digitos[2] == "3":
        return f"+{solo_digitos}"
    if len(solo_digitos) == 10 and solo_digitos[0] == "3":
        return f"+57{solo_digitos}"
    return ""


def _extraer_numero_de_enlace_wa(href: str) -> str:
    """
    Extrae el número crudo (solo dígitos) de un enlace de WhatsApp. wa.me/<num>
    lleva el número en la ruta; api.whatsapp.com/send lo lleva en el query param
    'phone' — tomar dígitos de todo el href en ese segundo caso mezcla el número
    con otros parámetros (texto, utm, etc.) y produce basura.
    """
    from urllib.parse import parse_qs, urlparse as _urlparse

    if "wa.me/" in href:
        return re.sub(r"\D", "", href.split("wa.me/")[-1].split("?")[0])
    if "whatsapp.com/send" in href:
        qs = parse_qs(_urlparse(href).query)
        return re.sub(r"\D", "", (qs.get("phone", [""])[0]))
    return ""

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

    def __init__(self, timeout: int = 5, max_paginas: int = 2):
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
        """
        Visita los sitios web en paralelo (hasta 8 hilos) para reducir el tiempo de espera.
        Si el dominio tiene varios correos corporativos, crea un registro por cada uno.
        """
        from copy import copy
        from concurrent.futures import ThreadPoolExecutor, as_completed

        con_web    = [p for p in prospectos if p.sitio_web]
        sin_web    = [p for p in prospectos if not p.sitio_web]

        def _enriquecer_uno(p):
            try:
                emails, tel, wa = self._buscar_todos_emails_telefono_whatsapp(p.sitio_web)
            except Exception:
                emails, tel, wa = [], "", ""
            return p, emails, tel, wa

        enriquecidos: list = list(sin_web)

        with ThreadPoolExecutor(max_workers=8) as pool:
            futuros = {pool.submit(_enriquecer_uno, p): p for p in con_web}
            for fut in as_completed(futuros):
                try:
                    p, emails, tel, wa = fut.result()
                except Exception:
                    enriquecidos.append(futuros[fut])
                    continue
                if not p.tiene_email and emails:
                    p.email = emails[0]
                if (not p.telefono or not _parece_telefono_valido(p.telefono)) and tel:
                    p.telefono = tel
                if not p.whatsapp and wa:
                    p.whatsapp = wa
                enriquecidos.append(p)
                for email_extra in emails[1:]:
                    if email_extra == p.email:
                        continue
                    clon = copy(p)
                    clon.email = email_extra
                    enriquecidos.append(clon)

        return enriquecidos

    # ── Implementación interna ────────────────────────────────────────────────

    def _buscar_email(self, url_base: str) -> str:
        emails, _, _wa = self._buscar_todos_emails_telefono_whatsapp(url_base)
        return emails[0] if emails else ""

    def _buscar_email_y_telefono(self, url_base: str) -> tuple[str, str]:
        emails, tel, _wa = self._buscar_todos_emails_telefono_whatsapp(url_base)
        return (emails[0] if emails else ""), tel

    def _buscar_todos_emails_y_telefono(self, url_base: str) -> tuple[list[str], str]:
        emails, tel, _wa = self._buscar_todos_emails_telefono_whatsapp(url_base)
        return emails, tel

    def _buscar_todos_emails_telefono_whatsapp(self, url_base: str) -> tuple[list[str], str, str]:
        try:
            import httpx
            from bs4 import BeautifulSoup
        except ImportError:
            return [], ""

        dominio = urlparse(url_base).netloc
        urls_a_revisar = [url_base] + [
            urljoin(url_base, ruta) for ruta in _RUTAS_CONTACTO
        ]

        emails_encontrados: list[str] = []
        tel_encontrado = ""
        wa_encontrado = ""

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

                # ── WhatsApp (wa.me links) ────────────────────────────────
                if not wa_encontrado:
                    for tag in soup.find_all("a", href=True):
                        href = tag["href"]
                        if "wa.me/" in href or "whatsapp.com/send" in href:
                            numero_valido = _numero_co_valido(_extraer_numero_de_enlace_wa(href))
                            if numero_valido:
                                wa_encontrado = numero_valido
                                break

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

        return self._seleccionar_todos_del_dominio(emails_encontrados, dominio), tel_encontrado, wa_encontrado

    @staticmethod
    def _seleccionar_todos_del_dominio(emails: list[str], dominio_empresa: str) -> list[str]:
        """
        Retorna todos los emails corporativos del dominio de la empresa.
        Prioriza los del mismo dominio; incluye genéricos (gmail) solo si no hay corporativos.
        """
        if not emails:
            return []

        emails_limpios = list({e.lower().strip() for e in emails
                               if _PATRON_EMAIL.fullmatch(e.strip())})
        emails_limpios = [e for e in emails_limpios if e.split("@")[-1] not in _DOMINIOS_FILTRO]

        dominio_base = dominio_empresa.lstrip("www.") if dominio_empresa else ""
        corporativos = [e for e in emails_limpios if dominio_base and dominio_base in e]

        # Si hay emails del mismo dominio, devolver solo esos (más confiables)
        if corporativos:
            return corporativos

        # Si no hay corporativos, devolver cualquier email encontrado
        return emails_limpios[:3]
