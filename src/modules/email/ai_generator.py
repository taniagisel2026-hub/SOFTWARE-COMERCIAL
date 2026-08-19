"""
Genera introducciones de correo únicas e impactantes con Gemini Flash.
Cada correo abre con un gancho específico al sector/riesgo de la empresa
para despertar interés real y evitar filtros de spam semántico.
Retorna None si Gemini falla tras 2 intentos — el llamador usa el fallback.
"""
import os
import threading
import time
from typing import Optional

# Espaciado mínimo entre llamadas a Gemini para no chocar con el límite de
# solicitudes por minuto de la capa gratuita (429 Too Many Requests) cuando
# se envían varios correos seguidos (cadencia, envío masivo).
# 4.5s (~13/min) seguía superando el límite real de 10-15 RPM de la capa
# gratuita de gemini-2.5-flash y el 429 volvía a aparecer; 6.5s deja margen
# incluso en el escenario más estricto (10 RPM = 6s).
_INTERVALO_MIN_S = 6.5
_ultima_llamada_ts = 0.0
_lock = threading.Lock()


def _esperar_turno() -> None:
    global _ultima_llamada_ts
    with _lock:
        espera = _INTERVALO_MIN_S - (time.monotonic() - _ultima_llamada_ts)
        if espera > 0:
            time.sleep(espera)
        _ultima_llamada_ts = time.monotonic()

_DOLORES_SECTOR: dict[str, str] = {
    "Construcción":             "accidentes en alturas, derrumbes y maquinaria pesada que cada año generan las multas más altas del sector",
    "Manufactura / Industria":  "ruido industrial, polvos y riesgos mecánicos que silenciosamente destruyen la salud de los trabajadores",
    "Transporte y Logística":   "accidentes viales y fatiga de conductores — el sector con más muertes laborales en Colombia",
    "Comercio y Retail":        "caídas, lesiones ergonómicas y estrés laboral que disparan las incapacidades y reducen la productividad",
    "Servicios Empresariales":  "riesgo psicosocial y burnout que hoy son la primera causa de ausentismo laboral en Colombia",
    "Salud y Clínicas":         "exposición a agentes biológicos y violencia laboral — el sector con mayor subregistro de accidentes",
    "Hotelería y Turismo":      "caídas, esfuerzo físico y riesgo psicosocial en un sector donde el ausentismo dispara costos operativos sin que los gerentes lo vean venir",
    "Petróleo y Gas":           "espacios confinados, fugas de gas y alto riesgo eléctrico — donde las multas del Mintrabajo son de las más altas del país",
    "Ingeniería y Consultoría": "trabajo en campo y riesgo en alturas donde un solo accidente puede paralizar toda la operación",
    "Farmacéutico y Químico":   "exposición a sustancias químicas y agentes biológicos que generan enfermedades laborales silenciosas y costosas demandas",
    "Telecomunicaciones":       "trabajo en altura en antenas y torres donde los accidentes son graves y las sanciones del Mintrabajo inmediatas",
    "Entretenimiento y Eventos":"riesgo eléctrico, trabajo nocturno y esfuerzo físico extremo en un sector que el Mintrabajo está empezando a fiscalizar con fuerza",
    "Minería y Energía":        "explosiones, espacios confinados y gases tóxicos — el sector con las multas más severas del Decreto 472",
    "Tecnología y Software":    "burnout y lesiones por sedentarismo que ya son reconocidas como enfermedad laboral en Colombia",
    "Alimentos y Bebidas":      "calor extremo, riesgos biológicos y trabajo repetitivo que disparan las enfermedades laborales",
    "Seguridad Privada":        "jornadas extenuantes, agresiones y fatiga crónica en el sector con mayor rotación por accidentes laborales",
    "Ingeniería y Consultoría": "trabajo en campo y riesgo en alturas donde un solo accidente puede paralizar toda la operación",
    "Petróleo y Gas":           "espacios confinados, fugas de gas y alto riesgo eléctrico — donde las multas del Mintrabajo son de las más altas del país",
}

