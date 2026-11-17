"""Database setup. SQLite for dev; set DATABASE_URL to a postgresql:// URL to migrate."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

_url = get_settings().database_url
_engine_kwargs = {"connect_args": {"check_same_thread": False}} if _url.startswith("sqlite") else {}
engine = create_engine(_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import tables  # noqa: F401  (register models)
    Base.metadata.create_all(engine)
