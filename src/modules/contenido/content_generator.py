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
    "Prompt detallado en español para imagen 1 (entorno corporativo profesional, oficina colombiana)",
    "Prompt detallado en español para imagen 2 (estilo infografía en español, visualización de datos de seguridad)",
    "Prompt detallado en español para imagen 3 (personas trabajando, conciencia de seguridad, contexto latinoamericano)"
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

    MODEL = "gemini-2.5-flash"
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
        articulo.modelo_usado = os.getenv("GEMINI_MODEL", self.MODEL)
        self._persistir_json(articulo)
        return articulo

    def _llamar_gemini(self, user_prompt: str) -> str:
        import time
        import requests as _req

        model = os.getenv("GEMINI_MODEL", self.MODEL)
        url = f"{self._BASE_URL}/{model}:generateContent?key={self._api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.8, "maxOutputTokens": 8192},
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