_PROMPTS: dict[str, str] = {

    "PRIMER_CONTACTO": """\
Escribe UNA sola oración de apertura para un correo a una empresa del sector {sector} en {ciudad}.
La frase debe despertar curiosidad genuina o aportar una idea útil. Puede ser una pregunta o una idea que
haga pensar. NO uses tono de amenaza ni menciones multas, sanciones, muertes o accidentes graves —
esto es un primer contacto, no un correo de urgencia.
NO inventes estadísticas, porcentajes ni cifras específicas (nada de "el X% de...") — no hay forma de
verificarlas y una cifra falsa en un primer correo es un riesgo real. Habla en términos generales.
NO empieces con "Estimado", "Hola", "Buenos días" ni el nombre de la empresa.
Ejemplo de tono: "Muchas empresas de {sector} creen que ya cumplen su SG-SST, pero les falta justo
el estándar que más revisan los auditores."
Contexto del sector (úsalo como trasfondo, no lo repitas literalmente ni en tono alarmista): {dolor}.
Solo escribe la oración. Sin HTML. Sin introducción. Sin explicación.""",

    "SEGUIMIENTO_COTIZACION": """\
Escribe UNA sola oración natural de seguimiento para {razon_social} en sector {sector}.
La frase debe mencionar que ya les escribiste antes y conectar con su riesgo: {dolor}.
Tono: humano y cercano. Sin presión. Sin HTML. Solo la oración.""",

    "RECORDATORIO_VENCIMIENTO": """\
Escribe UNA sola oración de seguimiento con algo de urgencia para una empresa de {sector} que aún
no ha implementado su SG-SST y no respondió al primer correo. Puede aludir a que el tiempo pasa o a
que conviene resolverlo pronto, sin mencionar multas, decretos ni cifras legales específicas —
eso ya se explicó en el primer correo, este es de seguimiento, no de amenaza.
Riesgo del sector: {dolor}.
Tono directo pero cordial. Sin HTML. Solo la oración. Ángulo diferente a "¿está preparado?".""",

    "ULTIMO_CONTACTO": """\
Escribe UNA sola oración de cierre para el último correo de seguimiento a una empresa del sector {sector}.
Debe sonar cordial y sin presión, dejando la puerta abierta sin insistir más.
Puedes aludir sutilmente al riesgo real del sector sin sonar alarmista: {dolor}.
NO empieces con "Estimado", "Hola", "Buenos días" ni el nombre de la empresa. NO digas literalmente "este es mi último correo".
Tono: cordial, breve, sin presión. Sin HTML. Solo la oración.""",
}


def generar_cuerpo_ia(
    tipo: str,
    razon_social: str,
    nombre_contacto: str,
    ciudad: str,
    departamento: str,
    sector: str,
    num_empleados: int,
    nivel_riesgo: str,
    articulo_resolucion: str,
    num_estandares: int,
    empresa_remitente: str,
    nombre_asesora: str = "Tania Peñaloza",
) -> Optional[str]:
    """
    Genera la introducción personalizada del correo con Gemini Flash.
    Reintenta una vez si hay error de conexión.
    Retorna None si falla — el llamador usa el texto de respaldo.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    prompt_tpl = _PROMPTS.get(tipo)
    if not prompt_tpl:
        return None

    dolor = _DOLORES_SECTOR.get(sector, "riesgos laborales que el Ministerio del Trabajo está fiscalizando activamente")
    contacto = nombre_contacto if nombre_contacto and nombre_contacto != "Gerente" else "equipo"

    prompt = prompt_tpl.format(
        empresa_remitente=empresa_remitente,
        razon_social=razon_social,
        nombre_contacto=contacto,
        ciudad=ciudad,
        departamento=departamento,
        sector=sector or "su sector",
        dolor=dolor,
        num_empleados=num_empleados,
        nivel_riesgo=nivel_riesgo,
        articulo_resolucion=articulo_resolucion,
        num_estandares=num_estandares,
        nombre_asesora=nombre_asesora,
    )

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 800,
            # gemini-2.5-flash gasta tokens de "pensamiento" interno que se
            # descuentan de maxOutputTokens; sin esto, el modelo consume casi
            # todo el presupuesto pensando y la oración final sale cortada.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    for intento in range(2):
        _esperar_turno()
        try:
            import requests as _req
            r = _req.post(url, json=payload, timeout=60)
            r.raise_for_status()
            texto = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Eliminar comillas que Gemini a veces añade alrededor de la oración
            texto = texto.strip('"').strip("'").strip()
            # La oración debe estar completa: terminar en puntuación final
            if len(texto) > 30 and texto[-1] in ".!?":
                return texto
            print(f"[AI_GENERATOR] Respuesta incompleta: '{texto[-30:]}' — reintentando...")
        except Exception as e:
            print(f"[AI_GENERATOR] Intento {intento+1} fallido ({tipo}): {e}")
            if intento == 0:
                # Un 429 significa que ya se agotó la cuota de la ventana actual;
                # reintentar a los 2s de un error normal solo lo vuelve a chocar.
                es_429 = getattr(getattr(e, "response", None), "status_code", None) == 429
                time.sleep(15 if es_429 else 2)
                continue
        if intento == 0:
            time.sleep(2)

    return None
