"""
ContentGeneratorService — genera artículos SST diarios usando la API de Gemini (gratuita).
Modelo: gemini-2.0-flash
"""
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from ...config import get_config
from .topics import TemaSSTInfo, obtener_tema_del_dia

# Estado persistido de qué imagen (1, 2 o 3) es la "infografía del día" — rota
# para no ser siempre la misma posición. Solo tiene sentido con generación
# manual (Canva/ChatGPT con texto real); con generadores automáticos como
# Pollinations esa imagen tendría el mismo problema de texto ilegible que las
# demás, porque siguen siendo modelos de IA sin control sobre el texto.
_ESTADO_INFOGRAFIA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "infografia_estado.json"


def _slot_infografia_hoy(dia: date | None = None) -> int:
    """Retorna 1, 2 o 3 — el número de imagen que hoy debe ser infografía.
    Rota un puesto por día calendario (1 -> 2 -> 3 -> 1 -> ...)."""
    target = dia or date.today()
    try:
        estado = json.loads(_ESTADO_INFOGRAFIA_PATH.read_text(encoding="utf-8"))
    except Exception:
        estado = {"fecha": None, "slot": 1}

    if estado.get("fecha") != target.isoformat():
        if estado.get("fecha") is not None:
            estado["slot"] = (estado.get("slot", 1) % 3) + 1
        estado["fecha"] = target.isoformat()
        _ESTADO_INFOGRAFIA_PATH.parent.mkdir(parents=True, exist_ok=True)
        _ESTADO_INFOGRAFIA_PATH.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")

    return estado["slot"]

# ── System prompt (se cachea — no modificar sin evaluar impacto de costo) ────

_SYSTEM_PROMPT = """Eres el redactor de contenido especializado de Medina SST Empresarial SAS, \
empresa colombiana líder en Seguridad y Salud en el Trabajo (SST). Tu misión es generar contenido \
técnico-educativo de alto valor para pequeñas y medianas empresas colombianas que necesitan cumplir \
la Resolución 0312 de 2019 del Ministerio del Trabajo.

CONTEXTO NORMATIVO VIGENTE:
- Resolución 0312/2019 Ministerio del Trabajo: estándares mínimos SG-SST
  · Art. 3: 7 estándares — hasta 10 trabajadores, Riesgo I/II/III
  · Art. 16: 21 estándares — 11 a 50 trabajadores, Riesgo I/II/III
  · Art. 27: 60 estándares — más de 50 trabajadores o Riesgo IV/V
- Decreto 472/2015: multas hasta 500 SMMLV por incumplimientos SST
- Ley 1562/2012: Sistema General de Riesgos Laborales (SGRL)
- GTC-45: guía para identificación de peligros y valoración de riesgos
- Ley 1581/2012: Habeas Data (protección de datos personales)

AUDIENCIA OBJETIVO:
- Gerentes y propietarios de PYMEs colombianas (5-200 empleados)
- Responsables de RRHH sin formación técnica en SST
- Sectores: construcción, manufactura, comercio, servicios, transporte
- Ciudades: Bogotá, Medellín, Cali, Barranquilla, Bucaramanga, Pereira, Cúcuta

DIRECTRICES DE ESTILO:
- Tono: profesional y cercano; explica lo técnico en lenguaje gerencial
- Artículo: 500-700 palabras, estructura clara con subtítulos
- Incluir cifras reales de la normativa (artículos, montos en SMMLV)
- Generar sentido de urgencia sin ser alarmista
- Cada pieza cierra con un llamado a la acción claro hacia Medina SST
- Usar emojis con moderación solo en copys de redes sociales
- Enfoque SEO en las tres redes (LinkedIn, Facebook, Instagram): incluir de forma
  natural las palabras clave del tema (ver "palabras_clave"), términos que un
  gerente de PYME buscaría (ej. "SG-SST Colombia", "Resolución 0312"), y usar los
  primeros renglones como gancho que resuma el tema para mejorar el posicionamiento
  y la vista previa en cada plataforma

RESPONDE ÚNICAMENTE con un objeto JSON válido, sin texto adicional antes ni después:
{
  "titulo": "Título SEO optimizado (60-70 caracteres)",
  "cuerpo": "Artículo completo en Markdown (500-700 palabras, usa ## para subtítulos)",
  "copy_linkedin": "Borrador corto de LinkedIn (150-200 palabras) — se reemplaza después por la versión larga, solo sirve de referencia de tono",
  "copy_facebook": "Copy para Facebook (100-130 palabras, más directo y emocional, enfoque SEO)",
  "copy_instagram": "Copy para Instagram (80-100 palabras, impactante, visual en descripción, enfoque SEO)",
  "hashtags": ["#SST", "#SeguridadLaboral", "..."] (exactamente 8 hashtags relevantes),
  "cta": "Llamado a la acción único para Medina SST Empresarial SAS (1-2 oraciones)",
  "prompts_imagenes": [
    "Prompt detallado en español para imagen 1 (entorno corporativo profesional, oficina colombiana; plano medio o amplio con el rostro y la postura como foco principal, manos relajadas o fuera de primer plano — los modelos de IA generan manos y dedos deformes en primeros planos, evitarlos)",
    "Prompt detallado en español para imagen 2 (escena o composición simbólica de seguridad industrial: cascos, chalecos, señalización, equipos de protección, entorno de trabajo; SIN texto, letras, números, pantallas, gráficos de datos, iconos de interfaz ni ningún tipo de escritura visible — los modelos de IA no pueden renderizar texto legible, usar solo imagen fotográfica o ilustrativa sin escritura)",
    "Prompt detallado en español para imagen 3 (personas trabajando con elementos de protección personal, contexto latinoamericano; plano medio o amplio, evitar primeros planos de manos y dedos por la misma razón que la imagen 1)"
  ]
}"""


