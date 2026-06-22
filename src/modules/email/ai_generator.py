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
Escribe UNA sola oración de apertura impactante para un correo a una empresa del sector {sector} en {ciudad}.
La frase debe despertar curiosidad o generar urgencia. Puede ser una pregunta o un dato sorprendente.
NO empieces con "Estimado", "Hola", "Buenos días" ni el nombre de la empresa.
Ejemplos de tono: "¿Sabe cuántas empresas de {sector} reciben multas del Mintrabajo sin saberlo?"
Riesgo real del sector: {dolor}.
Solo escribe la oración. Sin HTML. Sin introducción. Sin explicación.""",

    "SEGUIMIENTO_COTIZACION": """\
Escribe UNA sola oración natural de seguimiento para {razon_social} en sector {sector}.
La frase debe mencionar que ya les escribiste antes y conectar con su riesgo: {dolor}.
Tono: humano y cercano. Sin presión. Sin HTML. Solo la oración.""",

    "RECORDATORIO_VENCIMIENTO": """\
Escribe UNA sola oración de urgencia para una empresa de {sector} que aún no ha implementado su SG-SST.
Menciona algo concreto que puede pasarles (inspección, accidente, multa Decreto 472/2015).
Riesgo del sector: {dolor}.
Tono directo. Sin HTML. Solo la oración. Ángulo diferente a "¿está preparado?".""",
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
            # Eliminar comillas que Gemini a veces añade alrededor de la oración
            texto = texto.strip('"').strip("'").strip()
            # La oración debe estar completa: terminar en puntuación final
            if len(texto) > 30 and texto[-1] in ".!?":
                return texto
            print(f"[AI_GENERATOR] Respuesta incompleta: '{texto[-30:]}' — reintentando...")
        except Exception as e:
            print(f"[AI_GENERATOR] Intento {intento+1} fallido ({tipo}): {e}")
        if intento == 0:
            time.sleep(2)

    return None
