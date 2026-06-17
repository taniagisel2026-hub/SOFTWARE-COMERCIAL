"""
Script de inicialización del esquema y carga de datos de demo.
Uso: python -m src.database.init_db
"""
from datetime import date
from pathlib import Path

from sqlalchemy import inspect, text

from .connection import engine, get_session
from .models import Base, EmpresaProspecto, ReferidoCompecer
from ..config import get_config


def create_tables() -> None:
    cfg = get_config()
    if cfg.db_url.startswith("sqlite"):
        db_path = Path(str(cfg.db_url).replace("sqlite:///", ""))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"[OK] Esquema creado en: {cfg.db_url}")


def migrate_add_opt_out() -> None:
    """Migración no destructiva para añadir columnas Habeas Data a tablas existentes."""
    if not inspect(engine).has_table("empresa_prospecto"):
        return
    existing = {col["name"] for col in inspect(engine).get_columns("empresa_prospecto")}
    pending = {
        "opt_out": "BOOLEAN NOT NULL DEFAULT 0",
        "fecha_opt_out": "DATE",
        "motivo_opt_out": "VARCHAR(300)",
    }
    with engine.connect() as conn:
        for col, definition in pending.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE empresa_prospecto ADD COLUMN {col} {definition}"))
                conn.commit()
                print(f"[MIGRACIÓN] Columna '{col}' añadida a empresa_prospecto.")


def seed_demo_data() -> None:
    with get_session() as session:
        if session.query(EmpresaProspecto).count() > 0:
            print("[SKIP] Datos de demo ya existentes.")
            return

        demo = [
            EmpresaProspecto(
                razon_social="Constructora El Progreso SAS",
                nit="900123456-1",
                sector_economico="Construcción",
                ciudad="Bogotá D.C.",
                departamento="Cundinamarca",
                num_empleados=8,
                nivel_riesgo_arl="III",
                estado_prospecto="NUEVO",
                fuente_origen="Google Maps",
                fecha_registro=date.today(),
                fecha_ultima_actualizacion=date.today(),
            ),
            EmpresaProspecto(
                razon_social="Logística Nacional LTDA",
                nit="800987654-2",
                sector_economico="Transporte y Logística",
                ciudad="Medellín",
                departamento="Antioquia",
                num_empleados=35,
                nivel_riesgo_arl="II",
                estado_prospecto="NUEVO",
                fuente_origen="LinkedIn",
                fecha_registro=date.today(),
                fecha_ultima_actualizacion=date.today(),
            ),
            EmpresaProspecto(
                razon_social="Petroquímica del Oriente SA",
                nit="860543210-3",
                sector_economico="Industria Petroquímica",
                ciudad="Barrancabermeja",
                departamento="Santander",
                num_empleados=120,
                nivel_riesgo_arl="V",
                estado_prospecto="NUEVO",
                fuente_origen="Google Maps",
                fecha_registro=date.today(),
                fecha_ultima_actualizacion=date.today(),
            ),
        ]
        session.add_all(demo)
    print("[OK] 3 empresas de demo insertadas.")


def migrate_add_referido_compecer() -> None:
    """Crea la tabla referido_compecer si no existe."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_tables()
    migrate_add_opt_out()
    migrate_add_referido_compecer()
    seed_demo_data()
