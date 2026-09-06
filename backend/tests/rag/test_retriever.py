"""Retrieval: the authorization filter reaches the Chroma query."""

from src.rag import retriever


def test_retrieve_forwards_the_authorization_filter(monkeypatch):
    captured: dict = {}

    class _Retriever:
        def invoke(self, _query, config=None):
            return []

    def _build(where=None):
        captured["where"] = where
        return _Retriever()

    monkeypatch.setattr(retriever, "_build_retriever", _build)
    retriever.retrieve("q", where={"tenant_id": "acme"})

    assert captured["where"] == {"tenant_id": "acme"}
