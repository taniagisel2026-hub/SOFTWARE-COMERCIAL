"""
Scheduler autónomo — ejecuta tareas programadas sin intervención manual.

Tareas programadas:
  - 07:00 sábado   → extracción Facatativá (todos los sectores)
  - 07:00 domingo  → extracción Fusagasugá (todos los sectores)
  - 07:00 lunes    → extracción Zipaquirá  (todos los sectores)
  - 08:30 diario   → cadencia de correos (Día 1 + Día 4 + Día 8)
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

_LOG_PATH        = _ROOT / "data" / "scheduler_log.json"
_LOG_EXTRAC_PATH = _ROOT / "data" / "scheduler_extraccion_log.json"
_CONFIG_PATH     = _ROOT / "data" / "scheduler_config.json"
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

_SECTORES = [
    "Construcción", "Manufactura / Industria", "Transporte y Logística",
    "Comercio y Retail", "Servicios Empresariales", "Salud y Clínicas",
    "Minería y Energía", "Tecnología y Software", "Alimentos y Bebidas",
    "Seguridad Privada", "Hotelería y Turismo", "Petróleo y Gas",
    "Ingeniería y Consultoría", "Farmacéutico y Químico", "Telecomunicaciones",
    "Entretenimiento y Eventos",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Scheduler] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def _auto_dia1_activo() -> bool:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8")).get("auto_dia1", False)
    except Exception:
        return False


def _guardar_log(datos: dict) -> None:
    _LOG_PATH.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def _guardar_log_extraccion(datos: dict) -> None:
    _LOG_EXTRAC_PATH.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def tarea_extraccion(ciudad: str) -> None:
    """Extrae empresas de todos los sectores en la ciudad indicada (sin enviar correos)."""
    inicio = datetime.now()
    log.info(f"Iniciando extracción automática — ciudad: {ciudad}")

    resultado = {
        "ultima_ejecucion": inicio.strftime("%Y-%m-%d %H:%M:%S"),
        "ciudad": ciudad,
        "empresas_nuevas": 0,
        "sectores_procesados": 0,
        "errores": [],
        "estado": "en_progreso",
    }
    _guardar_log_extraccion(resultado)

    try:
        from src.modules.scraper.pipeline import ProspectionPipeline
        pipeline = ProspectionPipeline()

        total_nuevas = 0
        for sector in _SECTORES:
            try:
                r = pipeline.ejecutar(
                    ciudad=ciudad,
                    sector=sector,
                    max_por_fuente=30,
                    disparar_emails=False,
                    usar_linkedin=False,
                )
                total_nuevas += r.empresas_nuevas
                resultado["sectores_procesados"] += 1
                log.info(f"  [{sector}] {r.empresas_nuevas} nuevas")
            except Exception as exc:
                resultado["errores"].append(f"{sector}: {exc}")
                log.warning(f"  [{sector}] Error: {exc}")

        resultado.update({
            "empresas_nuevas": total_nuevas,
            "estado": "completado",
            "duracion_s": round((datetime.now() - inicio).total_seconds(), 1),
        })
        log.info(f"Extracción completada — {ciudad}: {total_nuevas} empresas nuevas")

    except Exception as exc:
        resultado.update({"estado": "error", "errores": [str(exc)]})
        log.error(f"Error en extracción: {exc}")

    _guardar_log_extraccion(resultado)


def tarea_cadencia() -> None:
    """Ejecuta la cadencia completa: Día 1 (nuevos prospectos) + Día 4 + Día 8."""
    inicio = datetime.now()
    log.info("Iniciando cadencia automática completa (Día 1 + Día 4 + Día 8)...")

    resultado = {
        "ultima_ejecucion": inicio.strftime("%Y-%m-%d %H:%M:%S"),
        "dia1": 0,
        "dia4": 0,
        "dia8": 0,
        "correos_enviados": 0,
        "errores": [],
        "estado": "en_progreso",
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
        errores = [f"{r.razon_social}: {r.mensaje}" for r in resultados if not r.ok and r.mensaje]

        resultado.update({
            "dia1": len(dia1),
            "dia4": len(dia4),
            "dia8": len(dia8),
            "correos_enviados": len(dia1) + len(dia4) + len(dia8),
            "errores": errores,
            "estado": "completado",
            "duracion_s": round((datetime.now() - inicio).total_seconds(), 1),
        })
        log.info(f"Cadencia completada — Día 1: {len(dia1)} · Día 4: {len(dia4)} · Día 8: {len(dia8)}")

    except Exception as exc:
        resultado.update({"estado": "error", "errores": [str(exc)]})
        log.error(f"Error en cadencia: {exc}")

    _guardar_log(resultado)


def main() -> None:
    log.info("=" * 55)
    log.info("  Medina SST — Scheduler Autónomo activo")
    log.info("  Extracción: 09:30 sáb=Facatativá · dom=Fusagasugá · lun=Zipaquirá")
    log.info("  Cadencia:   todos los días 08:30")
    log.info("=" * 55)

    # Extracciones por día de la semana (después del envío de correos)
    schedule.every().saturday.at("09:30").do(tarea_extraccion, ciudad="Facatativá")
    schedule.every().sunday.at("09:30").do(tarea_extraccion,   ciudad="Fusagasugá")
    schedule.every().monday.at("09:30").do(tarea_extraccion,   ciudad="Zipaquirá")

    # Cadencia de correos diaria
    schedule.every().day.at("08:30").do(tarea_cadencia)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
