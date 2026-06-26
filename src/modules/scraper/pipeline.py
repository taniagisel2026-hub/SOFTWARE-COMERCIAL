"""
ProspectionPipeline — orquestador de punta a punta de la Fase 4.

Conecta el motor de scraping (Fase 4) con el motor de correos (Fase 2)
respetando estrictamente el rate limiting y el control de Habeas Data.

Flujo completo:
  extraer → deduplicar → inyectar en CRM → convertir a dominio → enviar correos
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ...database.connection import get_session
from ...database.models import EmpresaProspecto as EmpresaProspectoORM
from ...domain.entities import (
    EmpresaProspecto as EmpresaProspectoDomain,
    EstadoProspecto,
    NivelRiesgo,
)
from ..compliance.habeas_data import HabeasDataError
from ..email.email_service import EmailService
from ..email.rate_limiter import RateLimitExceededError
from .crm_injector import CRMInjectorService, InyeccionLoteResult
from .engine import EngineResult, ScraperEngineService


@dataclass
class PipelineResult:
    ciudad: str
    sector: str
    inicio: datetime
    fin: datetime
    empresas_encontradas: int = 0
    empresas_nuevas: int = 0
    empresas_existentes: int = 0
    emails_enviados: int = 0
    emails_sin_contacto: int = 0
    emails_fallidos: int = 0
    rate_limit_alcanzado: bool = False
    errores: list[str] = field(default_factory=list)

    @property
    def duracion_s(self) -> float:
        return (self.fin - self.inicio).total_seconds()

    def resumen(self) -> str:
        estado_email = "✓ Completado"
        if self.rate_limit_alcanzado:
            estado_email = f"⏸ Pausado por rate limit (enviados hoy: {self.emails_enviados})"
        return (
            f"\n{'='*55}\n"
            f" PIPELINE COMPLETADO — {self.ciudad} / {self.sector}\n"
            f"{'='*55}\n"
            f" Duración:          {self.duracion_s:.1f}s\n"
            f" Empresas totales:  {self.empresas_encontradas}\n"
            f" Nuevas en CRM:     {self.empresas_nuevas}\n"
            f" Ya existían:       {self.empresas_existentes}\n"
            f" Emails enviados:   {self.emails_enviados}\n"
            f" Sin email/contacto:{self.emails_sin_contacto}\n"
            f" Emails fallidos:   {self.emails_fallidos}\n"
            f" Canal email:       {estado_email}\n"
            f"{'='*55}"
        )


class ProspectionPipeline:
    """
    Orquestador de la prospección masiva por ciudad.
    Conecta extracción, CRM e inicio de secuencia de correos fríos.
    """

    def __init__(
        self,
        engine: Optional[ScraperEngineService] = None,
        injector: Optional[CRMInjectorService] = None,
        email_service: Optional[EmailService] = None,
    ):
        self._engine = engine or ScraperEngineService()
        self._injector = injector or CRMInjectorService()
        self._email = email_service or EmailService()

    def ejecutar(
        self,
        ciudad: str,
        sector: str,
        max_por_fuente: int = 30,
        disparar_emails: bool = True,
        solo_nuevas: bool = True,
        usar_gmaps: bool = True,
        usar_paginas_amarillas: bool = True,
        usar_linkedin: bool = True,
        usar_webscraper: bool = True,
    ) -> PipelineResult:
        """
        Parámetros:
          ciudad          — ciudad colombiana objetivo
          sector          — sector económico ("Construcción", "Manufactura", etc.)
          max_por_fuente  — máximo de empresas por scraper
          disparar_emails — conectar con EmailService al finalizar
          solo_nuevas     — solo enviar correos a empresas recién insertadas
        """
        inicio = datetime.now()
        resultado = PipelineResult(ciudad=ciudad, sector=sector, inicio=inicio, fin=inicio)

        print(f"\n[Pipeline] Iniciando: {ciudad} / {sector}")

        # Reconstruir engine con solo los adaptadores seleccionados
        from .engine import ScraperEngineService
        from .google_maps import GoogleMapsScraper
        from .linkedin_auto import LinkedInAutoScraper
        from .linkedin import LinkedInScraper
        from .paginas_amarillas import PaginasAmarillasScraper
        from .web_scraper import WebScraper

        adapters = []
        if usar_gmaps:
            adapters.append(GoogleMapsScraper())
        if usar_paginas_amarillas:
            adapters.append(PaginasAmarillasScraper())
        if usar_linkedin:
            li = LinkedInAutoScraper() if LinkedInAutoScraper.sesion_existe() else LinkedInScraper()
            adapters.append(li)

        engine = ScraperEngineService(
            adapters=adapters,
            enriquecer_emails=usar_webscraper,
        )

        # ── Paso 1: Extracción ────────────────────────────────────────────────
        print("[Pipeline] Paso 1/3: Extracción de prospectos...")
        engine_result: EngineResult = engine.extraer_ciudad(ciudad, sector, max_por_fuente)
        resultado.empresas_encontradas = engine_result.total
        print(engine_result.resumen())

        if not engine_result.prospectos:
            resultado.fin = datetime.now()
            resultado.errores.append("No se encontraron prospectos.")
            return resultado

        # ── Paso 2: Inyección en CRM ──────────────────────────────────────────
        print(f"[Pipeline] Paso 2/3: Inyectando {engine_result.total} prospectos en CRM...")
        inyeccion: InyeccionLoteResult = self._injector.inyectar_lote(engine_result.prospectos)
        resultado.empresas_nuevas = inyeccion.insertadas
        resultado.empresas_existentes = inyeccion.actualizadas
        resultado.errores.extend(inyeccion.errores)
        print(
            f"  Nuevas: {inyeccion.insertadas} | "
            f"Actualizadas: {inyeccion.actualizadas} | "
            f"Omitidas: {inyeccion.omitidas}"
        )

        # ── Paso 3: Secuencia de correos fríos ───────────────────────────────
        if not disparar_emails:
            resultado.fin = datetime.now()
            return resultado

        ids_objetivo = inyeccion.ids_nuevos if solo_nuevas else self._obtener_ids_ciudad(ciudad)
        print(f"[Pipeline] Paso 3/3: Iniciando outreach para {len(ids_objetivo)} empresas...")

        for id_empresa in ids_objetivo:
            if resultado.rate_limit_alcanzado:
                break
            try:
                empresa_domain = self._orm_a_dominio(id_empresa)
                if not empresa_domain.email_contacto:
                    resultado.emails_sin_contacto += 1
                    continue

                self._email.enviar(
                    empresa=empresa_domain,
                    tipo_plantilla="PRIMER_CONTACTO",
                    creado_por="Pipeline Automatizado",
                )
                resultado.emails_enviados += 1
                print(f"  ✓ Email enviado → {empresa_domain.razon_social}")

            except RateLimitExceededError:
                resultado.rate_limit_alcanzado = True
                print(f"  ⏸ Rate limit alcanzado. Correos enviados hoy: {resultado.emails_enviados}")

            except HabeasDataError as exc:
                resultado.emails_fallidos += 1
                print(f"  ⚠ Opt-out activo: {exc}")

            except Exception as exc:
                resultado.emails_fallidos += 1
                resultado.errores.append(f"Email id={id_empresa}: {exc}")

        resultado.fin = datetime.now()
        print(resultado.resumen())
        return resultado

    # ── Conversión ORM → entidad dominio ──────────────────────────────────────

    @staticmethod
    def _orm_a_dominio(id_empresa: int) -> EmpresaProspectoDomain:
        with get_session() as session:
            orm = session.get(EmpresaProspectoORM, id_empresa)
            if orm is None:
                raise ValueError(f"Empresa id={id_empresa} no encontrada.")
            return EmpresaProspectoDomain(
                id_empresa=orm.id_empresa,
                razon_social=orm.razon_social,
                nit=orm.nit,
                ciudad=orm.ciudad,
                departamento=orm.departamento,
                num_empleados=orm.num_empleados,
                nivel_riesgo_arl=NivelRiesgo(orm.nivel_riesgo_arl),
                sector_economico=orm.sector_economico or "",
                direccion=orm.direccion or "",
                telefono=orm.telefono or "",
                email_contacto=orm.email_contacto or "",
                nombre_contacto=orm.nombre_contacto or "",
                cargo_contacto=orm.cargo_contacto or "",
                estado_prospecto=EstadoProspecto(orm.estado_prospecto),
                fuente_origen=orm.fuente_origen or "",
                fecha_registro=orm.fecha_registro,
                fecha_ultima_actualizacion=orm.fecha_ultima_actualizacion,
            )

    @staticmethod
    def _obtener_ids_ciudad(ciudad: str) -> list[int]:
        with get_session() as session:
            rows = (
                session.query(EmpresaProspectoORM.id_empresa)
                .filter(
                    EmpresaProspectoORM.ciudad.ilike(f"%{ciudad}%"),
                    EmpresaProspectoORM.estado_prospecto == "NUEVO",
                    EmpresaProspectoORM.email_contacto.isnot(None),
                    EmpresaProspectoORM.opt_out == False,
                )
                .all()
            )
        return [r.id_empresa for r in rows]
