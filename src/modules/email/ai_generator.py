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
Eres {nombre_asesora}, asesora comercial de {empresa_remitente}, especialistas en \
Seguridad y Salud en el Trabajo (SST) en Colombia.

Escribe una introducción de correo de primer contacto para:
- Empresa: {razon_social} | Contacto: {nombre_contacto} | Ciudad: {ciudad}
- Sector: {sector} | Empleados: {num_empleados} | Riesgo ARL: Clase {nivel_riesgo}
- Obligación legal: {articulo_resolucion} de la Res. 0312/2019 = {num_estandares} estándares mínimos
- Riesgo del sector: {dolor}

OBJETIVO: que quien lo lea quiera saber más. Nada de presentaciones corporativas aburridas.

Estructura OBLIGATORIA (3 párrafos cortos):
1. GANCHO (1 oración impactante): abre con una pregunta o dato concreto sobre el riesgo \
específico de {razon_social} en el sector {sector}. No empieces con "Estimado" ni con el nombre \
de la empresa. Sorprende al lector desde la primera línea.
2. CONTEXTO LEGAL (2-3 oraciones): explica que empresas como {razon_social} con {num_empleados} \
trabajadores y riesgo ARL Clase {nivel_riesgo} deben cumplir exactamente {num_estandares} estándares \
según el {articulo_resolucion} de la Res. 0312/2019. Menciona el riesgo real de una multa \
(Decreto 472/2015, hasta 500 SMMLV) sin ser alarmista.
3. PROPUESTA (1-2 oraciones): preséntate como {nombre_asesora} de {empresa_remitente} y \
cierra con UNA pregunta directa que invite a responder.

Reglas:
- Máximo 120 palabras en total.
- Tono: directo, humano y consultivo. Como si hablaras con un colega, no con un desconocido.
- Nada de frases como "queremos presentar nuestros servicios" o "nos permitimos contactarlos".
- No incluyas lista de servicios (va aparte). No incluyas datos de contacto.
- Solo etiquetas <p> y <strong>. Sin HTML adicional.""",

    "SEGUIMIENTO_COTIZACION": """\
Eres {nombre_asesora}, asesora de {empresa_remitente}, SST Colombia.

Escribe el cuerpo de un correo de seguimiento para {razon_social} ({nombre_contacto}).
Sector: {sector}. Riesgo ARL Clase {nivel_riesgo}. Propuesta previa: {num_estandares} estándares.

OBJETIVO: recordar sin presionar. Abrir una conversación real.

Estructura:
1. Abre mencionando que ya les escribiste, de forma natural (no "le hago seguimiento a...").
2. Conecta con un dolor real del sector {sector}: {dolor}.
3. Ofrece resolver UNA duda específica. Cierra con disponibilidad para 15 minutos.

Máximo 80 palabras. Tono humano y directo. Solo <p> y <strong>.
No incluyas firma (va aparte).""",

    "RECORDATORIO_VENCIMIENTO": """\
Eres {nombre_asesora}, asesora de {empresa_remitente}, SST Colombia.

Escribe la introducción del tercer contacto (Día 8) para {razon_social} ({nombre_contacto}).
Sector: {sector}. Riesgo ARL Clase {nivel_riesgo}. Obligación: {num_estandares} estándares Res. 0312/2019.
Riesgo del sector: {dolor}.

OBJETIVO: generar urgencia real sin sonar a spam ni a amenaza.

Estructura (2 párrafos):
1. Abre con el riesgo específico del sector {sector} — algo concreto que les puede pasar \
si no tienen el SG-SST al día (inspección, accidente, multa Decreto 472/2015).
2. Recuerda que puedes ayudarles a cumplir los {num_estandares} estándares rápidamente. \
Cierra con una pregunta directa de cierre.

Máximo 100 palabras. Ángulo DIFERENTE al primer correo. Tono más directo.
No incluyas lista de servicios (va aparte). Solo <p> y <strong>.""",
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
