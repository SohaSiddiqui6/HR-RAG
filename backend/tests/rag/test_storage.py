"""src.rag.storage — the local and Supabase-bucket PDF sources."""

import httpx
import pytest

from src import config
from src.rag import storage


# --- local ---------------------------------------------------------------


def test_local_lists_and_reads_docs_dir():
    docs = storage.LocalDocs()
    refs = docs.list_pdfs()

    assert refs, "expected the committed policy PDFs"
    assert all(r.name.endswith(".pdf") for r in refs)
    assert refs == sorted(refs, key=lambda r: r.name)

    data = docs.fetch_pdf(refs[0].name)
    assert data[:5] == b"%PDF-"
    assert len(data) == refs[0].size


# --- supabase ----------------------------------------------------------


@pytest.fixture
def _supabase_config(monkeypatch):
    monkeypatch.setattr(config, "SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setattr(config, "SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
    monkeypatch.setattr(config, "DOCS_BUCKET", "hr-policy-docs")
    monkeypatch.setattr(config, "DOCS_PREFIX", "")


class _FakeResponse:
    def __init__(self, *, json_data=None, content=b""):
        self._json = json_data
        self.content = content

    def json(self):
        return self._json

    def raise_for_status(self):
        pass


def test_supabase_requires_credentials(monkeypatch):
    monkeypatch.setattr(config, "SUPABASE_URL", "")
    monkeypatch.setattr(config, "SUPABASE_SERVICE_ROLE_KEY", "")
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        storage.SupabaseDocs()


def test_supabase_list_filters_folders_and_non_pdf(monkeypatch, _supabase_config):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json
        return _FakeResponse(
            json_data=[
                {
                    "name": "benefits-overview.pdf",
                    "metadata": {"size": 1234, "eTag": '"abc"'},
                },
                {"name": "nested", "metadata": None},  # pseudo-folder
                {"name": "notes.txt", "metadata": {"size": 10, "eTag": '"x"'}},
            ]
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    refs = storage.SupabaseDocs().list_pdfs()

    assert refs == [storage.DocRef(name="benefits-overview.pdf", size=1234, etag="abc")]
    assert captured["url"] == (
        "https://proj.supabase.co/storage/v1/object/list/hr-policy-docs"
    )
    assert captured["headers"]["Authorization"] == "Bearer service-role-key"
    assert captured["headers"]["apikey"] == "service-role-key"


def test_supabase_fetch_hits_object_endpoint(monkeypatch, _supabase_config):
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return _FakeResponse(content=b"%PDF-1.7 ...")

    monkeypatch.setattr(httpx, "get", fake_get)

    data = storage.SupabaseDocs().fetch_pdf("benefits-overview.pdf")

    assert data == b"%PDF-1.7 ..."
    assert captured["url"] == (
        "https://proj.supabase.co/storage/v1/object/"
        "hr-policy-docs/benefits-overview.pdf"
    )


def test_supabase_fetch_applies_prefix(monkeypatch, _supabase_config):
    monkeypatch.setattr(config, "DOCS_PREFIX", "policies/")
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return _FakeResponse(content=b"%PDF-")

    monkeypatch.setattr(httpx, "get", fake_get)
    storage.SupabaseDocs().fetch_pdf("a.pdf")
    assert captured["url"].endswith("/hr-policy-docs/policies/a.pdf")


# --- selector --------------------------------------------------------


def test_get_docs_switches_on_config(monkeypatch):
    monkeypatch.setattr(config, "DOCS_SOURCE", "local")
    assert isinstance(storage.get_docs(), storage.LocalDocs)

    monkeypatch.setattr(config, "DOCS_SOURCE", "supabase")
    monkeypatch.setattr(config, "SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setattr(config, "SUPABASE_SERVICE_ROLE_KEY", "k")
    assert isinstance(storage.get_docs(), storage.SupabaseDocs)
