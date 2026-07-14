"""
ScraperEngineService — orquesta los tres adaptadores de scraping y entrega
una lista deduplicada de prospectos listos para inyectar en el CRM.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .base import BaseScraperAdapter, ExtractionResult, ProspectoExtraido, _normalizar_texto
from .paginas_amarillas import PaginasAmarillasScraper
from .linkedin_auto import LinkedInAutoScraper, LinkedInSinSesionError
from .linkedin import LinkedInScraper
from .google_maps import GoogleMapsScraper
from .web_scraper import WebScraper


@dataclass
class EngineResult:
    ciudad: str
    sector: str
    inicio: datetime
    fin: datetime
    por_fuente: dict[str, int] = field(default_factory=dict)
    prospectos: list[ProspectoExtraido] = field(default_factory=list)
    duplicados_removidos: int = 0
    descartados_fuera_zona: int = 0
    errores: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.prospectos)

    @property
    def duracion_s(self) -> float:
        return (self.fin - self.inicio).total_seconds()

    def resumen(self) -> str:
        lineas = [
            f"Ciudad: {self.ciudad} | Sector: {self.sector}",
            f"Duración: {self.duracion_s:.1f}s",
            f"Prospectos únicos: {self.total}",
        ]
        for fuente, cantidad in self.por_fuente.items():
            lineas.append(f"  · {fuente}: {cantidad}")
        if self.duplicados_removidos:
            lineas.append(f"Duplicados removidos: {self.duplicados_removidos}")
        if self.descartados_fuera_zona:
            lineas.append(f"Descartados fuera de zona: {self.descartados_fuera_zona}")
        if self.errores:
            for e in self.errores:
                lineas.append(f"  ⚠ {e}")
        return "\n".join(lineas)


class ScraperEngineService:
    """
    Orquesta múltiples adaptadores, desduplicar resultados cruzados entre fuentes
    y devuelve la lista consolidada de prospectos únicos.
    """

    def __init__(
        self,
        adapters: Optional[list[BaseScraperAdapter]] = None,
        web_scraper: Optional[WebScraper] = None,
        enriquecer_emails: bool = True,
    ):
        self._adapters = adapters or [
            GoogleMapsScraper(),
        ]
        self._web = web_scraper or WebScraper()
        self._enriquecer_emails = enriquecer_emails

    def extraer_ciudad(
        self,
        ciudad: str,
        sector: str,
        max_por_fuente: int = 30,
        ciudades_permitidas: Optional[list[str]] = None,
    ) -> EngineResult:
        """
        Ejecuta todos los adaptadores para una ciudad y sector,
        desduplicar el resultado cruzado y opcionalmente enriquecer emails.

        ciudades_permitidas: si se indica, cualquier prospecto cuya ciudad real
        (detectada desde la ficha de Maps) no esté en esta lista se descarta.
        Evita que negocios ubicados en municipios vecinos fuera de la zona de
        cobertura configurada terminen guardados en el CRM.
        """
        inicio = datetime.now()
        todos_prospectos: list[ProspectoExtraido] = []
        por_fuente: dict[str, int] = {}
        errores: list[str] = []

        for adapter in self._adapters:
            resultado: ExtractionResult = adapter.ejecutar_con_resultado(
                ciudad, sector, max_por_fuente
            )
            por_fuente[adapter.SOURCE] = resultado.total
            todos_prospectos.extend(resultado.prospectos)
            errores.extend(resultado.errores)
            print(
                f"  [{adapter.SOURCE}] {resultado.total} prospectos encontrados "
                f"en {resultado.duracion_s:.1f}s"
            )

        # Descartar prospectos cuya ciudad real quede fuera de la zona permitida
        descartados = 0
        if ciudades_permitidas:
            permitidas_norm: set[str] = set()
            for c in ciudades_permitidas:
                norm = _normalizar_texto(c)
                permitidas_norm.add(norm)
                # Google Maps suele devolver "Bogotá" sin el sufijo "D.C."
                if norm.endswith(" d.c."):
                    permitidas_norm.add(norm[: -len(" d.c.")])
            en_zona = []
            for p in todos_prospectos:
                if _normalizar_texto(p.ciudad) in permitidas_norm:
                    en_zona.append(p)
                else:
                    descartados += 1
                    print(f"  ⛔ Descartado fuera de zona: {p.razon_social} ({p.ciudad})")
            todos_prospectos = en_zona

        # Deduplicación cruzada por clave normalizada
        unicos, dup_count = self._deduplicar(todos_prospectos)

        # Enriquecimiento de emails vía WebScraper
        if self._enriquecer_emails:
            unicos = self._web.enriquecer_prospectos(unicos)
            con_email = sum(1 for p in unicos if p.tiene_email)
            print(f"  [WebScraper] {con_email}/{len(unicos)} prospectos con email")

        return EngineResult(
            ciudad=ciudad,
            sector=sector,
            inicio=inicio,
            fin=datetime.now(),
            por_fuente=por_fuente,
            prospectos=unicos,
            duplicados_removidos=dup_count,
            descartados_fuera_zona=descartados,
            errores=errores,
        )

    # ── Deduplicación ─────────────────────────────────────────────────────────

    @staticmethod
    def _deduplicar(
        prospectos: list[ProspectoExtraido],
    ) -> tuple[list[ProspectoExtraido], int]:
        """
        Mantiene un único prospecto por clave normalizada nombre+ciudad.
        Si hay duplicados, fusiona campos vacíos del duplicado al principal.
        """
        vistos: dict[str, ProspectoExtraido] = {}
        dup_count = 0

        for p in prospectos:
            clave = p.clave_dedup
            if clave not in vistos:
                vistos[clave] = p
            else:
                # Fusionar: llenar campos vacíos del principal con datos del duplicado
                principal = vistos[clave]
                if p.telefono and not principal.telefono:
                    principal.telefono = p.telefono
                if p.email and not principal.email:
                    principal.email = p.email
                if p.nombre_contacto and not principal.nombre_contacto:
                    principal.nombre_contacto = p.nombre_contacto
                if p.cargo_contacto and not principal.cargo_contacto:
                    principal.cargo_contacto = p.cargo_contacto
                if p.num_empleados > 0 and principal.num_empleados == 0:
                    principal.num_empleados = p.num_empleados
                if p.confianza > principal.confianza:
                    principal.confianza = p.confianza
                dup_count += 1

        return list(vistos.values()), dup_count