@dataclass
class ArticuloGenerado:
    tema: TemaSSTInfo
    titulo: str
    cuerpo: str
    copy_linkedin: str
    copy_facebook: str
    copy_instagram: str
    hashtags: list[str]
    cta: str
    prompts_imagenes: list[str]
    fecha_generacion: date = field(default_factory=date.today)
    modelo_usado: str = "claude-sonnet-4-6"
    tokens_entrada: int = 0
    tokens_salida: int = 0
    cache_hit: bool = False  # no aplica con Gemini, se mantiene por compatibilidad

    @property
    def copy_combinado(self) -> str:
        """Copy unificado para plataformas no diferenciadas."""
        return self.copy_linkedin

    def to_dict(self) -> dict:
        return {
            "fecha": str(self.fecha_generacion),
            "tema_categoria": self.tema.categoria,
            "tema_titulo_base": self.tema.titulo_base,
            "titulo": self.titulo,
            "cuerpo": self.cuerpo,
            "copy_linkedin": self.copy_linkedin,
            "copy_facebook": self.copy_facebook,
            "copy_instagram": self.copy_instagram,
            "hashtags": self.hashtags,
            "cta": self.cta,
            "prompts_imagenes": self.prompts_imagenes,
            "modelo_usado": self.modelo_usado,
            "tokens_entrada": self.tokens_entrada,
            "tokens_salida": self.tokens_salida,
            "cache_hit": self.cache_hit,
        }


