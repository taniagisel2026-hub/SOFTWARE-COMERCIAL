"""
Genera cuerpos de correo únicos con Claude API.
Analiza el sector de la empresa y sus dolores específicos en SST
para que ningún mensaje sea idéntico a otro (anti-spam semántico).
Retorna None si ANTHROPIC_API_KEY no está configurado o la llamada falla,
activando el fallback a plantillas estáticas en EmailTemplateEngine.
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
Eres el redactor de correos corporativos de {empresa_remitente}, consultoría especializada \
en Seguridad y Salud en el Trabajo (SST) en Colombia.

Escribe el cuerpo HTML de un correo de primer contacto en frío para:
- Empresa destinataria: {razon_social}
- Nombre del contacto: {nombre_contacto}
- Ubicación: {ciudad}, {departamento}
- Sector económico: {sector}
- Dolor principal en SST del sector: {dolor}
- Número de trabajadores: {num_empleados}
- Nivel de riesgo ARL: Clase {nivel_riesgo}
- Obligación legal vigente: {articulo_resolucion} — {num_estandares} estándares mínimos (Resolución 0312 de 2019)

Reglas obligatorias:
1. Máximo 130 palabras de texto visible.
2. Abre directamente con el nombre del contacto.
3. En la primera oración menciona el dolor específico del sector.
4. Cita con exactitud los {num_estandares} estándares mínimos exigidos.
5. Cierra con UNA sola pregunta consultiva (no dos).
6. Tono profesional y consultivo, nunca alarmista ni invasivo.
7. Retorna ÚNICAMENTE etiquetas <p> y <strong>. Sin <html>, <body>, <head>, <table> ni ningún otro elemento.""",

    "SEGUIMIENTO_COTIZACION": """\
Eres el redactor de correos corporativos de {empresa_remitente}, consultoría SST colombiana.

Escribe el cuerpo HTML de un correo de seguimiento de cotización para:
- Empresa: {razon_social} — Contacto: {nombre_contacto}
- Sector: {sector} — Dolor: {dolor}
- Propuesta enviada: {num_estandares} estándares SG-SST ({articulo_resolucion}, Res. 0312/2019)

Reglas obligatorias:
1. Máximo 100 palabras.
2. Referencia la propuesta anterior de forma natural, sin ser insistente.
3. Ofrece resolver UNA duda concreta relacionada con el sector.
4. Cierra con disponibilidad para una llamada de 15 minutos.
5. Solo <p> y <strong>. Sin otros elementos HTML.""",

    "RECORDATORIO_VENCIMIENTO": """\
Eres el redactor de correos corporativos de {empresa_remitente}, consultoría SST colombiana.

Escribe el cuerpo HTML de un recordatorio de vencimiento de propuesta para:
- Empresa: {razon_social} — Contacto: {nombre_contacto}
- Sector: {sector}
- Obligación legal: {num_estandares} estándares Res. 0312/2019 ({articulo_resolucion})

Reglas obligatorias:
1. Máximo 90 palabras.
2. Menciona el riesgo legal de incumplimiento (Decreto 472 de 2015, multas hasta 500 SMMLV).
3. Tono urgente pero no alarmista.
4. Un solo CTA claro al final.
5. Solo <p> y <strong>. Sin otros elementos HTML.""",
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
) -> Optional[str]:
    """
    Genera el cuerpo HTML del correo con Claude Haiku (rápido y económico).
    Retorna None si no hay API key o si la llamada falla — el llamador
    debe hacer fallback a la plantilla estática correspondiente.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
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
    )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key, timeout=12.0)
        msg = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=450,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    except Exception:
        return None
