"""
Detecta rebotes permanentes (bounces) en Gmail y marca la empresa correspondiente
como opt-out para que la cadencia deje de reenviarle correo a una dirección muerta.
Requiere que gmail_client esté autenticado con scope gmail.readonly.
"""
import base64
import re
from datetime import datetime, timedelta

_PATRON_FINAL_RECIPIENT = re.compile(r"Final-Recipient:\s*rfc822;\s*([^\s,]+)", re.IGNORECASE)


def _extraer_destinatario_rebotado(service, msg_id: str) -> str:
    """Busca el header 'Final-Recipient' dentro de la parte message/delivery-status."""
    full = service.users().messages().get(userId="me", id=msg_id, format="full").execute()

    def buscar(payload):
        data = payload.get("body", {}).get("data")
        if data:
            texto = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            m = _PATRON_FINAL_RECIPIENT.search(texto)
            if m:
                return m.group(1).strip().rstrip(">;")
        for part in payload.get("parts", []) or []:
            r = buscar(part)
            if r:
                return r
        return ""

    return buscar(full.get("payload", {}))


def detectar_y_marcar_rebotes(desde_dias: int = 30) -> tuple[int, str]:
    """
    Escanea Gmail por notificaciones de rebote (mailer-daemon / postmaster) y marca
    como opt-out (email inválido) a la empresa correspondiente, deteniendo la cadencia.
    Retorna (cantidad_marcadas, mensaje).
    """
    try:
        from ..email.gmail_client import GmailClient
        client = GmailClient.from_config()
        client.authenticate()
        service = client._service
    except Exception as exc:
        return 0, f"Error al acceder a Gmail: {exc}"

    desde_dt = datetime.now() - timedelta(days=desde_dias)
    query = (
        f"in:inbox after:{desde_dt.strftime('%Y/%m/%d')} "
        f"(from:mailer-daemon@googlemail.com OR from:postmaster)"
    )
    try:
        mensajes = []
        page_token = None
        while True:
            kwargs = {"userId": "me", "q": query, "maxResults": 500}
            if page_token:
                kwargs["pageToken"] = page_token
            result = service.users().messages().list(**kwargs).execute()
            mensajes.extend(result.get("messages", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break
    except Exception as exc:
        return 0, f"Error al listar rebotes: {exc}"

    if not mensajes:
        return 0, "No se encontraron rebotes."

    from ...database.connection import get_session
    from ...database.models import EmpresaProspecto
    from ..compliance.habeas_data import HabeasDataService

    habeas = HabeasDataService()
    count = 0
    procesados = set()

    for m in mensajes:
        try:
            destinatario = _extraer_destinatario_rebotado(service, m["id"])
        except Exception:
            continue
        if not destinatario:
            continue
        destinatario = destinatario.lower().strip()
        if destinatario in procesados:
            continue
        procesados.add(destinatario)

        id_empresa = None
        with get_session() as session:
            empresa = (
                session.query(EmpresaProspecto)
                .filter(EmpresaProspecto.email_contacto.ilike(destinatario))
                .first()
            )
            if empresa and not empresa.opt_out:
                id_empresa = empresa.id_empresa

        if id_empresa is None:
            continue

        habeas.registrar_opt_out(
            id_empresa,
            motivo=f"Rebote permanente detectado: {destinatario} no existe o rechaza el correo.",
        )
        count += 1

    return count, f"{count} empresa(s) marcadas como email inválido (rebote) y excluidas de la cadencia."
