from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_config


def _build_engine():
    cfg = get_config()
    # SQLite requires check_same_thread=False for use across threads
    connect_args = {"check_same_thread": False} if cfg.db_url.startswith("sqlite") else {}
    return create_engine(cfg.db_url, connect_args=connect_args, echo=False)


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
