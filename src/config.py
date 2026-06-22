import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


@dataclass(frozen=True)
class AppConfig:
    db_url: str
    ciudad_base: str
    departamento_base: str
    empresa_nombre: str
    empresa_nit: str
    empresa_telefono: str
    empresa_email: str
    output_dir: Path
    gemini_api_key: str
    gemini_model: str
    asesora_nombre: str


_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _dotenv = BASE_DIR / ".env"
        if _dotenv.exists():
            from dotenv import load_dotenv
            load_dotenv(_dotenv)
        _config = AppConfig(
            db_url=os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'comercial.db'}",
            ciudad_base=os.getenv("CIUDAD_BASE", "Bogotá D.C."),
            departamento_base=os.getenv("DEPARTAMENTO_BASE", "Cundinamarca"),
            empresa_nombre=os.getenv("EMPRESA_NOMBRE", "Medina SST Empresarial SAS"),
            empresa_nit=os.getenv("EMPRESA_NIT", ""),
            empresa_telefono=os.getenv("EMPRESA_TELEFONO", ""),
            empresa_email=os.getenv("EMPRESA_EMAIL", ""),
            output_dir=Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "output"))),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            asesora_nombre=os.getenv("ASESORA_NOMBRE", "Tania Peñaloza"),
        )
    return _config
