from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_config


def _build_engine():
    cfg = get_config()
    is_sqlite = cfg.db_url.startswith("sqlite")
    # SQLite requires check_same_thread=False for use across threads
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(cfg.db_url, connect_args=connect_args, echo=False)

    if is_sqlite:
        # WAL permite que el scheduler automático (proceso aparte) y el panel
        # escriban a la vez sin bloquearse mutuamente ("database is locked").
        @event.listens_for(engine, "connect")
        def _activar_wal(conexion_dbapi, _):
            cursor = conexion_dbapi.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
