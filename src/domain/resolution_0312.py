"""
Reglas de negocio de la Resolución 0312 de 2019 del Ministerio del Trabajo de Colombia.
Define la matriz de clasificación y las especificaciones de cada nivel de estándares.
"""
from dataclasses import dataclass
from decimal import Decimal

from .entities import NivelEstandares, NivelRiesgo

_RIESGOS_ALTOS = {NivelRiesgo.IV, NivelRiesgo.V}


def clasificar_nivel_estandares(num_empleados: int, nivel_riesgo: NivelRiesgo) -> NivelEstandares:
    """
    Matriz de aplicación — Resolución 0312/2019:
      · 1–10 trabajadores, Riesgo I/II/III       →  7 estándares  (Art. 3)
      · 11–50 trabajadores, Riesgo I/II/III      → 21 estándares  (Art. 16)
      · >50 trabajadores (cualquier riesgo)      → 60 estándares  (Art. 27)
      · 1–50 trabajadores, Riesgo IV/V           → 60 estándares  (Art. 27)
    """
    if nivel_riesgo in _RIESGOS_ALTOS:
        return NivelEstandares.NIVEL_60
    if num_empleados > 50:
        return NivelEstandares.NIVEL_60
    if num_empleados <= 10:
        return NivelEstandares.NIVEL_7
    return NivelEstandares.NIVEL_21


@dataclass(frozen=True)
class EspecificacionNivel:
    nivel: NivelEstandares
    num_estandares: int
    articulo_resolucion: str
    descripcion_legal: str
    horas_base: int
    valor_base_cop: Decimal
    # Incremento en COP por cada trabajador sobre el umbral mínimo del nivel
    factor_por_empleado_cop: Decimal
    descripcion_servicios: tuple[str, ...]


ESPECIFICACIONES: dict[NivelEstandares, EspecificacionNivel] = {

    NivelEstandares.NIVEL_7: EspecificacionNivel(
        nivel=NivelEstandares.NIVEL_7,
        num_estandares=7,
        articulo_resolucion="Artículo 3",
        descripcion_legal=(
            "Empresas de 1 a 10 trabajadores clasificadas en riesgo I, II o III. "
            "Deben cumplir con los 7 estándares mínimos del SG-SST."
        ),
        horas_base=24,
        valor_base_cop=Decimal("1_900_000"),
        factor_por_empleado_cop=Decimal("60_000"),
        descripcion_servicios=(
            "Diagnóstico inicial del SG-SST (lista de verificación 7 estándares)",
            "Diseño de política y objetivos de SST",
            "Elaboración del plan de trabajo anual",
            "Identificación de peligros y valoración de riesgos básica",
            "Capacitación introductoria en SST (4 horas)",
            "Programa de inspecciones de seguridad",
            "Entrega de documentación digital (PDF editable)",
        ),
    ),

    NivelEstandares.NIVEL_21: EspecificacionNivel(
        nivel=NivelEstandares.NIVEL_21,
        num_estandares=21,
        articulo_resolucion="Artículo 16",
        descripcion_legal=(
            "Empresas de 11 a 50 trabajadores clasificadas en riesgo I, II o III. "
            "Deben cumplir con los 21 estándares mínimos del SG-SST."
        ),
        horas_base=72,
        valor_base_cop=Decimal("4_500_000"),
        factor_por_empleado_cop=Decimal("45_000"),
        descripcion_servicios=(
            "Diagnóstico inicial del SG-SST (lista de verificación 21 estándares)",
            "Diseño y documentación completa del SG-SST",
            "Matriz de identificación de peligros y valoración de riesgos (GTC-45)",
            "Plan de emergencias y evacuación",
            "Programa de medicina preventiva del trabajo",
            "Plan de capacitación anual en SST (20 horas)",
            "Indicadores del SG-SST (estructura, proceso y resultado)",
            "Programa de mantenimiento preventivo de equipos e instalaciones",
            "Acompañamiento en primera auditoría interna del SG-SST",
            "Entrega de documentación digital y física",
        ),
    ),

    NivelEstandares.NIVEL_60: EspecificacionNivel(
        nivel=NivelEstandares.NIVEL_60,
        num_estandares=60,
        articulo_resolucion="Artículo 27",
        descripcion_legal=(
            "Empresas con más de 50 trabajadores (cualquier riesgo) o empresas de 1 a 50 "
            "trabajadores clasificadas en riesgo IV o V. "
            "Deben cumplir con los 60 estándares mínimos del SG-SST."
        ),
        horas_base=200,
        valor_base_cop=Decimal("9_800_000"),
        factor_por_empleado_cop=Decimal("28_000"),
        descripcion_servicios=(
            "Diagnóstico inicial del SG-SST (lista de verificación 60 estándares)",
            "Diseño e implementación integral del SG-SST",
            "Sistema de vigilancia epidemiológica (SVE) para riesgos prioritarios",
            "Programa de riesgo psicosocial (Batería de instrumentos MinTrabajo)",
            "Plan de gestión del cambio y control de proveedores",
            "Programa de higiene y seguridad industrial",
            "Auditoría interna del SG-SST",
            "Revisión por la alta dirección",
            "Plan de mejoramiento continuo post-auditoría",
            "Capacitación especializada en SST (40 horas curriculares)",
            "Entrega de documentación digital y física completa",
        ),
    ),
}
