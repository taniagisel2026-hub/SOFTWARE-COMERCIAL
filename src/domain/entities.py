from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


class NivelRiesgo(str, Enum):
    I = "I"
    II = "II"
    III = "III"
    IV = "IV"
    V = "V"


class EstadoProspecto(str, Enum):
    NUEVO = "NUEVO"
    EN_SEGUIMIENTO = "EN_SEGUIMIENTO"
    COTIZACION_ENVIADA = "COTIZACION_ENVIADA"
    NEGOCIACION = "NEGOCIACION"
    CERRADO_GANADO = "CERRADO_GANADO"
    CERRADO_PERDIDO = "CERRADO_PERDIDO"


class EstadoCotizacion(str, Enum):
    BORRADOR = "BORRADOR"
    ENVIADA = "ENVIADA"
    ACEPTADA = "ACEPTADA"
    RECHAZADA = "RECHAZADA"
    VENCIDA = "VENCIDA"


class NivelEstandares(str, Enum):
    NIVEL_7 = "NIVEL_7"    # 1–10 trabajadores, Riesgo I/II/III
    NIVEL_21 = "NIVEL_21"  # 11–50 trabajadores, Riesgo I/II/III
    NIVEL_60 = "NIVEL_60"  # >50 trabajadores (cualquier riesgo) ó 1–50 con Riesgo IV/V


@dataclass
class EmpresaProspecto:
    razon_social: str
    nit: str
    ciudad: str
    departamento: str
    num_empleados: int
    nivel_riesgo_arl: NivelRiesgo
    sector_economico: str = ""
    direccion: str = ""
    telefono: str = ""
    email_contacto: str = ""
    nombre_contacto: str = ""
    cargo_contacto: str = ""
    estado_prospecto: EstadoProspecto = EstadoProspecto.NUEVO
    fuente_origen: str = ""
    id_empresa: int = 0
    fecha_registro: date = field(default_factory=date.today)
    fecha_ultima_actualizacion: date = field(default_factory=date.today)


@dataclass
class ServicioCotizado:
    nombre: str
    descripcion: str
    cantidad_horas: int
    valor_unitario: Decimal

    @property
    def valor_total(self) -> Decimal:
        return Decimal(str(self.cantidad_horas)) * self.valor_unitario

    def to_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "cantidad_horas": self.cantidad_horas,
            "valor_unitario": str(self.valor_unitario),
            "valor_total": str(self.valor_total),
        }


@dataclass
class Cotizacion:
    id_empresa: int
    nivel_estandares: NivelEstandares
    num_empleados_cotizados: int
    nivel_riesgo: NivelRiesgo
    servicios_incluidos: list[ServicioCotizado]
    valor_viaticos: Decimal
    creado_por: str
    id_cotizacion: int = 0
    codigo_cotizacion: str = field(default_factory=lambda: f"COT-{uuid.uuid4().hex[:8].upper()}")
    version: str = "1.0"
    moneda: str = "COP"
    estado_cotizacion: EstadoCotizacion = EstadoCotizacion.BORRADOR
    fecha_emision: date = field(default_factory=date.today)
    fecha_vencimiento: Optional[date] = field(
        default_factory=lambda: date.today() + timedelta(days=30)
    )
    url_documento_pdf: str = ""

    @property
    def valor_servicios(self) -> Decimal:
        return sum((s.valor_total for s in self.servicios_incluidos), Decimal("0"))

    @property
    def valor_total_proyecto(self) -> Decimal:
        return self.valor_servicios + self.valor_viaticos

    @property
    def valor_total_mensual(self) -> Decimal:
        return (self.valor_total_proyecto / 12).quantize(Decimal("1"))

    @property
    def valor_total_anual(self) -> Decimal:
        return self.valor_total_proyecto
