"""
Tracking de aperturas de correo mediante pixel de 1x1.

Flujo:
  1. email_service genera un token antes de enviar con generar_token()
  2. El pixel se incrusta en el HTML con incrustar_pixel()
  3. El token se persiste en la BD con registrar_token()
  4. Al abrir el correo, el cliente de email carga la imagen del servidor
  5. El servidor de tracking llama marcar_apertura(token)
  6. El CRM actualiza estado_respuesta = "ABIERTO"

Para activar el tracking:
  Agregar en .env:  TRACKING_URL=https://tu-servidor.com
  El servidor debe manejar GET /pixel/{token} y llamar a marcar_apertura()
  (ver tracker_server.py para la implementación del servidor)
"""
import os
import uuid
from datetime import datetime
from typing import Optional


def generar_token() -> str:
    """Genera un token UUID único para rastrear la apertura de un correo."""
    return uuid.uuid4().hex


def html_pixel(token: str) -> str:
    """
    Retorna el tag HTML del pixel de tracking.
    Retorna cadena vacía si TRACKING_URL no está configurado.
    """
    url = os.getenv("TRACKING_URL", "").strip().rstrip("/")
    if not url:
        return ""
    return (
        f'<img src="{url}/pixel/{token}" '
        f'width="1" height="1" alt="" style="display:none;" />'
    )


def incrustar_pixel(html_body: str, token: str) -> str:
    """Añade el pixel de tracking justo antes de </body>."""
    pixel = html_pixel(token)
    if not pixel:
        return html_body
    if "</body>" in html_body:
        return html_body.replace("</body>", f"{pixel}\n</body>", 1)
    return html_body + pixel


def registrar_token(id_interaccion: int, token: str) -> None:
    """Persiste el token en el campo notas_seguimiento del historial."""
    try:
        from ...database.connection import get_session
        from ...database.models import HistorialInteracciones
        with get_session() as session:
            rec = session.get(HistorialInteracciones, id_interaccion)
            if rec:
                notas = rec.notas_seguimiento or ""
                rec.notas_seguimiento = f"{notas} | TRACK:{token}".lstrip(" |")
    except Exception:
        pass


def marcar_apertura(token: str) -> bool:
    """
    Busca la interacción por token y la marca como ABIERTO.
    No sobreescribe si ya fue marcada como RESPONDIDO.
    Retorna True si se actualizó correctamente.
    """
    try:
        from ...database.connection import get_session
        from ...database.models import HistorialInteracciones
        with get_session() as session:
            rec = (
                session.query(HistorialInteracciones)
                .filter(HistorialInteracciones.notas_seguimiento.like(f"%TRACK:{token}%"))
                .first()
            )
            if not rec:
                return False
            if rec.estado_respuesta == "RESPONDIDO":
                return True
            rec.estado_respuesta = "ABIERTO"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            rec.notas_seguimiento = (rec.notas_seguimiento or "") + f" | ABIERTO:{ts}"
            return True
    except Exception:
        return False


def obtener_token(notas_seguimiento: Optional[str]) -> Optional[str]:
    """Extrae el token de tracking de notas_seguimiento si existe."""
    if not notas_seguimiento or "TRACK:" not in notas_seguimiento:
        return None
    for part in notas_seguimiento.split("|"):
        p = part.strip()
        if p.startswith("TRACK:"):
            return p[6:].strip()
    return None
