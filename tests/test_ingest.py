import pytest

from src import config

# The ingest module pulls in docling / transformers / pymupdf; skip cleanly
# when the ingestion extras are not installed.
ingest = pytest.importorskip("src.ingest")


def test_manifest_roundtrip(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    monkeypatch.setattr(config, "MANIFEST_PATH", path)

    assert ingest.load_manifest() == {}
    ingest.save_manifest({"a.pdf": "hash"})
    assert ingest.load_manifest() == {"a.pdf": "hash"}


def test_clean_drops_none_values():
    assert ingest._clean({"a": 1, "b": None, "c": ""}) == {"a": 1, "c": ""}


def test_docs_dir_has_pdfs():
    assert list(config.DOCS_DIR.glob("*.pdf")), "expected policy PDFs in docs/"
