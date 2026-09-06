import pytest
from sqlmodel import Session

from src import config
from src.db import store
from src.db.session import get_engine

# The ingest module pulls in docling / transformers / pymupdf; skip cleanly
# when the ingestion extras are not installed.
ingest = pytest.importorskip("src.rag.ingest")


def test_manifest_roundtrip():
    """The Postgres-backed manifest: read empty, write a row, read it back."""
    with Session(get_engine()) as session:
        assert store.get_ingest_manifest(session) == {}

        store.upsert_ingested_document(session, "a.pdf", "hash", chunk_count=3)
        assert store.get_ingest_manifest(session) == {"a.pdf": "hash"}

        # Re-ingesting the same file (new hash) replaces the row, not appends.
        store.upsert_ingested_document(session, "a.pdf", "hash2", chunk_count=5)
        manifest = store.get_ingest_manifest(session)
        assert manifest == {"a.pdf": "hash2"}
        assert session.get(store.IngestedDocument, "a.pdf").chunk_count == 5


def test_clean_drops_none_values():
    assert ingest._clean({"a": 1, "b": None, "c": ""}) == {"a": 1, "c": ""}


def test_file_hash_is_content_based():
    assert ingest.file_hash(b"same") == ingest.file_hash(b"same")
    assert ingest.file_hash(b"a") != ingest.file_hash(b"b")


def test_docs_dir_has_pdfs():
    assert list(config.DOCS_DIR.glob("*.pdf")), "expected policy PDFs in docs/"
