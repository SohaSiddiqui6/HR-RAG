"""Database engine and session wiring.

``DATABASE_URL`` is a Postgres connection string in prod (Supabase); tests set it
to ``sqlite://`` (in-memory). SQLModel keeps the queries dialect-agnostic.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src import config
from src.db import models  # noqa: F401 — registers the tables on SQLModel.metadata

_engine: Engine | None = None


def _build_engine() -> Engine:
    url = config.DATABASE_URL
    if not url:
        raise RuntimeError("DATABASE_URL is not set (see .env.example)")
    if url.startswith("sqlite"):
        # One shared in-memory DB for the process (used by tests).
        return create_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    # Route bare postgres URLs through psycopg 3.
    return create_engine(url.replace("postgresql://", "postgresql+psycopg://", 1))


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def reset_engine() -> None:
    """Drop the cached engine so the next call rebuilds from the current URL (tests)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def init_db() -> None:
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