class ContentGeneratorService:

    # Modelo separado del que usan los correos (gemini-2.5-flash en .env)
    # gemini-1.5-flash fue retirado por Google (404) — se usa el alias "latest"
    # de la familia lite para que Google lo mantenga apuntando a un modelo
    # vigente sin que el código quede roto cuando retiren la versión actual.
    MODEL = "gemini-flash-lite-latest"
    _BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: Optional[str] = None):
        cfg = get_config()
        key = api_key or cfg.gemini_api_key
        if not key:
            raise EnvironmentError(
                "GEMINI_API_KEY no definida. Añádela al archivo .env"
            )
        self._api_key = key
        self._output_dir = cfg.output_dir / "contenido" / "articulos"

    def generar(self, tema: Optional[TemaSSTInfo] = None, dia: Optional[date] = None) -> ArticuloGenerado:
        """Genera el artículo del día con rotación automática de temas."""
        tema_activo = tema or obtener_tema_del_dia(dia)
        user_prompt = self._construir_prompt_usuario(tema_activo)
        raw_text = self._llamar_gemini(user_prompt)
        articulo = self._parsear_respuesta(raw_text, tema_activo)

        # El copy de LinkedIn (1500-1800 palabras) se genera en una llamada
        # aparte: pedirlo junto con el resto del JSON hacía que el modelo
        # recortara la extensión para "repartir" su esfuerzo entre todos los
        # campos. En una llamada dedicada sí respeta la extensión.
        articulo.copy_linkedin = self._generar_linkedin_largo(tema_activo, articulo.titulo)

        articulo.modelo_usado = os.getenv("GEMINI_CONTENT_MODEL", self.MODEL)
        self._persistir_json(articulo)
        return articulo

    def _generar_linkedin_largo(self, tema: TemaSSTInfo, titulo_articulo: str) -> str:
        """Genera el artículo largo de LinkedIn (1500-1800 palabras) en una llamada dedicada."""
        cfg = get_config()
        prompt = (
            f"Escribe un artículo largo de LinkedIn (formato 'LinkedIn Article') sobre:\n\n"
            f"**Tema:** {tema.titulo_base}\n"
            f"**Categoría:** {tema.categoria}\n"
            f"**Ángulo narrativo:** {tema.angulo_narrativo}\n"
            f"**Brief:** {tema.descripcion_brief}\n"
            f"**Palabras clave SEO a incluir de forma natural:** {', '.join(tema.palabras_clave)}\n"
            f"**Empresa que publica:** {cfg.empresa_nombre} (SST en Colombia)\n\n"
            "REQUISITO ESTRICTO DE EXTENSIÓN: el artículo debe tener entre 1500 y 1800 "
            "palabras. Desarrolla estas 6 secciones completas, cada una de 200-300 "
            "palabras, cada una con su propio subtítulo en Markdown (##):\n"
            "1. Gancho inicial y por qué el tema importa hoy para una PYME colombiana\n"
            "2. Contexto normativo detallado (artículos exactos, decretos, sanciones)\n"
            "3. Riesgos concretos de no actuar (ejemplos realistas del sector)\n"
            "4. Cómo abordarlo paso a paso (metodología, sin vender todavía)\n"
            "5. Un caso o escenario ilustrativo (hipotético, sin nombres reales)\n"
            "6. Cierre con llamado a la acción hacia la empresa\n\n"
            "Tono profesional y cercano, emojis con moderación. Responde ÚNICAMENTE "
            "con el texto del artículo en Markdown — sin JSON, sin comillas envolventes, "
            "sin texto adicional antes ni después."
        )
        model = os.getenv("GEMINI_CONTENT_MODEL", self.MODEL)
        url = f"{self._BASE_URL}/{model}:generateContent?key={self._api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.8, "maxOutputTokens": 16000},
        }
        import requests as _req
        r = _req.post(url, json=payload, timeout=90)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    def _llamar_gemini(self, user_prompt: str) -> str:
        import time
        import requests as _req

        # GEMINI_CONTENT_MODEL permite sobrescribir el modelo solo para contenido
        # sin afectar el gemini-2.5-flash que usan los correos (GEMINI_MODEL)
        model = os.getenv("GEMINI_CONTENT_MODEL", self.MODEL)
        url = f"{self._BASE_URL}/{model}:generateContent?key={self._api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            # 8192 se quedaba corto con el copy de LinkedIn de ~1500 palabras
            "generationConfig": {"temperature": 0.8, "maxOutputTokens": 16000},
        }

        esperas = [30, 60]  # segundos entre reintentos
        for intento, espera in enumerate(esperas + [None], start=1):
            r = _req.post(url, json=payload, timeout=60)
            if r.status_code == 429 and espera is not None:
                time.sleep(espera)
                continue
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]

    def _construir_prompt_usuario(self, tema: TemaSSTInfo) -> str:
        cfg = get_config()
        slot_info = _slot_infografia_hoy()
        return (
            f"Genera contenido completo sobre el siguiente tema SST:\n\n"
            f"**Categoría:** {tema.categoria}\n"
            f"**Título base:** {tema.titulo_base}\n"
            f"**Ángulo narrativo:** {tema.angulo_narrativo}\n"
            f"**Brief:** {tema.descripcion_brief}\n"
            f"**Palabras clave a incluir:** {', '.join(tema.palabras_clave)}\n\n"
            f"**Empresa que publica:** {cfg.empresa_nombre}\n"
            f"**Email de contacto:** {cfg.empresa_email}\n"
            f"**Fecha de publicación:** {date.today().strftime('%d de %B de %Y')}\n\n"
            f"**Instrucción especial para prompts_imagenes:** la imagen número "
            f"{slot_info} de las 3 debe describirse como una INFOGRAFÍA (no una "
            f"foto): incluye 2-4 cifras o datos concretos y reales de este tema "
            f"(artículos de la normativa, porcentajes, montos en SMMLV, etc.) que "
            f"deban aparecer como texto en la infografía, y describe un diseño "
            f"visual claro con esos datos — esta se crea manualmente en Canva "
            f"con texto real, no lo genera una IA de imágenes, así que SÍ puede "
            f"pedir texto/cifras visibles. Las otras 2 imágenes (no la "
            f"{slot_info}) deben seguir siendo fotográficas, sin texto y evitando "
            f"primeros planos de manos, como siempre.\n\n"
            "Recuerda: responde ÚNICAMENTE con el objeto JSON, sin texto adicional."
        )

    def _parsear_respuesta(self, raw: str, tema: TemaSSTInfo) -> ArticuloGenerado:
        try:
            # Quitar bloques de código markdown si Gemini los incluye
            texto = re.sub(r"```(?:json)?\s*", "", raw).strip()
            match = re.search(r"\{[\s\S]*\}", texto)
            data = json.loads(match.group() if match else texto)
        except (json.JSONDecodeError, AttributeError):
            # Fallback: construir estructura mínima si el JSON viene malformado
            data = {
                "titulo": tema.titulo_base,
                "cuerpo": raw,
                "copy_linkedin": raw[:300],
                "copy_facebook": raw[:200],
                "copy_instagram": raw[:150],
                "hashtags": ["#SST", "#SeguridadLaboral", "#Colombia", "#Resolución0312"],
                "cta": f"Contáctanos en {get_config().empresa_email}",
                "prompts_imagenes": [
                    "Professional Colombian office safety meeting, corporate setting",
                    "Infographic about workplace safety regulations in Colombia",
                    "Latin American workers with safety equipment, construction site",
                ],
            }

        return ArticuloGenerado(
            tema=tema,
            titulo=data.get("titulo", tema.titulo_base),
            cuerpo=data.get("cuerpo", ""),
            copy_linkedin=data.get("copy_linkedin", ""),
            copy_facebook=data.get("copy_facebook", ""),
            copy_instagram=data.get("copy_instagram", ""),
            hashtags=data.get("hashtags", []),
            cta=data.get("cta", ""),
            prompts_imagenes=data.get("prompts_imagenes", [])[:3],
        )

    def _persistir_json(self, articulo: ArticuloGenerado) -> Path:
        """Guarda el artículo en disco para trazabilidad y re-uso."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", articulo.titulo.lower())[:50]
        path = self._output_dir / f"{articulo.fecha_generacion}_{slug}.json"
        path.write_text(
            json.dumps(articulo.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path
