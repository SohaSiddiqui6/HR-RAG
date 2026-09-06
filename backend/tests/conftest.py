import pytest
from fastapi.testclient import TestClient

from src import config
from src.app import app
from src.db.session import init_db, reset_engine


@pytest.fixture(autouse=True)
def _db():
    """Fresh in-memory SQLite for every test — no Postgres, no shared state."""
    config.DATABASE_URL = "sqlite://"
    reset_engine()
    init_db()
    yield
    reset_engine()


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client
