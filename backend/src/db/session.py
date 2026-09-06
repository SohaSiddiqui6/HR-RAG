"""Database engine and session wiring.

``DATABASE_URL`` is a Postgres connection string in prod (Supabase); tests set it
to ``sqlite://`` (in-memory). SQLModel keeps the queries dialect-agnostic.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, inspect
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
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _add_missing_columns(engine)


# Columns added after a table was first created. `create_all` only creates whole
# tables, so on an existing DB these need adding explicitly. Forward-only and
# idempotent — enough for a project this size without a migration tool.
_ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "message": {
        "outcome": "VARCHAR NOT NULL DEFAULT 'answered'",
        "escalation": "JSON",  # JSONB on Postgres (see below)
        "trace_id": "VARCHAR",
    },
}


def _add_missing_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    is_postgres = engine.dialect.name == "postgresql"

    for table, columns in _ADDED_COLUMNS.items():
        if table not in tables:
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        with engine.begin() as conn:
            for name, ddl in columns.items():
                if name in existing:
                    continue
                if is_postgres:
                    ddl = ddl.replace("JSON", "JSONB")
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
