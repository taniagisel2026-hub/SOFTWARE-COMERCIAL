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

_LOG_PATH    = _ROOT / "data" / "scheduler_log.json"
_CONFIG_PATH = _ROOT / "data" / "scheduler_config.json"
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _auto_dia1_activo() -> bool:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8")).get("auto_dia1", False)
    except Exception:
        return False

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
    """Ejecuta la cadencia completa: Día 1 (nuevos prospectos) + Día 4 + Día 8."""
    inicio = datetime.now()
    log.info("Iniciando cadencia automática completa (Día 1 + Día 4 + Día 8)...")

    resultado = {
        "ultima_ejecucion": inicio.strftime("%Y-%m-%d %H:%M:%S"),
        "dia1":             0,
        "dia4":             0,
        "dia8":             0,
        "correos_enviados": 0,
        "errores":          [],
        "estado":           "en_progreso",
    }
    _guardar_log(resultado)

    try:
        from src.modules.outreach.sequence_orchestrator import SequenceOrchestrator

        resultados = SequenceOrchestrator().procesar_pendientes(
            creado_por="Scheduler",
            incluir_dia1=_auto_dia1_activo(),
        )
        dia1    = [r for r in resultados if r.ok and r.accion == "DIA_1"]
        dia4    = [r for r in resultados if r.ok and r.accion == "DIA_4"]
        dia8    = [r for r in resultados if r.ok and r.accion == "DIA_8"]
        errores = [f"{r.razon_social}: {r.error}" for r in resultados if not r.ok and r.error]

        resultado.update({
            "dia1":             len(dia1),
            "dia4":             len(dia4),
            "dia8":             len(dia8),
            "correos_enviados": len(dia1) + len(dia4) + len(dia8),
            "errores":          errores,
            "estado":           "completado",
            "duracion_s":       round((datetime.now() - inicio).total_seconds(), 1),
        })
        log.info(f"Cadencia completada — Día 1: {len(dia1)} · Día 4: {len(dia4)} · Día 8: {len(dia8)}")

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
