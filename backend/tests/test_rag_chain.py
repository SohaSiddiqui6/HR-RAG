"""Offline test for the retrieval-relevance floor / abstention in answer_question."""

from langchain_core.documents import Document

from src import config
from src.rag import chain as rag_chain


def _doc(score):
    return Document("some policy text", metadata={"source": "x.pdf", "relevance_score": score})


def _no_llm():
    raise AssertionError("get_llm() must not be called on the abstention path")


def test_abstains_when_no_chunk_clears_threshold(monkeypatch):
    below = config.RELEVANCE_THRESHOLD - 0.05
    monkeypatch.setattr(rag_chain, "retrieve", lambda *a, **k: [_doc(below), _doc(below)])
    monkeypatch.setattr(rag_chain, "get_llm", _no_llm)

    answer = rag_chain.answer_question("something out of scope")

    assert answer.text == rag_chain.NO_ANSWER
    assert answer.sources == []
    assert answer.contexts == []
