"""
ContentGeneratorService — genera artículos SST diarios usando la API de Claude.

Optimizaciones de costo aplicadas:
  · Prompt caching ephemeral en el system prompt (se reutiliza por 5 minutos,
    ahorra ~90% del costo de tokens de entrada en llamadas repetidas del mismo día)
  · Modelo recomendado: claude-sonnet-4-6 (mejor balance calidad/costo)
"""
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import anthropic

from ...config import get_config
from .topics import TemaSSTInfo, obtener_tema_del_dia

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

RESPONDE ÚNICAMENTE con un objeto JSON válido, sin texto adicional antes ni después:
{
  "titulo": "Título SEO optimizado (60-70 caracteres)",
  "cuerpo": "Artículo completo en Markdown (500-700 palabras, usa ## para subtítulos)",
  "copy_linkedin": "Copy para LinkedIn (150-200 palabras, profesional, con emoji moderado)",
  "copy_facebook": "Copy para Facebook (100-130 palabras, más directo y emocional)",
  "copy_instagram": "Copy para Instagram (80-100 palabras, impactante, visual en descripción)",
  "hashtags": ["#SST", "#SeguridadLaboral", "..."] (exactamente 8 hashtags relevantes),
  "cta": "Llamado a la acción único para Medina SST Empresarial SAS (1-2 oraciones)",
  "prompts_imagenes": [
    "Detailed image prompt in English for image 1 (professional corporate setting, Colombian office)",
    "Detailed image prompt in English for image 2 (infographic style, data visualization on safety)",
    "Detailed image prompt in English for image 3 (people at work, safety awareness, Latin American context)"
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
    cache_hit: bool = False

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

    MODEL = "claude-sonnet-4-6"
    MAX_TOKENS = 4096

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY no definida. Añádela al archivo .env"
            )
        self._client = anthropic.Anthropic(api_key=key)
        self._output_dir = get_config().output_dir / "contenido" / "articulos"

    def generar(self, tema: Optional[TemaSSTInfo] = None, dia: Optional[date] = None) -> ArticuloGenerado:
        """
        Genera el artículo del día.
        Si no se especifica tema, usa la rotación automática por día del año.
        """
        tema_activo = tema or obtener_tema_del_dia(dia)
        user_prompt = self._construir_prompt_usuario(tema_activo)

        response = self._client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    # Cache el system prompt: ahorra ~90% de tokens de entrada en
                    # llamadas repetidas del mismo día (TTL 5 minutos por defecto)
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text
        articulo = self._parsear_respuesta(raw_text, tema_activo)

        # Enriquecer con métricas de uso
        articulo.tokens_entrada = response.usage.input_tokens
        articulo.tokens_salida = response.usage.output_tokens
        articulo.cache_hit = getattr(response.usage, "cache_read_input_tokens", 0) > 0

        self._persistir_json(articulo)
        return articulo

    def _construir_prompt_usuario(self, tema: TemaSSTInfo) -> str:
        cfg = get_config()
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
            "Recuerda: responde ÚNICAMENTE con el objeto JSON, sin texto adicional."
        )

    def _parsear_respuesta(self, raw: str, tema: TemaSSTInfo) -> ArticuloGenerado:
        try:
            # Extraer bloque JSON aunque Claude añada texto envolvente
            match = re.search(r"\{[\s\S]*\}", raw)
            data = json.loads(match.group() if match else raw)
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
