"""
Scheduler autónomo — ejecuta tareas programadas sin que el software esté abierto en pantalla.

Tareas programadas:
  - 08:00 todos los días → cadencia de correos (Día 4 + Día 8 automáticos)

Cómo funciona:
  - Se inicia junto con el software desde start.bat (ventana minimizada)
  - Escribe resultados en data/scheduler_log.json
  - El panel Campañas lee ese archivo para mostrar estado en tiempo real
"""
import json
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import schedule

_LOG_PATH = _ROOT / "data" / "scheduler_log.json"
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Scheduler] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def _guardar_log(datos: dict) -> None:
    _LOG_PATH.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def tarea_cadencia() -> None:
    """Ejecuta la cadencia automática de correos (Día 4 + Día 8)."""
    inicio = datetime.now()
    log.info("Iniciando cadencia automática...")

    resultado = {
        "ultima_ejecucion": inicio.strftime("%Y-%m-%d %H:%M:%S"),
        "dia4":             0,
        "dia8":             0,
        "correos_enviados": 0,
        "errores":          [],
        "estado":           "en_progreso",
    }
    _guardar_log(resultado)

    try:
        from src.modules.outreach.sequence_orchestrator import SequenceOrchestrator

        resultados = SequenceOrchestrator().procesar_pendientes(creado_por="Scheduler")
        dia4    = [r for r in resultados if r.ok and r.accion == "DIA_4"]
        dia8    = [r for r in resultados if r.ok and r.accion == "DIA_8"]
        errores = [f"{r.razon_social}: {r.error}" for r in resultados if not r.ok and r.error]

        resultado.update({
            "dia4":             len(dia4),
            "dia8":             len(dia8),
            "correos_enviados": len(dia4) + len(dia8),
            "errores":          errores,
            "estado":           "completado",
            "duracion_s":       round((datetime.now() - inicio).total_seconds(), 1),
        })
        log.info(f"Cadencia completada — Día 4: {len(dia4)} · Día 8: {len(dia8)}")

    except Exception as exc:
        resultado.update({"estado": "error", "errores": [str(exc)]})
        log.error(f"Error en cadencia: {exc}")

    _guardar_log(resultado)


def main() -> None:
    log.info("=" * 50)
    log.info("  Medina SST — Scheduler Autónomo activo")
    log.info("  Cadencia programada: todos los días 08:00")
    log.info("=" * 50)

    schedule.every().day.at("08:00").do(tarea_cadencia)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
