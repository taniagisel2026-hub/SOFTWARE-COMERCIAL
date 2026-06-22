"""
Genera introducciones de correo únicas con Gemini Flash (gratuito).
Analiza el sector y los riesgos específicos de cada empresa para que
ningún mensaje sea idéntico — evita filtros de spam semántico.
Retorna None si GEMINI_API_KEY no está configurado o la llamada falla,
activando el fallback a texto de respaldo en EmailTemplateEngine.
"""
import os
from typing import Optional

# Dolor principal en SST por sector económico colombiano
_DOLORES_SECTOR: dict[str, str] = {
    "Construcción":             "accidentes de trabajo en alturas, excavaciones y uso de maquinaria pesada",
    "Manufactura / Industria":  "exposición a ruido industrial, polvos y riesgos mecánicos",
    "Transporte y Logística":   "accidentes viales, fatiga de conductores y manejo manual de cargas",
    "Comercio y Retail":        "riesgos ergonómicos, caídas al mismo nivel y atención al público",
    "Servicios Empresariales":  "riesgos psicosociales, carga mental y postura sedentaria prolongada",
    "Salud y Clínicas":         "exposición a agentes biológicos, riesgo de pinchazos y violencia laboral",
    "Educación":                "riesgos psicosociales, carga laboral docente y lesiones músculo-esqueléticas",
    "Agricultura y Ganadería":  "exposición a plaguicidas, golpes de calor y herramientas cortopunzantes",
    "Minería y Energía":        "explosiones, derrumbes, exposición a gases tóxicos y alto riesgo eléctrico",
    "Tecnología y Software":    "síndrome de burnout, riesgos ergonómicos por sedentarismo y fatiga visual",
    "Alimentos y Bebidas":      "exposición a calor extremo, riesgos biológicos y trabajo altamente repetitivo",
    "Seguridad Privada":        "agresiones físicas, jornadas nocturnas y fatiga crónica por turnos rotativos",
    "Ingeniería y Consultoría": "trabajo en campo, riesgo en alturas y accidentes de desplazamiento",
    "Petróleo y Gas":           "explosiones, fugas de gas, espacios confinados y alto riesgo eléctrico",
}

_PROMPTS: dict[str, str] = {

    "PRIMER_CONTACTO": """\
Eres {nombre_asesora}, asesora comercial de {empresa_remitente}, consultoría especializada \
en Seguridad y Salud en el Trabajo (SST) en Colombia.

Escribe ÚNICAMENTE la introducción personalizada de un correo de primer contacto en frío para:
- Empresa destinataria: {razon_social}
- Nombre del contacto: {nombre_contacto}
- Ubicación: {ciudad}, {departamento}
- Sector económico: {sector}
- Dolor principal en SST del sector: {dolor}
- Número de trabajadores: {num_empleados}
- Nivel de riesgo ARL: Clase {nivel_riesgo}
- Obligación legal vigente: {articulo_resolucion} — {num_estandares} estándares mínimos (Resolución 0312 de 2019)

IMPORTANTE: No incluyas lista de servicios ni datos de contacto (se agregan automáticamente después).

Reglas obligatorias:
1. Máximo 3 párrafos, 150 palabras en total.
2. Abre con el nombre del contacto y preséntate como {nombre_asesora} de {empresa_remitente}.
3. En el primer párrafo menciona el dolor específico del sector de {razon_social}.
4. Cita los {num_estandares} estándares mínimos que les exige la Resolución 0312/2019.
5. Cierra con UNA sola pregunta consultiva que invite al diálogo.
6. Tono profesional y cercano, nunca alarmista ni invasivo.
7. Retorna ÚNICAMENTE etiquetas <p> y <strong>. Sin tablas, botones ni otros elementos.""",

    "SEGUIMIENTO_COTIZACION": """\
Eres {nombre_asesora}, asesora comercial de {empresa_remitente}, consultoría SST colombiana.

Escribe ÚNICAMENTE el cuerpo de un correo de seguimiento para:
- Empresa: {razon_social} — Contacto: {nombre_contacto}
- Sector: {sector} — Riesgo específico: {dolor}
- Propuesta enviada: {num_estandares} estándares SG-SST ({articulo_resolucion}, Res. 0312/2019)

IMPORTANTE: No incluyas firma ni datos de contacto (se agregan automáticamente).

Reglas obligatorias:
1. Máximo 100 palabras.
2. Preséntate como {nombre_asesora} al inicio.
3. Referencia la propuesta anterior de forma natural, sin ser insistente.
4. Ofrece resolver UNA duda concreta relacionada con el sector {sector}.
5. Cierra con disponibilidad para una llamada de 15 minutos.
6. Solo <p> y <strong>. Sin otros elementos HTML.""",

    "RECORDATORIO_VENCIMIENTO": """\
Eres {nombre_asesora}, asesora comercial de {empresa_remitente}, consultoría SST colombiana.

Escribe ÚNICAMENTE la introducción de un correo de seguimiento (Día 8) para:
- Empresa: {razon_social} — Contacto: {nombre_contacto}
- Sector: {sector} — Riesgo: {dolor}
- Obligación legal: {num_estandares} estándares Res. 0312/2019 ({articulo_resolucion})

IMPORTANTE: No incluyas lista de servicios ni datos de contacto (se agregan automáticamente).

Reglas obligatorias:
1. Máximo 2 párrafos, 100 palabras.
2. Preséntate como {nombre_asesora} y menciona que ya les escribiste antes.
3. Recuerda el riesgo legal de incumplimiento (Decreto 472 de 2015, multas hasta 500 SMMLV).
4. Usa un ángulo diferente al primer correo — enfócate en el riesgo específico del sector {sector}.
5. Tono urgente pero no alarmista.
6. Solo <p> y <strong>. Sin otros elementos HTML.""",
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
    Retorna None si no hay API key o si la llamada falla — el llamador
    usa el texto de respaldo estático.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    prompt_tpl = _PROMPTS.get(tipo)
    if not prompt_tpl:
        return None

    dolor = _DOLORES_SECTOR.get(sector, "riesgos laborales propios de su sector")

    prompt = prompt_tpl.format(
        empresa_remitente=empresa_remitente,
        razon_social=razon_social,
        nombre_contacto=nombre_contacto or "Gerente",
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

    try:
        import requests as _req
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        r = _req.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    except Exception:
        return None
