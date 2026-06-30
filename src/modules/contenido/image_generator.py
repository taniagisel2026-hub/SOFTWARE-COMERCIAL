"""
ImageGeneratorService — motor gráfico automatizado.

Arquitectura de adaptadores: BaseImageGenerator define el contrato; cualquier
proveedor implementa generate_one() sin cambiar nada en el resto del sistema.

Implementaciones disponibles:
  · PollinationsImageGenerator — activo por defecto; GRATIS, sin API key (Flux model)
  · MockImageGenerator         — fallback si Pollinations falla; guarda prompts en disco
  · DalleImageGenerator        — stub listo para activar con OPENAI_API_KEY
  · ReplicateImageGenerator    — stub listo para activar con REPLICATE_API_TOKEN
"""
import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from ...config import get_config
from .topics import TemaSSTInfo


@dataclass
class ImageResult:
    indice: int                    # 1, 2 o 3
    prompt_original: str           # prompt enviado al generador
    url_local: str                 # ruta en disco (real o placeholder)
    url_remota: str = ""           # URL pública si se subió a CDN
    proveedor: str = "mock"
    estado: str = "PENDIENTE"      # PENDIENTE | GENERADA | ERROR


@dataclass
class SolicitudImagenes:
    articulo_titulo: str
    tema: TemaSSTInfo
    prompts: list[str]             # exactamente 3 prompts del artículo
    fecha: date = field(default_factory=date.today)

    @property
    def slug(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.articulo_titulo.lower())[:40]

    @property
    def output_dir(self) -> Path:
        base = get_config().output_dir / "contenido" / "imagenes"
        return base / f"{self.fecha}_{self.slug}"


# ── Interfaz base ─────────────────────────────────────────────────────────────

class BaseImageGenerator(ABC):

    @abstractmethod
    def generate_one(self, prompt: str, indice: int, output_dir: Path) -> ImageResult:
        """Genera una imagen. Retorna ImageResult con la ruta resultante."""
        ...

    def generate_all(self, solicitud: SolicitudImagenes) -> list[ImageResult]:
        solicitud.output_dir.mkdir(parents=True, exist_ok=True)
        results = []
        for i, prompt in enumerate(solicitud.prompts[:3], start=1):
            resultado = self.generate_one(prompt, i, solicitud.output_dir)
            results.append(resultado)
        return results


# ── MockImageGenerator (activo por defecto) ───────────────────────────────────

