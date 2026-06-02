from decimal import Decimal
from typing import Optional

from ...domain.entities import Cotizacion, EmpresaProspecto, NivelEstandares, ServicioCotizado
from ...domain.resolution_0312 import ESPECIFICACIONES, EspecificacionNivel, clasificar_nivel_estandares
from .viaticos import ViaticosCalculator


SERVICIOS_ADICIONALES: dict[str, dict] = {
    "HIGIENE_INDUSTRIAL": {
        "nombre": "Mediciones Ambientales e Higiene Industrial",
        "descripcion": "Mediciones higiénicas: ruido, iluminación, material particulado y agentes químicos",
        "horas_base": 16,
        "factor_por_empleado": Decimal("0.10"),
    },
    "APT": {
        "nombre": "Análisis de Puestos de Trabajo (APT)",
        "descripcion": "Análisis ergonómico y evaluación de condiciones por cargo (APT)",
        "horas_base": 16,
        "factor_por_empleado": Decimal("0.30"),
    },
    "BATERIA_PSICOSOCIAL": {
        "nombre": "Batería de Riesgo Psicosocial",
        "descripcion": "Aplicación e interpretación de la Batería de Instrumentos para Evaluación de Riesgo Psicosocial (Min. Trabajo)",
        "horas_base": 12,
        "factor_por_empleado": Decimal("0.25"),
    },
    "PESV": {
        "nombre": "Plan Estratégico de Seguridad Vial (PESV)",
        "descripcion": "Diseño e implementación del PESV según Ley 1503/2011 y Resolución 40595/2022",
        "horas_base": 40,
        "factor_por_empleado": Decimal("0.20"),
    },
    "ISO_45001": {
        "nombre": "Sistema de Gestión ISO 45001:2018",
        "descripcion": "Implementación del SG-SST bajo la norma ISO 45001:2018 con preparación para certificación",
        "horas_base": 80,
        "factor_por_empleado": Decimal("0.50"),
    },
}


class CotizadorService:
    """
    Genera cotizaciones de diseño del SG-SST aplicando la Resolución 0312/2019.
    """

    VALOR_HORA_COP = Decimal("88_000")

    def __init__(self, viaticos_calc: Optional[ViaticosCalculator] = None):
        self._viaticos = viaticos_calc or ViaticosCalculator()

    def generar_cotizacion(
        self,
        empresa: EmpresaProspecto,
        creado_por: str = "Sistema",
    ) -> Cotizacion:
        nivel = clasificar_nivel_estandares(empresa.num_empleados, empresa.nivel_riesgo_arl)
        spec = ESPECIFICACIONES[nivel]

        servicios = self._construir_servicios(empresa, spec)

        valor_viaticos = self._viaticos.calcular(
            ciudad_destino=empresa.ciudad,
            departamento_destino=empresa.departamento,
            horas_proyecto=spec.horas_base,
        )

        return Cotizacion(
            id_empresa=empresa.id_empresa,
            nivel_estandares=nivel,
            num_empleados_cotizados=empresa.num_empleados,
            nivel_riesgo=empresa.nivel_riesgo_arl,
            servicios_incluidos=servicios,
            valor_viaticos=valor_viaticos,
            creado_por=creado_por,
        )

    def _construir_servicios(
        self,
        empresa: EmpresaProspecto,
        spec: EspecificacionNivel,
    ) -> list[ServicioCotizado]:
        horas_totales = self._calcular_horas_totales(spec, empresa.num_empleados)
        n = len(spec.descripcion_servicios)
        horas_base_por_servicio = horas_totales // n
        # Distribuye el remanente de la división entera en los primeros servicios
        remanente = horas_totales % n

        servicios = []
        for i, descripcion in enumerate(spec.descripcion_servicios):
            horas = horas_base_por_servicio + (1 if i < remanente else 0)
            servicios.append(ServicioCotizado(
                nombre=descripcion.split("(")[0].strip().rstrip(",").rstrip(" —"),
                descripcion=descripcion,
                cantidad_horas=max(1, horas),
                valor_unitario=self.VALOR_HORA_COP,
            ))
        return servicios

    def _calcular_horas_totales(self, spec: EspecificacionNivel, num_empleados: int) -> int:
        # Incremento de horas proporcional al número de trabajadores por encima del umbral mínimo del nivel
        exceso = max(0, num_empleados - 10)
        horas_extra = int(exceso * float(spec.factor_por_empleado_cop) / float(self.VALOR_HORA_COP))
        return spec.horas_base + horas_extra

    def agregar_servicios_adicionales(
        self,
        cotizacion: Cotizacion,
        claves: list[str],
    ) -> Cotizacion:
        """Añade servicios especializados opcionales a una cotización existente."""
        for clave in claves:
            info = SERVICIOS_ADICIONALES.get(clave)
            if not info:
                continue
            horas = int(
                info["horas_base"]
                + float(info["factor_por_empleado"]) * cotizacion.num_empleados_cotizados
            )
            cotizacion.servicios_incluidos.append(ServicioCotizado(
                nombre=info["nombre"],
                descripcion=info["descripcion"],
                cantidad_horas=max(1, horas),
                valor_unitario=self.VALOR_HORA_COP,
            ))
        return cotizacion

    @staticmethod
    def describir_clasificacion(empresa: EmpresaProspecto) -> str:
        nivel = clasificar_nivel_estandares(empresa.num_empleados, empresa.nivel_riesgo_arl)
        spec = ESPECIFICACIONES[nivel]
        return (
            f"{spec.articulo_resolucion} · {spec.num_estandares} estándares — "
            f"{empresa.num_empleados} trabajadores, Riesgo {empresa.nivel_riesgo_arl.value}"
        )
