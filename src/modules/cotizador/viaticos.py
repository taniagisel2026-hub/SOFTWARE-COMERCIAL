from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from ...config import get_config
from ...data.ciudades_colombia import CIUDADES, ZonaViaticos


@dataclass(frozen=True)
class TarifaViaticos:
    zona: ZonaViaticos
    descripcion: str
    valor_por_visita: Decimal


_TARIFAS: dict[ZonaViaticos, TarifaViaticos] = {
    ZonaViaticos.MISMA_CIUDAD: TarifaViaticos(
        zona=ZonaViaticos.MISMA_CIUDAD,
        descripcion="Sin viáticos (misma ciudad base)",
        valor_por_visita=Decimal("0"),
    ),
    ZonaViaticos.MISMO_DEPARTAMENTO: TarifaViaticos(
        zona=ZonaViaticos.MISMO_DEPARTAMENTO,
        descripcion="Viaje de día — mismo departamento (transporte + alimentación)",
        valor_por_visita=Decimal("130_000"),
    ),
    ZonaViaticos.DIFERENTE_DEPARTAMENTO: TarifaViaticos(
        zona=ZonaViaticos.DIFERENTE_DEPARTAMENTO,
        descripcion="Viaje con pernocta — diferente departamento (tiquete + hotel + viáticos)",
        valor_por_visita=Decimal("380_000"),
    ),
    ZonaViaticos.ZONA_REMOTA: TarifaViaticos(
        zona=ZonaViaticos.ZONA_REMOTA,
        descripcion="Zona remota — requiere transporte aéreo (tiquete + hotel + viáticos x3 días)",
        valor_por_visita=Decimal("680_000"),
    ),
}

# Una visita de campo por cada 20 horas de trabajo estimado
_HORAS_POR_VISITA = 20


class ViaticosCalculator:

    def __init__(self, ciudad_base: Optional[str] = None, departamento_base: Optional[str] = None):
        cfg = get_config()
        self._ciudad_base = (ciudad_base or cfg.ciudad_base).lower()
        self._departamento_base = (departamento_base or cfg.departamento_base).lower()

    def calcular(
        self,
        ciudad_destino: str,
        departamento_destino: str,
        horas_proyecto: int,
    ) -> Decimal:
        zona = self._determinar_zona(ciudad_destino, departamento_destino)
        tarifa = _TARIFAS[zona]
        if tarifa.valor_por_visita == Decimal("0"):
            return Decimal("0")
        num_visitas = max(1, horas_proyecto // _HORAS_POR_VISITA)
        return tarifa.valor_por_visita * num_visitas

    def describir_zona(self, ciudad_destino: str, departamento_destino: str) -> str:
        zona = self._determinar_zona(ciudad_destino, departamento_destino)
        return _TARIFAS[zona].descripcion

    def _determinar_zona(self, ciudad_destino: str, departamento_destino: str) -> ZonaViaticos:
        if ciudad_destino.lower() == self._ciudad_base:
            return ZonaViaticos.MISMA_CIUDAD

        ciudad_info = CIUDADES.get(ciudad_destino.lower())
        if ciudad_info and ciudad_info.zona_remota:
            return ZonaViaticos.ZONA_REMOTA

        if departamento_destino.lower() == self._departamento_base:
            return ZonaViaticos.MISMO_DEPARTAMENTO

        return ZonaViaticos.DIFERENTE_DEPARTAMENTO
