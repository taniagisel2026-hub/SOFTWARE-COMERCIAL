"""
Abstracción del cliente de WhatsApp Business.

Implementación actual: Twilio API for WhatsApp (más rápido de activar en Colombia).
Para migrar a Meta Cloud API implementar MetaWhatsAppClient con la misma interfaz.

Configuración Twilio:
  1. Crear cuenta en twilio.com
  2. Activar sandbox de WhatsApp (o número aprobado para producción)
  3. Añadir al .env: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WA_NUMBER
"""
import os
from abc import ABC, abstractmethod


class WhatsAppSendError(Exception):
    pass


class BaseWhatsAppClient(ABC):

    @abstractmethod
    def send_message(self, to_number: str, body: str) -> str:
        """Envía un mensaje de texto. Retorna el SID/ID del mensaje enviado."""
        ...


class TwilioWhatsAppClient(BaseWhatsAppClient):
    """
    Implementación sobre Twilio API for WhatsApp.
    Requiere: pip install twilio
    """

    def __init__(
        self,
        account_sid: str | None = None,
        auth_token: str | None = None,
        from_number: str | None = None,
    ):
        self._sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID", "")
        self._token = auth_token or os.getenv("TWILIO_AUTH_TOKEN", "")
        self._from = from_number or os.getenv("TWILIO_WA_NUMBER", "")

        if not all([self._sid, self._token, self._from]):
            raise EnvironmentError(
                "Faltan credenciales de Twilio. Define en .env:\n"
                "  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WA_NUMBER"
            )

    def send_message(self, to_number: str, body: str) -> str:
        try:
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioRestException
        except ImportError as exc:
            raise ImportError("Instala twilio: pip install twilio") from exc

        client = Client(self._sid, self._token)
        try:
            msg = client.messages.create(
                from_=f"whatsapp:{self._from}",
                body=body,
                to=f"whatsapp:{to_number}",
            )
            return msg.sid
        except Exception as exc:
            raise WhatsAppSendError(f"Error enviando WhatsApp a {to_number}: {exc}") from exc

    @classmethod
    def from_env(cls) -> "TwilioWhatsAppClient":
        return cls()
