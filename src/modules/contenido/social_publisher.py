"""
Publicadores de contenido en redes sociales.

Arquitectura de modo dual:
  · is_configured() → True  : publica automáticamente vía API
  · is_configured() → False : el sistema opera en modo manual (copiar y pegar)

Credenciales configuradas en .env — ver sección "Redes Sociales (OAuth2)".

APIs utilizadas:
  LinkedIn  : UGC Posts API v2  — https://docs.microsoft.com/linkedin/marketing/ugc-posts
  Facebook  : Meta Graph API v19 — https://developers.facebook.com/docs/pages
  Instagram : Meta Graph API v19 — https://developers.facebook.com/docs/instagram-api
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ResultadoPublicacion:
    plataforma: str
    ok: bool
    mensaje: str
    post_id: str = ""


# ── LinkedIn ──────────────────────────────────────────────────────────────────

class LinkedInPublisher:
    """
    Publica en una Página de empresa de LinkedIn.
    Requiere: LINKEDIN_ACCESS_TOKEN + LINKEDIN_ORGANIZATION_ID
    """
    _API = "https://api.linkedin.com/v2"

    def is_configured(self) -> bool:
        return bool(
            os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
            and os.getenv("LINKEDIN_ORGANIZATION_ID", "").strip()
        )

    def publicar(self, texto: str, imagen_url: str = "") -> ResultadoPublicacion:
        if not self.is_configured():
            return ResultadoPublicacion("LINKEDIN", False, "Credenciales no configuradas.")

        try:
            import httpx
            token  = os.getenv("LINKEDIN_ACCESS_TOKEN")
            org_id = os.getenv("LINKEDIN_ORGANIZATION_ID")

            body: dict = {
                "author": f"urn:li:organization:{org_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": texto[:3000]},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                },
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            }
            r = httpx.post(f"{self._API}/ugcPosts", json=body,
                           headers=headers, timeout=15)
            r.raise_for_status()
            post_id = r.headers.get("x-restli-id", "—")
            return ResultadoPublicacion("LINKEDIN", True,
                                        f"Publicado correctamente.", post_id)
        except Exception as exc:
            return ResultadoPublicacion("LINKEDIN", False, str(exc))


# ── Facebook ──────────────────────────────────────────────────────────────────

class FacebookPublisher:
    """
    Publica en una Página de Facebook.
    Requiere: META_PAGE_ACCESS_TOKEN + META_FACEBOOK_PAGE_ID
    """
    _API = "https://graph.facebook.com/v19.0"

    def is_configured(self) -> bool:
        return bool(
            os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
            and os.getenv("META_FACEBOOK_PAGE_ID", "").strip()
        )

    def publicar(self, texto: str, imagen_url: str = "") -> ResultadoPublicacion:
        if not self.is_configured():
            return ResultadoPublicacion("FACEBOOK", False, "Credenciales no configuradas.")

        try:
            import httpx
            token   = os.getenv("META_PAGE_ACCESS_TOKEN")
            page_id = os.getenv("META_FACEBOOK_PAGE_ID")
            params: dict = {"message": texto, "access_token": token}
            if imagen_url:
                params["link"] = imagen_url

            r = httpx.post(f"{self._API}/{page_id}/feed",
                           params=params, timeout=15)
            r.raise_for_status()
            post_id = r.json().get("id", "—")
            return ResultadoPublicacion("FACEBOOK", True,
                                        "Publicado correctamente.", post_id)
        except Exception as exc:
            return ResultadoPublicacion("FACEBOOK", False, str(exc))


# ── Instagram ─────────────────────────────────────────────────────────────────

class InstagramPublisher:
    """
    Publica en una cuenta de Instagram Business.
    Requiere: META_PAGE_ACCESS_TOKEN + META_INSTAGRAM_ACCOUNT_ID + imagen_url pública.

    Flujo de 2 pasos (API Meta):
      1. Crear contenedor de media  → devuelve container_id
      2. Publicar el contenedor     → devuelve media_id
    """
    _API = "https://graph.facebook.com/v19.0"

    def is_configured(self) -> bool:
        return bool(
            os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
            and os.getenv("META_INSTAGRAM_ACCOUNT_ID", "").strip()
        )

    def publicar(self, texto: str, imagen_url: str = "") -> ResultadoPublicacion:
        if not self.is_configured():
            return ResultadoPublicacion("INSTAGRAM", False, "Credenciales no configuradas.")
        if not imagen_url:
            return ResultadoPublicacion(
                "INSTAGRAM", False,
                "Instagram requiere una imagen con URL pública para publicar."
            )
        try:
            import httpx
            token = os.getenv("META_PAGE_ACCESS_TOKEN")
            ig_id = os.getenv("META_INSTAGRAM_ACCOUNT_ID")

            # Paso 1: contenedor
            r1 = httpx.post(
                f"{self._API}/{ig_id}/media",
                params={"image_url": imagen_url,
                        "caption": texto[:2200],
                        "access_token": token},
                timeout=20,
            )
            r1.raise_for_status()
            container_id = r1.json().get("id")
            if not container_id:
                return ResultadoPublicacion("INSTAGRAM", False,
                                            "No se obtuvo container_id.")

            # Paso 2: publicar
            r2 = httpx.post(
                f"{self._API}/{ig_id}/media_publish",
                params={"creation_id": container_id, "access_token": token},
                timeout=20,
            )
            r2.raise_for_status()
            media_id = r2.json().get("id", "—")
            return ResultadoPublicacion("INSTAGRAM", True,
                                        "Publicado correctamente.", media_id)
        except Exception as exc:
            return ResultadoPublicacion("INSTAGRAM", False, str(exc))


# ── Helper: estado global de configuración ────────────────────────────────────

def estado_plataformas() -> dict[str, bool]:
    """Retorna qué plataformas tienen credenciales configuradas."""
    return {
        "LINKEDIN":  LinkedInPublisher().is_configured(),
        "FACEBOOK":  FacebookPublisher().is_configured(),
        "INSTAGRAM": InstagramPublisher().is_configured(),
    }


def publicar_en_todas(
    texto_linkedin: str,
    texto_facebook: str,
    texto_instagram: str,
    imagen_url: str = "",
) -> list[ResultadoPublicacion]:
    """Dispara publicación en todas las plataformas configuradas."""
    resultados = []
    resultados.append(LinkedInPublisher().publicar(texto_linkedin, imagen_url))
    resultados.append(FacebookPublisher().publicar(texto_facebook, imagen_url))
    resultados.append(InstagramPublisher().publicar(texto_instagram, imagen_url))
    return resultados
