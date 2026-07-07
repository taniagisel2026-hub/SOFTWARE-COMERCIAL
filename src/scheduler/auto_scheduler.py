"""
Scheduler autónomo — ejecuta tareas programadas sin intervención manual.

Tareas programadas:
  - 08:30 lunes a viernes → cadencia de correos (Día 1 + Día 4 + Día 8)
  - 14:00 lunes a viernes → extracción de prospectos (1 municipio/día, rotativo)
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

# ── Extracción de prospectos: rotación 1 municipio/día ───────────────────────
# Mismo orden que _REGIONES["Bogotá + Cundinamarca"] en src/frontend/pages/scraper.py.
# Los primeros 5 ya se extrajeron manualmente antes de automatizar esto (2026-07-06);
# se dejan primero en la lista para que, al completar el ciclo, se retomen en el
# mismo orden en que se hicieron.
_MUNICIPIOS_SCRAPING = [
    "Bogotá D.C.", "Soacha", "Chía", "Cota", "Facatativá",
    "Fusagasugá", "Zipaquirá", "Villeta", "Girardot", "Mosquera",
    "La Vega", "Cajicá", "Sopó", "La Calera", "Guaduas",
    "Flandes", "Tocancipá", "Madrid", "Sibaté",
]

# Mismos 16 sectores que _SECTORES en src/frontend/pages/scraper.py.
_SECTORES_SCRAPING = [
    "Construcción", "Manufactura / Industria", "Transporte y Logística",
    "Comercio y Retail", "Servicios Empresariales", "Salud y Clínicas",
    "Minería y Energía", "Tecnología y Software", "Alimentos y Bebidas",
    "Seguridad Privada", "Hotelería y Turismo", "Petróleo y Gas",
    "Ingeniería y Consultoría", "Farmacéutico y Químico", "Telecomunicaciones",
    "Entretenimiento y Eventos",
]

_MAX_POR_FUENTE_SCRAPING = 30

_ESTADO_SCRAPING_PATH = _ROOT / "data" / "scraper_scheduler_estado.json"
_LOG_SCRAPING_PATH    = _ROOT / "data" / "scraper_scheduler_log.json"

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


def _leer_indice_municipio() -> int:
    try:
        return json.loads(_ESTADO_SCRAPING_PATH.read_text(encoding="utf-8")).get("indice", 0)
    except Exception:
        return 0


def _guardar_indice_municipio(indice: int) -> None:
    _ESTADO_SCRAPING_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ESTADO_SCRAPING_PATH.write_text(
        json.dumps({"indice": indice}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _guardar_log_scraping(datos: dict) -> None:
    _LOG_SCRAPING_PATH.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


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


def tarea_scraping() -> None:
    """
    Extrae prospectos de UN municipio por día (rotación fija en _MUNICIPIOS_SCRAPING),
    recorriendo los 16 sectores económicos para ese municipio (Google Maps + WebScraper,
    sin LinkedIn porque su sesión guardada caduca y no se puede renovar sola).

    No dispara correos (disparar_emails=False) — el Día 1 queda centralizado en
    tarea_cadencia() de las 8:30am, que ya tiene protección anti-duplicados.
    Al terminar el municipio de hoy, avanza el índice para mañana; al llegar al
    final de la lista, vuelve a empezar desde el primero.
    """
    inicio = datetime.now()
    indice = _leer_indice_municipio() % len(_MUNICIPIOS_SCRAPING)
    municipio = _MUNICIPIOS_SCRAPING[indice]
    log.info(f"Iniciando extracción automática — municipio {indice + 1}/{len(_MUNICIPIOS_SCRAPING)}: {municipio}")

    resultado = {
        "ultima_ejecucion": inicio.strftime("%Y-%m-%d %H:%M:%S"),
        "municipio": municipio,
        "sectores_procesados": 0,
        "empresas_nuevas": 0,
        "empresas_existentes": 0,
        "errores": [],
        "estado": "en_progreso",
    }
    _guardar_log_scraping(resultado)

    total_nuevas = 0
    total_existentes = 0
    errores: list[str] = []

    try:
        from src.modules.scraper.pipeline import ProspectionPipeline
        pipeline = ProspectionPipeline()

        for sector in _SECTORES_SCRAPING:
            try:
                r = pipeline.ejecutar(
                    ciudad=municipio,
                    sector=sector,
                    max_por_fuente=_MAX_POR_FUENTE_SCRAPING,
                    disparar_emails=False,
                    usar_gmaps=True,
                    usar_linkedin=False,
                    usar_webscraper=True,
                )
                total_nuevas += r.empresas_nuevas
                total_existentes += r.empresas_existentes
                errores.extend(r.errores)
            except Exception as exc:
                errores.append(f"{sector}: {exc}")

        resultado.update({
            "sectores_procesados": len(_SECTORES_SCRAPING),
            "empresas_nuevas": total_nuevas,
            "empresas_existentes": total_existentes,
            "errores": errores[:20],
            "estado": "completado",
            "duracion_s": round((datetime.now() - inicio).total_seconds(), 1),
        })
        log.info(f"Extracción completada — {municipio}: {total_nuevas} nuevas, {total_existentes} ya existían")

        # Avanza al siguiente municipio para mañana (solo si el municipio de hoy
        # terminó, para no saltarse uno si el proceso se interrumpe a medias).
        _guardar_indice_municipio((indice + 1) % len(_MUNICIPIOS_SCRAPING))

    except Exception as exc:
        resultado.update({"estado": "error", "errores": [str(exc)]})
        log.error(f"Error en extracción automática: {exc}")

    _guardar_log_scraping(resultado)


def main() -> None:
    from src.database.init_db import create_tables, migrate_dedup_cadencia
    create_tables()
    migrate_dedup_cadencia()

    log.info("=" * 55)
    log.info("  Medina SST — Scheduler Autónomo activo")
    log.info("  Cadencia de correos: lunes a viernes 08:30")
    log.info("  Extracción de prospectos: lunes a viernes 14:00")
    log.info("=" * 55)

    schedule.every().monday.at("08:30").do(tarea_cadencia)
    schedule.every().tuesday.at("08:30").do(tarea_cadencia)
    schedule.every().wednesday.at("08:30").do(tarea_cadencia)
    schedule.every().thursday.at("08:30").do(tarea_cadencia)
    schedule.every().friday.at("08:30").do(tarea_cadencia)

    schedule.every().monday.at("14:00").do(tarea_scraping)
    schedule.every().tuesday.at("14:00").do(tarea_scraping)
    schedule.every().wednesday.at("14:00").do(tarea_scraping)
    schedule.every().thursday.at("14:00").do(tarea_scraping)
    schedule.every().friday.at("14:00").do(tarea_scraping)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
