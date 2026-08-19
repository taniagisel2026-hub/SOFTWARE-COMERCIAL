"""
Detecta respuestas de prospectos en Gmail y actualiza HistorialInteracciones.
Si la respuesta tiene intención negativa ("no me interesa", "ya contamos con
eso", etc.) activa el opt-out automáticamente para que la cadencia deje de
reenviarle correo a esa empresa (Ley 1581 de 2012, ver compliance.habeas_data).
Requiere que gmail_client esté autenticado con scope gmail.readonly.
"""
import unicodedata
from datetime import datetime, timedelta

# Frases típicas de rechazo en respuestas de prospectos colombianos.
# Se comparan en minúsculas y sin tildes (ver _normalizar).
_FRASES_NEGATIVAS = [
    "no me interesa",
    "no nos interesa",
    "no estamos interesados",
    "no esta interesado",
    "no estoy interesado",
    "no gracias",
    "no, gracias",
    "ya contamos con",
    "ya tenemos proveedor",
    "ya tenemos quien nos preste",
    "ya tenemos ese servicio",
    "ya tenemos este servicio",
    "ya contratamos",
    "no requerimos",
    "no necesitamos este servicio",
    "no necesitamos el servicio",
    "quitenme de la lista",
    "sacame de la lista",
    "saquenme de la lista",
    "no deseo recibir",
    "no deseamos recibir",
    "no enviar mas correos",
    "no envien mas correos",
    "dejen de enviarme",
    "dejen de escribirme",
    "no volver a contactar",
    "no vuelvan a contactar",
    "no contactar de nuevo",
    "eliminen mi correo",
    "remuevan mi correo",
    "unsubscribe",
]


def _normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def _detectar_frase_negativa(subject: str, snippet: str) -> str | None:
    texto = _normalizar(f"{subject} {snippet}")
    for frase in _FRASES_NEGATIVAS:
        if frase in texto:
            return frase
    return None


def detectar_y_registrar_respuestas() -> tuple[int, str]:
    """
    Escanea Gmail por correos entrantes de prospectos conocidos.
    Marca su última interacción como RESPONDIDO en la BD y, si detecta
    intención negativa, activa el opt-out automático (frena la cadencia).
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
    opt_outs = 0
    try:
        from ...database.connection import get_session
        from ...database.models import EmpresaProspecto, HistorialInteracciones
        from ..compliance.habeas_data import HabeasDataService

        habeas = HabeasDataService()

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

                frase = _detectar_frase_negativa(
                    resp.get("subject", ""), resp.get("snippet", "")
                )

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
                    etiqueta = f"RESPUESTA:{ts}" + (f" (NEGATIVA:{frase})" if frase else "")
                    ultima.notas_seguimiento = f"{notas} | {etiqueta}".lstrip(" |")
                    count += 1

                if frase and not empresa.opt_out:
                    habeas.registrar_opt_out(
                        empresa.id_empresa,
                        motivo=f"Respuesta negativa detectada en correo: \"{frase}\"",
                    )
                    opt_outs += 1

    except Exception as exc:
        return count, f"BD actualizada parcialmente: {exc}"

    mensaje = f"{count} respuesta(s) detectadas y registradas en el CRM."
    if opt_outs:
        mensaje += f" {opt_outs} marcada(s) como no interesada(s) — opt-out automático aplicado."
    return count, mensaje
