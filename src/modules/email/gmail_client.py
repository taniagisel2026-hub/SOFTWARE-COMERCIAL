"""
Cliente Gmail usando Google Workspace API v1 con autenticación OAuth2.

Configuración inicial (una sola vez):
  1. Google Cloud Console → APIs & Services → Enable Gmail API
  2. Credentials → Create OAuth 2.0 Client ID (Desktop app) → Descargar JSON
  3. Guardar como credentials/gmail_credentials.json en la raíz del proyecto
  4. Al ejecutar por primera vez, se abrirá el navegador para autorizar
     y se creará credentials/gmail_token.json automáticamente
"""
import base64
import email as _email_lib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


class GmailAuthError(Exception):
    pass


class GmailSendError(Exception):
    pass


class GmailClient:

    def __init__(self, credentials_path: Path, token_path: Path):
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._service = None

    @classmethod
    def from_config(cls) -> "GmailClient":
        from ...config import get_config
        root = get_config().output_dir.parent
        return cls(
            credentials_path=root / "credentials" / "gmail_credentials.json",
            token_path=root / "credentials" / "gmail_token.json",
        )

    def authenticate(self) -> None:
        """Realiza el flujo OAuth2. Abre el navegador en la primera ejecución."""
        creds: Optional[Credentials] = None

        if self._token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self._token_path), _SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self._credentials_path.exists():
                    raise GmailAuthError(
                        f"Credenciales no encontradas en: {self._credentials_path}\n"
                        "Instrucciones: Google Cloud Console → APIs & Services → "
                        "Credentials → OAuth 2.0 Client IDs → Download JSON"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self._credentials_path), _SCOPES
                )
                creds = flow.run_local_server(port=0)

            self._token_path.parent.mkdir(parents=True, exist_ok=True)
            self._token_path.write_text(creds.to_json(), encoding="utf-8")

        self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    def _obtener_firma(self) -> str:
        """Obtiene la firma HTML configurada en Gmail."""
        try:
            result = self._service.users().settings().sendAs().list(userId="me").execute()
            for alias in result.get("sendAs", []):
                sig = alias.get("signature", "")
                if sig:
                    sig = sig.replace('width:1342px', 'width:100%')
                    sig = sig.replace('align="left" style="text-align:left"', 'align="center" style="text-align:center"')
                    sig = sig.replace('margin:0px', 'margin:0px auto')
                    return f'<br>{sig}'
        except Exception:
            pass
        return ""

    def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        plain_text: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> str:
        """Envía un correo HTML con firma de Gmail. Retorna el ID de mensaje."""
        if self._service is None:
            self.authenticate()

        firma = self._obtener_firma()
        html_con_firma = html_body + firma

        msg = MIMEMultipart("alternative")
        msg["To"] = to
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to

        # Versión texto plano mejora entregabilidad ante filtros anti-spam
        if plain_text:
            msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_con_firma, "html", "utf-8"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        try:
            result = self._service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()
            return result["id"]
        except HttpError as exc:
            raise GmailSendError(f"Error enviando a {to}: {exc}") from exc

    def listar_respuestas(self, desde_dias: int = 30) -> list[dict]:
        """
        Busca correos entrantes (INBOX) en los últimos N días que provengan
        de direcciones que no sean el propio remitente (es decir, respuestas).
        Retorna lista de dicts con from_email, subject, date.
        """
        if self._service is None:
            self.authenticate()

        desde_dt = datetime.now() - timedelta(days=desde_dias)
        query = f"in:inbox after:{desde_dt.strftime('%Y/%m/%d')} -from:me"
        try:
            result = self._service.users().messages().list(
                userId="me", q=query, maxResults=100
            ).execute()
        except HttpError:
            return []

        mensajes = result.get("messages", [])
        respuestas = []
        for m in mensajes:
            try:
                msg = self._service.users().messages().get(
                    userId="me", id=m["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                ).execute()
                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                raw_from = headers.get("From", "")
                from_email = _email_lib.utils.parseaddr(raw_from)[1].lower()
                respuestas.append({
                    "from_email": from_email,
                    "subject":    headers.get("Subject", ""),
                    "date":       headers.get("Date", ""),
                })
            except HttpError:
                continue

        return respuestas
