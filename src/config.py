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
    anthropic_api_key: str
    anthropic_model: str


_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _dotenv = BASE_DIR / ".env"
        if _dotenv.exists():
            from dotenv import load_dotenv
            load_dotenv(_dotenv)
        _config = AppConfig(
            db_url=os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'comercial.db'}"),
            ciudad_base=os.getenv("CIUDAD_BASE", "Bogotá D.C."),
            departamento_base=os.getenv("DEPARTAMENTO_BASE", "Cundinamarca"),
            empresa_nombre=os.getenv("EMPRESA_NOMBRE", "Medina SST Empresarial SAS"),
            empresa_nit=os.getenv("EMPRESA_NIT", ""),
            empresa_telefono=os.getenv("EMPRESA_TELEFONO", ""),
            empresa_email=os.getenv("EMPRESA_EMAIL", "taniagisel2026@gmail.com"),
            output_dir=Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "output"))),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        )
    return _config
