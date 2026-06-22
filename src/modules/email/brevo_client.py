"""
Cliente Brevo (ex-Sendinblue) para envío de correos transaccionales.
Usa la API REST v3 de Brevo — no requiere OAuth ni credenciales de Gmail.
Documentación: https://developers.brevo.com/reference/sendtransacemail
"""
import os
from typing import Optional


class BrevoSendError(Exception):
    pass


class BrevoClient:

    _API_URL = "https://api.brevo.com/v3/smtp/email"

    def __init__(self, api_key: str, sender_name: str, sender_email: str):
        self._api_key = api_key
        self._sender_name = sender_name
        self._sender_email = sender_email

    @classmethod
    def from_env(cls) -> "BrevoClient":
        api_key = os.getenv("BREVO_API_KEY", "").strip()
        if not api_key:
            raise BrevoSendError("BREVO_API_KEY no está configurada en el archivo .env")
        sender_email = os.getenv("BREVO_SENDER_EMAIL", os.getenv("EMPRESA_EMAIL", "")).strip()
        sender_name = os.getenv("EMPRESA_NOMBRE", "Medina SST Empresarial SAS").strip()
        return cls(api_key=api_key, sender_name=sender_name, sender_email=sender_email)

    def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        plain_text: Optional[str] = None,
        reply_to: Optional[str] = None,
        to_name: str = "",
    ) -> str:
        """
        Envía un correo HTML vía Brevo.
        Retorna el messageId de Brevo.
        Lanza BrevoSendError si falla.
        """
        import requests as _req

        payload: dict = {
            "sender": {
                "name": self._sender_name,
                "email": self._sender_email,
            },
            "to": [{"email": to, "name": to_name or to}],
            "subject": subject,
            "htmlContent": html_body,
        }
        if plain_text:
            payload["textContent"] = plain_text
        if reply_to:
            payload["replyTo"] = {"email": reply_to}

        headers = {
            "api-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            r = _req.post(self._API_URL, json=payload, headers=headers, timeout=30)
            if r.status_code == 201:
                return r.json().get("messageId", "brevo-ok")
            raise BrevoSendError(
                f"Brevo respondió {r.status_code}: {r.text[:300]}"
            )
        except BrevoSendError:
            raise
        except Exception as e:
            raise BrevoSendError(f"Error de conexión con Brevo: {e}") from e
