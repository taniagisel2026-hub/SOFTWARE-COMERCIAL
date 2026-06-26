"""
FacebookPagesClient — enriquece empresas del CRM con datos de Facebook Pages.

Usa la Graph API pública de Meta para buscar páginas de negocio y extraer
teléfono, email y web. Solo funciona con páginas públicas.

Token: guardar en credentials/facebook_token.json como {"access_token": "..."}
El token tipo App Access Token no expira: formato APP_ID|APP_SECRET
"""
import json
import re
import unicodedata
from pathlib import Path
from dataclasses import dataclass

import httpx

_BASE_URL = "https://graph.facebook.com/v19.0"
_FIELDS = "id,name,phone,emails,website,single_line_address"
_SUFIJOS = re.compile(
    r"\b(s\.?a\.?s\.?|s\.?a\.?|ltda\.?|e\.?u\.?|s\.?c\.?a\.?|"
    r"sociedad|empresa|grupo|compania|cia)\b",
    re.IGNORECASE,
)


@dataclass
class InfoFacebook:
    facebook_id: str
    nombre_pagina: str
    telefono: str = ""
    email: str = ""
    sitio_web: str = ""
    direccion: str = ""


class FacebookTokenError(Exception):
    pass


class FacebookPagesClient:

    def __init__(self, access_token: str):
        self._token = access_token

    @classmethod
    def from_config(cls) -> "FacebookPagesClient":
        token = cls._leer_token()
        if not token:
            raise FacebookTokenError(
                "FACEBOOK_ACCESS_TOKEN no está configurado en el archivo .env\n"
                "Agrega: FACEBOOK_ACCESS_TOKEN=APP_ID|APP_SECRET"
            )
        return cls(token)

    @classmethod
    def token_configurado(cls) -> bool:
        return bool(cls._leer_token())

    @classmethod
    def _leer_token(cls) -> str:
        import os
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent.parent.parent / ".env"
        load_dotenv(env_path, override=True)
        return os.getenv("FACEBOOK_ACCESS_TOKEN", "").strip()

    def buscar_empresa(self, razon_social: str, ciudad: str = "") -> InfoFacebook | None:
        """
        Busca la página de Facebook más relevante para la empresa.
        Retorna None si no encuentra coincidencia confiable.
        """
        query = f"{razon_social} {ciudad}".strip()
        try:
            resp = httpx.get(
                f"{_BASE_URL}/search",
                params={
                    "q":            query,
                    "type":         "page",
                    "fields":       _FIELDS,
                    "access_token": self._token,
                    "limit":        5,
                },
                timeout=10,
            )
            resp.raise_for_status()
            paginas = resp.json().get("data", [])
        except Exception:
            return None

        nombre_norm = _normalizar(razon_social)
        for pagina in paginas:
            nombre_fb = _normalizar(pagina.get("name", ""))
            if _coincide(nombre_norm, nombre_fb):
                return self._mapear(pagina)

        return None

    def enriquecer_lote(
        self,
        empresas: list[dict],
        callback=None,
    ) -> list[dict]:
        """
        Recibe lista de dicts con {id_empresa, razon_social, ciudad}.
        Retorna lista de dicts con los datos encontrados por empresa.
        """
        resultados = []
        for i, emp in enumerate(empresas):
            info = self.buscar_empresa(emp["razon_social"], emp.get("ciudad", ""))
            resultados.append({
                "id_empresa":    emp["id_empresa"],
                "razon_social":  emp["razon_social"],
                "encontrado":    info is not None,
                "telefono":      info.telefono if info else "",
                "email":         info.email if info else "",
                "sitio_web":     info.sitio_web if info else "",
                "nombre_pagina": info.nombre_pagina if info else "",
            })
            if callback:
                callback(i + 1, len(empresas), emp["razon_social"])
        return resultados

    @staticmethod
    def _mapear(pagina: dict) -> InfoFacebook:
        emails = pagina.get("emails", [])
        return InfoFacebook(
            facebook_id=   pagina.get("id", ""),
            nombre_pagina= pagina.get("name", ""),
            telefono=      pagina.get("phone", ""),
            email=         emails[0] if emails else "",
            sitio_web=     pagina.get("website", ""),
            direccion=     pagina.get("single_line_address", ""),
        )


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = _SUFIJOS.sub("", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _coincide(nombre_crm: str, nombre_fb: str) -> bool:
    if not nombre_crm or not nombre_fb:
        return False
    palabras_crm = set(nombre_crm.split())
    palabras_fb  = set(nombre_fb.split())
    palabras_crm.discard("")
    palabras_fb.discard("")
    if len(palabras_crm) == 0:
        return False
    comunes = palabras_crm & palabras_fb
    return len(comunes) / len(palabras_crm) >= 0.6
