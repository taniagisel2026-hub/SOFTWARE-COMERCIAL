"""
Detecta respuestas de prospectos en Gmail y actualiza HistorialInteracciones.
Requiere que gmail_client esté autenticado con scope gmail.readonly.
"""
from datetime import datetime, timedelta


def detectar_y_registrar_respuestas() -> tuple[int, str]:
    """
    Escanea Gmail por correos entrantes de prospectos conocidos.
    Marca su última interacción como RESPONDIDO en la BD.
    Retorna (cantidad_detectadas, mensaje).
    """
    try:
        from ..email.gmail_client import GmailClient
        client = GmailClient.from_config()
        respuestas = client.listar_respuestas(desde_dias=30)
    except Exception as exc:
        return 0, f"Error al acceder a Gmail: {exc}"

    if not respuestas:
        return 0, "No se encontraron respuestas nuevas."

    count = 0
    try:
        from ...database.connection import get_session
        from ...database.models import EmpresaProspecto, HistorialInteracciones

        with get_session() as session:
            for resp in respuestas:
                sender = resp.get("from_email", "").lower().strip()
                if not sender:
                    continue

                empresa = (
                    session.query(EmpresaProspecto)
                    .filter(EmpresaProspecto.email_contacto.ilike(f"%{sender}%"))
                    .first()
                )
                if not empresa:
                    continue

                # Actualizar última interacción EMAIL no respondida
                ultima = (
                    session.query(HistorialInteracciones)
                    .filter(
                        HistorialInteracciones.id_empresa == empresa.id_empresa,
                        HistorialInteracciones.canal == "EMAIL",
                        HistorialInteracciones.estado_respuesta.notin_(["RESPONDIDO"]),
                    )
                    .order_by(HistorialInteracciones.fecha_interaccion.desc())
                    .first()
                )
                if ultima:
                    ultima.estado_respuesta = "RESPONDIDO"
                    ts = resp.get("date", datetime.now().strftime("%Y-%m-%d %H:%M"))
                    notas = ultima.notas_seguimiento or ""
                    ultima.notas_seguimiento = f"{notas} | RESPUESTA:{ts}".lstrip(" |")
                    count += 1

    except Exception as exc:
        return count, f"BD actualizada parcialmente: {exc}"

    return count, f"{count} respuesta(s) detectadas y registradas en el CRM."
