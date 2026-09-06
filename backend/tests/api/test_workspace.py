"""The /api/workspace coverage endpoint. The real Chroma call is stubbed."""

import pytest

from src import app as app_module


@pytest.fixture(autouse=True)
def _stub_stats(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_workspace_stats",
        lambda session: {
            "documents": ["pto-and-leave-policy.pdf", "code-of-conduct.pdf"],
            "document_count": 2,
            "chunk_count": 137,
        },
    )


def test_workspace_returns_coverage(client):
    resp = client.get("/api/workspace")
    assert resp.status_code == 200
    assert resp.json() == {
        "documents": ["pto-and-leave-policy.pdf", "code-of-conduct.pdf"],
        "document_count": 2,
        "chunk_count": 137,
    }
