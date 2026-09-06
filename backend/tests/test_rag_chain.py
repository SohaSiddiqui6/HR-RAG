"""Offline tests for answer_question: the abstention floor and follow-up condensing."""

from types import SimpleNamespace

from langchain_core.documents import Document

from src import config
from src.rag import chain as rag_chain


def _doc(score):
    return Document("some policy text", metadata={"source": "x.pdf", "relevance_score": score})


def _no_llm():
    raise AssertionError("get_llm() must not be called on the abstention path")


class _FakeLLM:
    """Returns fixed content for both `invoke` (condense + generation) and `stream`."""

    def __init__(self, content: str):
        self._content = content

    def invoke(self, _messages, config=None):
        return SimpleNamespace(content=self._content)


def _capturing_retrieve(sink: list[str]):
    def _retrieve(query: str, run_config=None):
        sink.append(query)
        return [_doc(0.9)]

    return _retrieve


def test_abstains_when_no_chunk_clears_threshold(monkeypatch):
    below = config.RELEVANCE_THRESHOLD - 0.05
    monkeypatch.setattr(rag_chain, "retrieve", lambda *a, **k: [_doc(below), _doc(below)])
    monkeypatch.setattr(rag_chain, "get_llm", _no_llm)

    answer = rag_chain.answer_question("something out of scope")

    assert answer.text == rag_chain.NO_ANSWER
    assert answer.sources == []
    assert answer.contexts == []


def test_no_history_retrieves_on_the_raw_question(monkeypatch):
    queries: list[str] = []
    monkeypatch.setattr(rag_chain, "retrieve", _capturing_retrieve(queries))
    monkeypatch.setattr(rag_chain, "get_llm", lambda: _FakeLLM("answer [x]"))

    rag_chain.answer_question("what is the PTO carryover limit?")

    assert queries == ["what is the PTO carryover limit?"]


def test_follow_up_is_condensed_before_retrieval(monkeypatch):
    queries: list[str] = []
    monkeypatch.setattr(rag_chain, "retrieve", _capturing_retrieve(queries))
    monkeypatch.setattr(rag_chain, "get_llm", lambda: _FakeLLM("PTO carryover limit for interns"))

    rag_chain.answer_question(
        "what about interns?",
        history=[
            ("user", "what is the PTO carryover limit?"),
            ("assistant", "Five days [pto-and-leave-policy]."),
        ],
    )

    assert queries == ["PTO carryover limit for interns"]
