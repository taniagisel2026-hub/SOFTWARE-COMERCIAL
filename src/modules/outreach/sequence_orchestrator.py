"""
SequenceOrchestrator — cadencia omnicanal Día 1 → Día 4 → Día 8.

  Día 1 : Email PRIMER_CONTACTO        (se dispara al incorporar el prospecto)
  Día 4 : WhatsApp de seguimiento       (≥3 días desde Día 1, requiere teléfono)
  Día 8 : Email RECORDATORIO_VENCIMIENTO (≥4 días desde Día 4 ó ≥7 desde Día 1)

Si la empresa no tiene teléfono, Día 4 se omite y Día 8 se calcula desde Día 1.
Apertura de email: al no disponer de webhooks, se usa el tiempo transcurrido como
proxy de "interacción ficticia" — si pasaron ≥3 días, se presume recibido.

Estado de la cadencia trazado en HISTORIAL_INTERACCIONES:
  tipo_interaccion = "SECUENCIA_CADENCIA"
  notas_seguimiento empieza con "[SEQ:DIA_1]", "[SEQ:DIA_4]" o "[SEQ:DIA_8]"
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func

from ...database.connection import get_session
from ...database.models import EmpresaProspecto as EmpresaORM
from ...database.models import HistorialInteracciones
from ...domain.entities import (
    EmpresaProspecto as EmpresaDominio,
    EstadoProspecto,
    NivelRiesgo,
)
from ..compliance.habeas_data import HabeasDataError, HabeasDataService
from ..email.email_service import EmailService
from ..email.rate_limiter import RateLimitExceededError
from ..whatsapp.whatsapp_service import WhatsAppService

# ── Tags de control de secuencia ────────────────────────────────────────────
TAG_DIA_1 = "[SEQ:DIA_1]"
TAG_DIA_4 = "[SEQ:DIA_4]"
TAG_DIA_8 = "[SEQ:DIA_8]"

OFFSET_DIA_4 = 3   # días después del Día 1
OFFSET_DIA_8 = 4   # días después del Día 4 (= Día 8 total)
OFFSET_DIA_8_SIN_WA = 7  # días desde Día 1 si no hubo Día 4


# ── Dataclasses de estado ────────────────────────────────────────────────────

@dataclass
class PasoSecuencia:
    tag: str
    enviado: bool
    fecha: Optional[date] = None


@dataclass
class EstadoSecuencia:
    id_empresa: int
    razon_social: str
    dia_1: PasoSecuencia = field(default_factory=lambda: PasoSecuencia(TAG_DIA_1, False))
    dia_4: PasoSecuencia = field(default_factory=lambda: PasoSecuencia(TAG_DIA_4, False))
    dia_8: PasoSecuencia = field(default_factory=lambda: PasoSecuencia(TAG_DIA_8, False))
    tiene_telefono: bool = False

    @property
    def siguiente_paso(self) -> str:
        if not self.dia_1.enviado:
            return "DIA_1"
        if not self.dia_4.enviado and self.tiene_telefono:
            return "DIA_4" if self._dias_desde(self.dia_1.fecha) >= OFFSET_DIA_4 else "EN_ESPERA"
        if not self.dia_8.enviado:
            ref = self.dia_4.fecha if self.dia_4.enviado else self.dia_1.fecha
            umbral = OFFSET_DIA_8 if self.dia_4.enviado else OFFSET_DIA_8_SIN_WA
            return "DIA_8" if self._dias_desde(ref) >= umbral else "EN_ESPERA"
        return "COMPLETA"

    @property
    def dias_en_secuencia(self) -> int:
        return self._dias_desde(self.dia_1.fecha) if self.dia_1.fecha else 0

    @staticmethod
    def _dias_desde(fecha: Optional[date]) -> int:
        return (date.today() - fecha).days if fecha else 0


@dataclass
class ResultadoProcesamiento:
    id_empresa: int
    razon_social: str
    accion: str        # "DIA_1" | "DIA_4" | "DIA_8" | "EN_ESPERA" | "COMPLETA" | "ERROR"
    ok: bool
    mensaje: str


# ── Servicio principal ────────────────────────────────────────────────────────

class SequenceOrchestrator:

    def __init__(
        self,
        email_svc: Optional[EmailService] = None,
        whatsapp_svc: Optional[WhatsAppService] = None,
        habeas_data: Optional[HabeasDataService] = None,
    ):
        self._email     = email_svc or EmailService()
        self._whatsapp  = whatsapp_svc or WhatsAppService()
        self._habeas    = habeas_data or HabeasDataService()

    # ── API pública ────────────────────────────────────────────────────────────

    def iniciar_secuencia(
        self, empresa: EmpresaDominio, creado_por: str = "Pipeline"
    ) -> ResultadoProcesamiento:
        """
        Dispara el Día 1 (email de presentación) y registra el inicio de la cadencia.
        Llamado por ProspectionPipeline al incorporar un prospecto nuevo.
        """
        try:
            self._habeas.verificar_opt_out(empresa.id_empresa)
            self._email.enviar(empresa, "PRIMER_CONTACTO", creado_por)
            self._log_secuencia(empresa.id_empresa, TAG_DIA_1,
                                "Día 1: Email de presentación enviado", creado_por)
            return ResultadoProcesamiento(
                id_empresa=empresa.id_empresa,
                razon_social=empresa.razon_social,
                accion="DIA_1", ok=True,
                mensaje="Email de presentación enviado correctamente.",
            )
        except (HabeasDataError, RateLimitExceededError) as exc:
            return ResultadoProcesamiento(
                id_empresa=empresa.id_empresa,
                razon_social=empresa.razon_social,
                accion="DIA_1", ok=False, mensaje=str(exc),
            )
        except Exception as exc:
            return ResultadoProcesamiento(
                id_empresa=empresa.id_empresa,
                razon_social=empresa.razon_social,
                accion="DIA_1", ok=False, mensaje=f"Error: {exc}",
            )

    def verificar_y_avanzar(
        self, id_empresa: int, creado_por: str = "Scheduler"
    ) -> ResultadoProcesamiento:
        """
        Evalúa si corresponde disparar Día 4 o Día 8 para una empresa específica.
        """
        estado = self.obtener_estado(id_empresa)
        accion = estado.siguiente_paso

        if accion == "EN_ESPERA":
            return ResultadoProcesamiento(
                id_empresa=id_empresa, razon_social=estado.razon_social,
                accion="EN_ESPERA", ok=True,
                mensaje=f"Día {estado.dias_en_secuencia} de secuencia. Aún no corresponde la siguiente acción.",
            )
        if accion == "COMPLETA":
            return ResultadoProcesamiento(
                id_empresa=id_empresa, razon_social=estado.razon_social,
                accion="COMPLETA", ok=True, mensaje="Secuencia omnicanal completada.",
            )
        if accion == "DIA_4":
            return self._enviar_dia_4(id_empresa, estado.razon_social, creado_por)
        if accion == "DIA_8":
            return self._enviar_dia_8(id_empresa, estado.razon_social, creado_por)

        return ResultadoProcesamiento(
            id_empresa=id_empresa, razon_social=estado.razon_social,
            accion="DIA_1", ok=False, mensaje="Secuencia no iniciada para esta empresa.",
        )

    def procesar_pendientes(
        self, creado_por: str = "Scheduler"
    ) -> list[ResultadoProcesamiento]:
        """
        Recorre todos los prospectos activos y avanza los que corresponda.
        Diseñado para ejecución diaria (botón en GUI o cron job).
        """
        resultados: list[ResultadoProcesamiento] = []

        with get_session() as session:
            candidatos_dia_4 = self._ids_candidatos_dia_4(session)
            candidatos_dia_8 = self._ids_candidatos_dia_8(session)

        rate_limit_alcanzado = False

        for id_emp in candidatos_dia_4:
            if rate_limit_alcanzado:
                break
            r = self._enviar_dia_4(id_emp, "", creado_por)
            resultados.append(r)
            if "Límite" in r.mensaje or "rate" in r.mensaje.lower():
                rate_limit_alcanzado = True

        for id_emp in candidatos_dia_8:
            if rate_limit_alcanzado:
                break
            r = self._enviar_dia_8(id_emp, "", creado_por)
            resultados.append(r)
            if "Límite" in r.mensaje or "rate" in r.mensaje.lower():
                rate_limit_alcanzado = True

        return resultados

    def obtener_estado(self, id_empresa: int) -> EstadoSecuencia:
        """Consulta el estado actual de la cadencia leyendo HistorialInteracciones."""
        with get_session() as session:
            empresa = session.get(EmpresaORM, id_empresa)
            if not empresa:
                raise ValueError(f"Empresa id={id_empresa} no encontrada.")

            logs = (
                session.query(HistorialInteracciones)
                .filter(
                    HistorialInteracciones.id_empresa == id_empresa,
                    HistorialInteracciones.tipo_interaccion == "SECUENCIA_CADENCIA",
                )
                .order_by(HistorialInteracciones.fecha_interaccion)
                .all()
            )

            def _buscar(tag: str) -> tuple[bool, Optional[date]]:
                for log in logs:
                    if log.notas_seguimiento and log.notas_seguimiento.startswith(tag):
                        return True, log.fecha_interaccion.date()
                return False, None

            d1_ok, d1_fecha = _buscar(TAG_DIA_1)
            d4_ok, d4_fecha = _buscar(TAG_DIA_4)
            d8_ok, d8_fecha = _buscar(TAG_DIA_8)

            return EstadoSecuencia(
                id_empresa=id_empresa,
                razon_social=empresa.razon_social,
                dia_1=PasoSecuencia(TAG_DIA_1, d1_ok, d1_fecha),
                dia_4=PasoSecuencia(TAG_DIA_4, d4_ok, d4_fecha),
                dia_8=PasoSecuencia(TAG_DIA_8, d8_ok, d8_fecha),
                tiene_telefono=bool(empresa.telefono),
            )

    # ── Envíos de cadencia ────────────────────────────────────────────────────

    def _enviar_dia_4(
        self, id_empresa: int, razon_social: str, creado_por: str
    ) -> ResultadoProcesamiento:
        try:
            empresa = self._cargar_dominio(id_empresa)
            razon_social = razon_social or empresa.razon_social
            self._habeas.verificar_opt_out(id_empresa)
            self._whatsapp.enviar(empresa, creado_por)
            self._log_secuencia(
                id_empresa, TAG_DIA_4,
                "Día 4: WhatsApp de seguimiento enviado — apertura email asumida por tiempo transcurrido",
                creado_por,
            )
            return ResultadoProcesamiento(
                id_empresa=id_empresa, razon_social=razon_social,
                accion="DIA_4", ok=True,
                mensaje=f"WhatsApp Día 4 enviado a {empresa.telefono}.",
            )
        except Exception as exc:
            return ResultadoProcesamiento(
                id_empresa=id_empresa, razon_social=razon_social,
                accion="DIA_4", ok=False, mensaje=str(exc),
            )

    def _enviar_dia_8(
        self, id_empresa: int, razon_social: str, creado_por: str
    ) -> ResultadoProcesamiento:
        try:
            empresa = self._cargar_dominio(id_empresa)
            razon_social = razon_social or empresa.razon_social
            self._habeas.verificar_opt_out(id_empresa)
            self._email.enviar(empresa, "RECORDATORIO_VENCIMIENTO", creado_por)
            self._log_secuencia(
                id_empresa, TAG_DIA_8,
                "Día 8: Email recordatorio de vencimiento enviado",
                creado_por,
            )
            return ResultadoProcesamiento(
                id_empresa=id_empresa, razon_social=razon_social,
                accion="DIA_8", ok=True,
                mensaje=f"Email recordatorio Día 8 enviado a {empresa.email_contacto}.",
            )
        except Exception as exc:
            return ResultadoProcesamiento(
                id_empresa=id_empresa, razon_social=razon_social,
                accion="DIA_8", ok=False, mensaje=str(exc),
            )

    # ── Consultas de candidatos ───────────────────────────────────────────────

    @staticmethod
    def _ids_candidatos_dia_4(session) -> list[int]:
        """Empresas con DIA_1 enviado hace ≥3 días, sin DIA_4, con teléfono, sin opt-out."""
        corte = datetime.now() - timedelta(days=OFFSET_DIA_4)

        tiene_dia_1 = (
            session.query(HistorialInteracciones.id_empresa)
            .filter(
                HistorialInteracciones.tipo_interaccion == "SECUENCIA_CADENCIA",
                HistorialInteracciones.notas_seguimiento.like(f"{TAG_DIA_1}%"),
                HistorialInteracciones.fecha_interaccion <= corte,
            )
            .subquery()
        )
        tiene_dia_4 = (
            session.query(HistorialInteracciones.id_empresa)
            .filter(
                HistorialInteracciones.tipo_interaccion == "SECUENCIA_CADENCIA",
                HistorialInteracciones.notas_seguimiento.like(f"{TAG_DIA_4}%"),
            )
            .subquery()
        )
        rows = (
            session.query(EmpresaORM.id_empresa)
            .filter(
                EmpresaORM.opt_out == False,
                EmpresaORM.telefono.isnot(None),
                EmpresaORM.id_empresa.in_(session.query(tiene_dia_1)),
                EmpresaORM.id_empresa.notin_(session.query(tiene_dia_4)),
            )
            .all()
        )
        return [r.id_empresa for r in rows]

    @staticmethod
    def _ids_candidatos_dia_8(session) -> list[int]:
        """
        Empresas con DIA_4 enviado hace ≥4 días (ó DIA_1 hace ≥7 días sin DIA_4),
        sin DIA_8, con email, sin opt-out.
        """
        corte_d4 = datetime.now() - timedelta(days=OFFSET_DIA_8)
        corte_d1_sin_wa = datetime.now() - timedelta(days=OFFSET_DIA_8_SIN_WA)

        # Caso A: tienen DIA_4 y ya pasaron ≥4 días
        tiene_dia_4_listo = (
            session.query(HistorialInteracciones.id_empresa)
            .filter(
                HistorialInteracciones.tipo_interaccion == "SECUENCIA_CADENCIA",
                HistorialInteracciones.notas_seguimiento.like(f"{TAG_DIA_4}%"),
                HistorialInteracciones.fecha_interaccion <= corte_d4,
            )
            .subquery()
        )
        # Caso B: tienen DIA_1 hace ≥7 días y no tienen DIA_4 (sin teléfono)
        tiene_dia_1_antiguo = (
            session.query(HistorialInteracciones.id_empresa)
            .filter(
                HistorialInteracciones.tipo_interaccion == "SECUENCIA_CADENCIA",
                HistorialInteracciones.notas_seguimiento.like(f"{TAG_DIA_1}%"),
                HistorialInteracciones.fecha_interaccion <= corte_d1_sin_wa,
            )
            .subquery()
        )
        tiene_dia_4_cualquiera = (
            session.query(HistorialInteracciones.id_empresa)
            .filter(
                HistorialInteracciones.tipo_interaccion == "SECUENCIA_CADENCIA",
                HistorialInteracciones.notas_seguimiento.like(f"{TAG_DIA_4}%"),
            )
            .subquery()
        )
        tiene_dia_8 = (
            session.query(HistorialInteracciones.id_empresa)
            .filter(
                HistorialInteracciones.tipo_interaccion == "SECUENCIA_CADENCIA",
                HistorialInteracciones.notas_seguimiento.like(f"{TAG_DIA_8}%"),
            )
            .subquery()
        )
        from sqlalchemy import or_
        rows = (
            session.query(EmpresaORM.id_empresa)
            .filter(
                EmpresaORM.opt_out == False,
                EmpresaORM.email_contacto.isnot(None),
                or_(
                    EmpresaORM.id_empresa.in_(session.query(tiene_dia_4_listo)),
                    EmpresaORM.id_empresa.in_(session.query(tiene_dia_1_antiguo)),
                ),
                EmpresaORM.id_empresa.notin_(session.query(tiene_dia_8)),
            )
            .all()
        )
        return [r.id_empresa for r in rows]

    # ── Utilidades ────────────────────────────────────────────────────────────

    @staticmethod
    def _log_secuencia(id_empresa: int, tag: str, descripcion: str, responsable: str) -> None:
        with get_session() as session:
            session.add(HistorialInteracciones(
                id_empresa=id_empresa,
                tipo_interaccion="SECUENCIA_CADENCIA",
                canal="SISTEMA",
                asunto=descripcion,
                estado_respuesta="REGISTRADO",
                fecha_interaccion=datetime.now(),
                responsable=responsable,
                notas_seguimiento=f"{tag} | {descripcion}",
            ))

    @staticmethod
    def _cargar_dominio(id_empresa: int) -> EmpresaDominio:
        with get_session() as session:
            r = session.get(EmpresaORM, id_empresa)
            if not r:
                raise ValueError(f"Empresa id={id_empresa} no encontrada.")
            return EmpresaDominio(
                id_empresa=r.id_empresa,
                razon_social=r.razon_social,
                nit=r.nit,
                ciudad=r.ciudad,
                departamento=r.departamento,
                num_empleados=r.num_empleados,
                nivel_riesgo_arl=NivelRiesgo(r.nivel_riesgo_arl),
                sector_economico=r.sector_economico or "",
                direccion=r.direccion or "",
                telefono=r.telefono or "",
                email_contacto=r.email_contacto or "",
                nombre_contacto=r.nombre_contacto or "",
                cargo_contacto=r.cargo_contacto or "",
                estado_prospecto=EstadoProspecto(r.estado_prospecto),
                fuente_origen=r.fuente_origen or "",
                fecha_registro=r.fecha_registro,
                fecha_ultima_actualizacion=r.fecha_ultima_actualizacion,
            )
