"""The POST /api/ingest trigger. The real Docling -> Chroma pipeline is stubbed."""

import pytest

# The endpoint lazily imports src.rag.ingest, which pulls in docling / transformers;
# skip cleanly when those extras are not installed.
ingest_module = pytest.importorskip("src.rag.ingest")


@pytest.fixture(autouse=True)
def _stub_run_ingestion(monkeypatch):
    monkeypatch.setattr(
        ingest_module,
        "run_ingestion",
        lambda: {
            "processed": ["remote-work-policy.pdf"],
            "skipped": ["code-of-conduct.pdf"],
            "chunks_upserted": 42,
            "collection_count": 137,
        },
    )


def test_ingest_returns_run_summary(client):
    resp = client.post("/api/ingest")
    assert resp.status_code == 200
    assert resp.json() == {
        "processed": ["remote-work-policy.pdf"],
        "skipped": ["code-of-conduct.pdf"],
        "chunks_upserted": 42,
        "collection_count": 137,
    }


def test_ingest_400_when_no_pdfs(client, monkeypatch):
    def _raise():
        raise FileNotFoundError("No PDFs found in /app/docs")

    monkeypatch.setattr(ingest_module, "run_ingestion", _raise)

    resp = client.post("/api/ingest")
    assert resp.status_code == 400
    assert resp.json() == {"error": "No PDFs found in /app/docs"}
