import os
import random
import time
from datetime import date

from sqlalchemy import func

from ...database.connection import get_session
from ...database.models import HistorialInteracciones


class RateLimitExceededError(Exception):
    pass


class RateLimiter:
    """
    Controla el volumen y cadencia de envíos para evitar bloqueos por spam.
    Los límites por defecto son conservadores para cuentas Gmail / WhatsApp Business nuevas.
    Pueden aumentarse gradualmente vía variables de entorno una vez calentada la cuenta.
    """

    _CANAL_DEFAULTS = {
        "EMAIL":     {"max_dia": 50,  "delay_min": 45,  "delay_max": 180},
        "WHATSAPP":  {"max_dia": 30,  "delay_min": 30,  "delay_max": 120},
    }

    def __init__(
        self,
        max_dia: int | None = None,
        delay_min_s: int | None = None,
        delay_max_s: int | None = None,
    ):
        self._override_max = max_dia
        self._override_min = delay_min_s
        self._override_max_delay = delay_max_s

    def verificar(self, canal: str) -> None:
        """Lanza RateLimitExceededError si se alcanzó el límite diario del canal."""
        defaults = self._CANAL_DEFAULTS.get(canal, self._CANAL_DEFAULTS["EMAIL"])
        max_dia = (
            self._override_max
            or int(os.getenv(f"MAX_{canal}_DIA", defaults["max_dia"]))
        )

        with get_session() as session:
            enviados_hoy = (
                session.query(HistorialInteracciones)
                .filter(
                    HistorialInteracciones.canal == canal,
                    func.date(HistorialInteracciones.fecha_interaccion) == date.today(),
                    HistorialInteracciones.estado_respuesta == "ENVIADO",
                )
                .count()
            )

        if enviados_hoy >= max_dia:
            raise RateLimitExceededError(
                f"Límite diario alcanzado para {canal}: {enviados_hoy}/{max_dia}. "
                f"Ajusta MAX_{canal}_DIA en .env para modificar el umbral."
            )

    def aplicar_delay(self, canal: str = "EMAIL") -> float:
        """Pausa aleatoria entre envíos para simular comportamiento humano."""
        defaults = self._CANAL_DEFAULTS.get(canal, self._CANAL_DEFAULTS["EMAIL"])
        d_min = self._override_min or int(os.getenv(f"DELAY_{canal}_MIN", defaults["delay_min"]))
        d_max = self._override_max_delay or int(os.getenv(f"DELAY_{canal}_MAX", defaults["delay_max"]))

        segundos = random.uniform(d_min, d_max)
        time.sleep(segundos)
        return round(segundos, 1)
