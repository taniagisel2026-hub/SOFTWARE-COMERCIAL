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
    El canal EMAIL sube de volumen solo, semana a semana, según _CALENTAMIENTO_EMAIL
    (calentamiento de cuenta Gmail/Workspace nueva). Un valor explícito en
    MAX_EMAIL_DIA/DELAY_EMAIL_MIN/DELAY_EMAIL_MAX (.env) o al construir RateLimiter
    anula el calentamiento automático para ese envío.
    """

    _CANAL_DEFAULTS = {
        "EMAIL":     {"max_dia": 10,  "delay_min": 120, "delay_max": 300},
        "WHATSAPP":  {"max_dia": 30,  "delay_min": 30,  "delay_max": 120},
    }

    # Calentamiento gradual del canal EMAIL: (día desde el inicio, max_dia, delay_min_s, delay_max_s).
    # El delay baja junto con el volumen para que el envío del día siga cabiendo
    # dentro de una jornada laboral (el scheduler corre una vez a las 8:30 a.m.).
    _CALENTAMIENTO_EMAIL = [
        (0,  10, 120, 300),
        (7,  20, 100, 250),
        (14, 35,  90, 220),
        (21, 55,  75, 190),
        (28, 80,  60, 160),
        (35, 120, 45, 130),
        (42, 180, 35, 100),
        (49, 250, 30,  90),
    ]
    # Fecha en que la cuenta Gmail empezó el calentamiento actual (10/día, commit bfe96ea).
    _INICIO_CALENTAMIENTO = date.fromisoformat(
        os.getenv("EMAIL_WARMUP_INICIO", "2026-06-30")
    )

    def __init__(
        self,
        max_dia: int | None = None,
        delay_min_s: int | None = None,
        delay_max_s: int | None = None,
    ):
        self._override_max = max_dia
        self._override_min = delay_min_s
        self._override_max_delay = delay_max_s

    @classmethod
    def _tramo_vigente(cls, canal: str) -> tuple[int, int, int] | None:
        """Retorna (max_dia, delay_min, delay_max) del tramo de calentamiento vigente hoy."""
        if canal != "EMAIL":
            return None
        dias = (date.today() - cls._INICIO_CALENTAMIENTO).days
        tramo = cls._CALENTAMIENTO_EMAIL[0]
        for candidato in cls._CALENTAMIENTO_EMAIL:
            if dias >= candidato[0]:
                tramo = candidato
        return tramo[1], tramo[2], tramo[3]

    def verificar(self, canal: str) -> None:
        """Lanza RateLimitExceededError si se alcanzó el límite diario del canal."""
        defaults = self._CANAL_DEFAULTS.get(canal, self._CANAL_DEFAULTS["EMAIL"])
        tramo = self._tramo_vigente(canal)
        max_dia_hoy = tramo[0] if tramo else defaults["max_dia"]

        max_dia = (
            self._override_max
            or int(os.getenv(f"MAX_{canal}_DIA", max_dia_hoy))
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
                f"Ajusta MAX_{canal}_DIA en .env para forzar otro umbral."
            )

    def aplicar_delay(self, canal: str = "EMAIL") -> float:
        """Pausa aleatoria entre envíos para simular comportamiento humano."""
        defaults = self._CANAL_DEFAULTS.get(canal, self._CANAL_DEFAULTS["EMAIL"])
        tramo = self._tramo_vigente(canal)
        delay_min_hoy = tramo[1] if tramo else defaults["delay_min"]
        delay_max_hoy = tramo[2] if tramo else defaults["delay_max"]

        d_min = self._override_min or int(os.getenv(f"DELAY_{canal}_MIN", delay_min_hoy))
        d_max = self._override_max_delay or int(os.getenv(f"DELAY_{canal}_MAX", delay_max_hoy))

        segundos = random.uniform(d_min, d_max)
        time.sleep(segundos)
        return round(segundos, 1)
