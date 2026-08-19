"""
Detecta respuestas de prospectos en Gmail y actualiza HistorialInteracciones.
Si la respuesta tiene intención negativa ("no me interesa", "ya contamos con
eso", etc.) activa el opt-out automáticamente para que la cadencia deje de
reenviarle correo a esa empresa (Ley 1581 de 2012, ver compliance.habeas_data).
Si tiene intención afirmativa ("SI", "me interesa", etc.) marca la empresa
como PIDIO_PORTAFOLIO para que aparezca lista en el panel (pestaña
Portafolio → "Pendientes de envío") con un solo clic para enviarle el
portafolio — la negativa siempre tiene prioridad sobre la afirmativa.
Requiere que gmail_client esté autenticado con scope gmail.readonly.
"""
import unicodedata
from datetime import date, datetime, timedelta

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



# Frases típicas de interés/aceptación. Solo se evalúan si NO hubo frase
# negativa (ver detectar_y_registrar_respuestas) para no confundir textos
# como "no me interesa", que contiene la sub-frase "me interesa".
_FRASES_AFIRMATIVAS = [
    "me interesa",
    "cuentenme mas",
    "cuenteme mas",
    "quiero informacion",
    "quiero mas informacion",
    "quiero la informacion",
    "envienme el portafolio",
    "envienme mas informacion",
    "manden el portafolio",
    "manden informacion",
    "claro que si",
    "si por favor",
    "si claro",
    "si quiero",
    "hablemos",
    "me gustaria conocer mas",
    "cuentame los detalles",
    "cuentenme los detalles",
]

# Respuestas muy cortas (≤6 palabras) que empiezan con una de estas palabras
# se toman como afirmación — es el caso más común, ya que el correo pide
# textualmente "responda con SI". No se busca "si" como sub-cadena en todo
# el texto porque es una palabra común en español como conjunción ("si tiene
# tiempo...") y generaría falsos positivos.
_PALABRAS_AFIRMATIVAS_INICIO = {"si", "sí", "ok", "dale", "claro", "listo", "perfecto", "vale", "excelente"}


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


def _detectar_afirmacion(subject: str, snippet: str) -> str | None:
    texto_completo = _normalizar(f"{subject} {snippet}")
    for frase in _FRASES_AFIRMATIVAS:
        if frase in texto_completo:
            return frase

    palabras = _normalizar(snippet).split()
    if palabras and len(palabras) <= 6:
        primera = palabras[0].strip(".,!¡¿?-")
        if primera in _PALABRAS_AFIRMATIVAS_INICIO:
            return primera
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

    # Estados desde los que es seguro pasar a PIDIO_PORTAFOLIO — no se
    # "retrocede" a una empresa que ya avanzó más en el embudo.
    _ESTADOS_PRE_PORTAFOLIO = {"NUEVO", "EN_SEGUIMIENTO"}

    count = 0
    opt_outs = 0
    portafolios = 0
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

                subject = resp.get("subject", "")
                snippet = resp.get("snippet", "")
                frase_neg = _detectar_frase_negativa(subject, snippet)
                frase_afirm = None if frase_neg else _detectar_afirmacion(subject, snippet)

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
                    if frase_neg:
                        etiqueta = f"RESPUESTA:{ts} (NEGATIVA:{frase_neg})"
                    elif frase_afirm:
                        etiqueta = f"RESPUESTA:{ts} (AFIRMATIVA:{frase_afirm})"
                    else:
                        etiqueta = f"RESPUESTA:{ts}"
                    ultima.notas_seguimiento = f"{notas} | {etiqueta}".lstrip(" |")
                    count += 1

                if frase_neg and not empresa.opt_out:
                    habeas.registrar_opt_out(
                        empresa.id_empresa,
                        motivo=f"Respuesta negativa detectada en correo: \"{frase_neg}\"",
                    )
                    opt_outs += 1
                elif frase_afirm and empresa.estado_prospecto in _ESTADOS_PRE_PORTAFOLIO:
                    empresa.estado_prospecto = "PIDIO_PORTAFOLIO"
                    empresa.fecha_ultima_actualizacion = date.today()
                    portafolios += 1

    except Exception as exc:
        return count, f"BD actualizada parcialmente: {exc}"

    mensaje = f"{count} respuesta(s) detectadas y registradas en el CRM."
    if opt_outs:
        mensaje += f" {opt_outs} marcada(s) como no interesada(s) — opt-out automático aplicado."
    if portafolios:
        mensaje += f" {portafolios} marcada(s) como \"pidió portafolio\" — listas para enviar en el panel."
    return count, mensaje