class MockImageGenerator(BaseImageGenerator):
    """
    Genera archivos de prompt estructurados listos para procesamiento manual
    o conexión con cualquier API de imágenes.

    Salida por imagen:
      output/contenido/imagenes/{fecha}_{slug}/imagen_{n}_prompt.txt
      output/contenido/imagenes/{fecha}_{slug}/imagen_{n}_placeholder.json
    """

    def generate_one(self, prompt: str, indice: int, output_dir: Path) -> ImageResult:
        # Guardar prompt en texto plano para uso manual (Midjourney, DALL-E web, etc.)
        prompt_path = output_dir / f"imagen_{indice}_prompt.txt"
        prompt_path.write_text(
            f"=== PROMPT PARA IMAGEN {indice} ===\n\n"
            f"Proveedor sugerido: DALL-E 3 / Midjourney / Stable Diffusion\n"
            f"Tamaño recomendado: 1080x1080 (Instagram) o 1200x628 (LinkedIn)\n"
            f"Estilo: professional, corporate, Colombian context\n\n"
            f"PROMPT:\n{prompt}\n\n"
            f"PROMPT EN ESPAÑOL:\n{self._traducir_hint(indice)}",
            encoding="utf-8",
        )

        # Guardar metadata en JSON para carga programática futura
        meta_path = output_dir / f"imagen_{indice}_meta.json"
        meta_path.write_text(
            json.dumps(
                {"indice": indice, "prompt": prompt, "estado": "PENDIENTE_GENERACION"},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )

        return ImageResult(
            indice=indice,
            prompt_original=prompt,
            url_local=str(prompt_path),
            proveedor="mock",
            estado="PENDIENTE",
        )

    @staticmethod
    def _traducir_hint(indice: int) -> str:
        hints = {
            1: "Escena profesional corporativa en oficina colombiana, reunión sobre seguridad laboral",
            2: "Infografía con datos de seguridad laboral, diseño limpio con colores azul y naranja",
            3: "Trabajadores latinoamericanos con equipos de protección, contexto de industria o construcción",
        }
        return hints.get(indice, "Imagen relacionada con seguridad y salud en el trabajo en Colombia")


# ── PollinationsImageGenerator (por defecto — 100% gratis, sin API key) ──────

class PollinationsImageGenerator(BaseImageGenerator):
    """
    Genera imágenes reales usando Pollinations.ai (modelo Flux) — completamente
    gratuito, sin registro ni API key. Cada imagen tarda ~15-30 segundos.

    Tamaño: 1024x1024 — compatible con Instagram, LinkedIn y Facebook.
    """

    _BASE = "https://image.pollinations.ai/prompt/{prompt}"
    _SUFIJO = (
        ", professional corporate photography, seguridad salud trabajo Colombia, "
        "clean modern style, high quality, 4k"
    )

    def generate_one(self, prompt: str, indice: int, output_dir: Path) -> ImageResult:
        try:
            import httpx
            from urllib.parse import quote

            prompt_completo = prompt + self._SUFIJO
            url = (
                f"https://image.pollinations.ai/prompt/{quote(prompt_completo)}"
                f"?width=1024&height=1024&model=flux&nologo=true&seed={indice * 42}"
            )

            respuesta = httpx.get(url, timeout=90, follow_redirects=True)
            respuesta.raise_for_status()

            img_path = output_dir / f"imagen_{indice}.png"
            img_path.write_bytes(respuesta.content)

            return ImageResult(
                indice=indice,
                prompt_original=prompt,
                url_local=str(img_path),
                url_remota=url,
                proveedor="pollinations-flux",
                estado="GENERADA",
            )

        except Exception as exc:
            # Fallback silencioso al mock si Pollinations no responde
            fallback = MockImageGenerator()
            resultado = fallback.generate_one(prompt, indice, output_dir)
            resultado.estado = f"ERROR_POLLINATIONS: {exc}"
            return resultado


# ── DalleImageGenerator (stub — activar con OPENAI_API_KEY) ──────────────────

class DalleImageGenerator(BaseImageGenerator):
    """
    Generador con DALL-E 3 (OpenAI).

    Para activar:
      1. pip install openai
      2. OPENAI_API_KEY=sk-... en .env
      3. Pasar DalleImageGenerator() al ImageGeneratorService
    """

    def __init__(self, api_key: Optional[str] = None, size: str = "1024x1024"):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._size = size

    def generate_one(self, prompt: str, indice: int, output_dir: Path) -> ImageResult:
        try:
            import openai
            import httpx
        except ImportError as exc:
            raise ImportError("Instala openai: pip install openai") from exc

        client = openai.OpenAI(api_key=self._api_key)
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"{prompt} -- professional photography style, corporate SST Colombia",
            size=self._size,
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url

        # Descargar y guardar localmente
        img_path = output_dir / f"imagen_{indice}.png"
        img_path.write_bytes(httpx.get(image_url).content)

        return ImageResult(
            indice=indice,
            prompt_original=prompt,
            url_local=str(img_path),
            url_remota=image_url,
            proveedor="dall-e-3",
            estado="GENERADA",
        )


# ── ReplicateImageGenerator (stub — activar con REPLICATE_API_TOKEN) ─────────

class ReplicateImageGenerator(BaseImageGenerator):
    """
    Generador con Stable Diffusion XL vía Replicate.

    Para activar:
      1. pip install replicate
      2. REPLICATE_API_TOKEN=r8_... en .env
      3. Pasar ReplicateImageGenerator() al ImageGeneratorService
    """

    MODEL_ID = "stability-ai/sdxl:39ed52f2319f9c5dc5d7fbed3b2e8b69b7d6ed8ac67427b3c5e994fac7a91e14"

    def generate_one(self, prompt: str, indice: int, output_dir: Path) -> ImageResult:
        try:
            import replicate
            import httpx
        except ImportError as exc:
            raise ImportError("Instala replicate: pip install replicate") from exc

        output = replicate.run(
            self.MODEL_ID,
            input={
                "prompt": f"{prompt}, professional corporate style, Colombian context, 8k",
                "negative_prompt": "blurry, low quality, cartoon, anime",
                "width": 1024,
                "height": 1024,
            },
        )
        image_url = str(output[0])
        img_path = output_dir / f"imagen_{indice}.png"
        img_path.write_bytes(httpx.get(image_url).content)

        return ImageResult(
            indice=indice,
            prompt_original=prompt,
            url_local=str(img_path),
            url_remota=image_url,
            proveedor="stable-diffusion-xl",
            estado="GENERADA",
        )


# ── Servicio orquestador ──────────────────────────────────────────────────────

class ImageGeneratorService:
    """
    Orquestador: recibe un ArticuloGenerado y produce 3 imágenes.
    El generador concreto se inyecta; por defecto usa MockImageGenerator.
    """

    def __init__(self, generator: Optional[BaseImageGenerator] = None):
        self._gen = generator or PollinationsImageGenerator()

    def generar_para_articulo(
        self,
        articulo_titulo: str,
        prompts: list[str],
        tema: TemaSSTInfo,
    ) -> list[ImageResult]:
        if len(prompts) < 3:
            raise ValueError(f"Se requieren exactamente 3 prompts; recibidos: {len(prompts)}")

        solicitud = SolicitudImagenes(
            articulo_titulo=articulo_titulo,
            tema=tema,
            prompts=prompts[:3],
        )
        return self._gen.generate_all(solicitud)
