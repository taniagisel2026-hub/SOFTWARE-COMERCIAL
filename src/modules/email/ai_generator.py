"""
Genera introducciones de correo únicas e impactantes con Gemini Flash.
Cada correo abre con un gancho específico al sector/riesgo de la empresa
para despertar interés real y evitar filtros de spam semántico.
Retorna None si Gemini falla tras 2 intentos — el llamador usa el fallback.
"""
import os
import time
from typing import Optional

_DOLORES_SECTOR: dict[str, str] = {
    "Construcción":             "accidentes en alturas, derrumbes y maquinaria pesada que cada año generan las multas más altas del sector",
    "Manufactura / Industria":  "ruido industrial, polvos y riesgos mecánicos que silenciosamente destruyen la salud de los trabajadores",
    "Transporte y Logística":   "accidentes viales y fatiga de conductores — el sector con más muertes laborales en Colombia",
    "Comercio y Retail":        "caídas, lesiones ergonómicas y estrés laboral que disparan las incapacidades y reducen la productividad",
    "Servicios Empresariales":  "riesgo psicosocial y burnout que hoy son la primera causa de ausentismo laboral en Colombia",
    "Salud y Clínicas":         "exposición a agentes biológicos y violencia laboral — el sector con mayor subregistro de accidentes",
    "Educación":                "sobrecarga laboral docente y riesgos psicosociales que el Ministerio del Trabajo está fiscalizando activamente",
    "Agricultura y Ganadería":  "plaguicidas, golpes de calor y herramientas cortopunzantes en zonas donde la inspección del Mintrabajo está aumentando",
    "Minería y Energía":        "explosiones, espacios confinados y gases tóxicos — el sector con las multas más severas del Decreto 472",
    "Tecnología y Software":    "burnout y lesiones por sedentarismo que ya son reconocidas como enfermedad laboral en Colombia",
    "Alimentos y Bebidas":      "calor extremo, riesgos biológicos y trabajo repetitivo que disparan las enfermedades laborales",
    "Seguridad Privada":        "jornadas extenuantes, agresiones y fatiga crónica en el sector con mayor rotación por accidentes laborales",
    "Ingeniería y Consultoría": "trabajo en campo y riesgo en alturas donde un solo accidente puede paralizar toda la operación",
    "Petróleo y Gas":           "espacios confinados, fugas de gas y alto riesgo eléctrico — donde las multas del Mintrabajo son de las más altas del país",
}

_PROMPTS: dict[str, str] = {

    "PRIMER_CONTACTO": """\
Eres {nombre_asesora}, asesora SST de {empresa_remitente} (Colombia).
Escribe 2 párrafos HTML cortos para un correo a {razon_social} ({sector}, {ciudad}).
Datos: {num_empleados} empleados, Riesgo ARL Clase {nivel_riesgo}, \
{num_estandares} estándares ({articulo_resolucion} Res. 0312/2019).
Riesgo real del sector: {dolor}.

Párrafo 1 — GANCHO: una sola oración que sorprenda. Puede ser una pregunta retórica \
o un dato concreto sobre el riesgo de {sector}. NO empieces con "Estimado" ni el nombre de la empresa.
Párrafo 2 — CONTEXTO + CTA: 2-3 oraciones. Menciona los {num_estandares} estándares, \
el riesgo de multa (Decreto 472/2015), y termina preguntando si pueden hablar 15 minutos.
Preséntate como {nombre_asesora} de {empresa_remitente} en este párrafo.

Reglas: máx 90 palabras. Tono directo y humano. Solo etiquetas <p> y <strong>. \
Sin lista de servicios ni datos de contacto.""",

    "SEGUIMIENTO_COTIZACION": """\
Eres {nombre_asesora}, asesora SST de {empresa_remitente} (Colombia).
Escribe 2 párrafos HTML para seguimiento a {razon_social} ({sector}, Riesgo {nivel_riesgo}).

Párrafo 1: menciona naturalmente que ya les escribiste antes. \
Conecta con el riesgo real: {dolor}.
Párrafo 2: ofrece resolver una duda específica. Pregunta si tienen 15 minutos esta semana.

Máx 70 palabras. Solo <p> y <strong>. Sin firma ni lista de servicios.""",

    "RECORDATORIO_VENCIMIENTO": """\
Eres {nombre_asesora}, asesora SST de {empresa_remitente} (Colombia).
Escribe 2 párrafos HTML de urgencia para {razon_social} ({sector}, Riesgo {nivel_riesgo}, \
{num_estandares} estándares Res. 0312/2019).
Riesgo del sector: {dolor}.

Párrafo 1: un riesgo concreto que puede ocurrirle a {razon_social} sin el SG-SST al día \
(multa Decreto 472/2015, inspección, accidente).
Párrafo 2: ofrece ayudarles a cumplir los {num_estandares} estándares. \
Cierra con una pregunta directa de cierre.

Máx 80 palabras. Ángulo diferente al primer correo. Solo <p> y <strong>. \
Sin lista de servicios.""",
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
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 800},
    }

    for intento in range(2):
        try:
            import requests as _req
            r = _req.post(url, json=payload, timeout=60)
            r.raise_for_status()
            texto = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if len(texto) > 80:
                return texto
            print(f"[AI_GENERATOR] Respuesta demasiado corta ({len(texto)} chars), reintentando...")
        except Exception as e:
            print(f"[AI_GENERATOR] Intento {intento+1} fallido ({tipo}): {e}")
            if intento == 0:
                time.sleep(2)

    return None
