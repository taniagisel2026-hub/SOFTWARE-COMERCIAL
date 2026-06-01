"""
Contratos base y estructuras de datos compartidas por todos los adaptadores de scraping.
"""
import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


# ── Estimación de nivel de riesgo ARL por sector (Decreto 1607/2002) ─────────
_SECTOR_RIESGO: dict[str, str] = {
    "construcción": "III",  "construccion": "III",
    "manufactura": "III",   "industria": "III",
    "minería": "IV",        "mineria": "IV",
    "petróleo": "V",        "petroleo": "V",  "gas": "V",
    "transporte": "III",    "logística": "III",  "logistica": "III",
    "agricultura": "IV",    "forestal": "III",
    "químico": "III",       "quimico": "III",
    "salud": "II",          "clínica": "II",  "clinica": "II",
    "educación": "I",       "educacion": "I",
    "comercio": "I",        "retail": "I",
    "servicios": "I",       "consultoría": "I",  "consultoria": "I",
    "tecnología": "I",      "tecnologia": "I",   "software": "I",
    "alimentos": "II",      "restaurante": "II",
    "seguridad": "II",
}

_NIVEL_DEFAULT = "I"


def estimar_nivel_riesgo(sector: str) -> str:
    sector_norm = _normalizar_texto(sector)
    for clave, nivel in _SECTOR_RIESGO.items():
        if clave in sector_norm:
            return nivel
    return _NIVEL_DEFAULT


def _normalizar_texto(texto: str) -> str:
    """Minúsculas + elimina tildes + colapsa espacios."""
    sin_tilde = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", sin_tilde.lower().strip())


def _normalizar_nombre_empresa(nombre: str) -> str:
    """Elimina sufijos legales para comparación de duplicados."""
    sufijos = r"\b(s\.?a\.?s\.?|s\.?a\.?|ltda\.?|s\.?a\.?s|inc\.?|corp\.?|srl\.?)\b"
    limpio = re.sub(sufijos, "", _normalizar_texto(nombre), flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", limpio).strip()


# ── Estructura de datos de un prospecto extraído ──────────────────────────────

@dataclass
class ProspectoExtraido:
    razon_social: str
    ciudad: str
    departamento: str
    fuente: str                          # "Google Maps" | "LinkedIn" | "Web"

    nit: str = ""
    sector_economico: str = ""
    direccion: str = ""
    telefono: str = ""
    email: str = ""
    sitio_web: str = ""
    nombre_contacto: str = ""
    cargo_contacto: str = ""
    num_empleados: int = 0               # 0 = desconocido
    nivel_riesgo_arl: str = ""           # se estima si está vacío
    confianza: float = 1.0               # 0.0–1.0
    raw_data: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.nivel_riesgo_arl:
            self.nivel_riesgo_arl = estimar_nivel_riesgo(self.sector_economico)

    @property
    def clave_dedup(self) -> str:
        """Clave de deduplicación: nombre normalizado + ciudad normalizada."""
        return f"{_normalizar_nombre_empresa(self.razon_social)}|{_normalizar_texto(self.ciudad)}"

    @property
    def tiene_email(self) -> bool:
        return bool(self.email and "@" in self.email)


@dataclass
class ExtractionResult:
    fuente: str
    ciudad: str
    sector: str
    prospectos: list[ProspectoExtraido]
    inicio: datetime
    fin: datetime
    errores: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.prospectos)

    @property
    def duracion_s(self) -> float:
        return (self.fin - self.inicio).total_seconds()


# ── Interfaz base para adaptadores ───────────────────────────────────────────

class BaseScraperAdapter(ABC):

    SOURCE: str = "Desconocido"

    @abstractmethod
    def extraer(
        self,
        ciudad: str,
        sector: str,
        max_resultados: int = 30,
    ) -> list[ProspectoExtraido]:
        """Ejecuta la extracción y retorna lista de prospectos."""
        ...

    def ejecutar_con_resultado(
        self,
        ciudad: str,
        sector: str,
        max_resultados: int = 30,
    ) -> ExtractionResult:
        inicio = datetime.now()
        errores: list[str] = []
        prospectos: list[ProspectoExtraido] = []
        try:
            prospectos = self.extraer(ciudad, sector, max_resultados)
        except Exception as exc:
            errores.append(f"{self.SOURCE}: {exc}")
        return ExtractionResult(
            fuente=self.SOURCE,
            ciudad=ciudad,
            sector=sector,
            prospectos=prospectos,
            inicio=inicio,
            fin=datetime.now(),
            errores=errores,
        )
