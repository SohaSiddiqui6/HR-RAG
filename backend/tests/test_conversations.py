"""Conversation store + streaming endpoint. RAG is stubbed; DB is in-memory SQLite."""

import json

import pytest

from src import app as app_module
from src.rag.chain import Answer

SOURCES = [{"source": "pto-and-leave-policy.pdf", "page_no": 1, "headings": "2.2"}]


def _fake_stream(question, history=None, run_config=None):
    yield "5 days "
    yield "[pto-and-leave-policy]"
    yield Answer(text="5 days [pto-and-leave-policy]", sources=SOURCES)


@pytest.fixture(autouse=True)
def _stub_rag(monkeypatch):
    monkeypatch.setattr(app_module, "stream_answer", _fake_stream)


def _events(response) -> list[dict]:
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]


def _new_conversation(client) -> str:
    return client.post("/api/conversations").json()["id"]


def _ask(client, conversation_id: str, question: str):
    return client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"question": question},
    )


def test_create_empty_conversation(client):
    body = client.post("/api/conversations").json()
    assert body["title"] == "New conversation"
    assert body["messages"] == []


def test_stream_emits_tokens_then_persists_and_titles(client):
    cid = _new_conversation(client)

    events = _events(_ask(client, cid, "What is the PTO carryover limit?"))

    assert [e["type"] for e in events] == ["token", "token", "done"]
    streamed = "".join(e["text"] for e in events if e["type"] == "token")
    assert streamed == "5 days [pto-and-leave-policy]"

    convo = client.get(f"/api/conversations/{cid}").json()
    assert convo["title"] == "What is the PTO carryover limit?"
    assert [m["role"] for m in convo["messages"]] == ["user", "assistant"]
    assert convo["messages"][1]["sources"][0]["source"] == "pto-and-leave-policy.pdf"


def test_list_orders_newest_first(client):
    first = _new_conversation(client)
    _ask(client, first, "one")
    second = _new_conversation(client)
    _ask(client, second, "two")

    listed = [c["id"] for c in client.get("/api/conversations").json()]
    assert listed == [second, first]


def test_follow_up_appends_to_the_conversation(client):
    cid = _new_conversation(client)
    _ask(client, cid, "first")
    _ask(client, cid, "second")

    assert len(client.get(f"/api/conversations/{cid}").json()["messages"]) == 4


def test_follow_up_passes_recent_history_to_the_chain(client, monkeypatch):
    seen: dict = {}

    def _capture(question, history=None, run_config=None):
        seen["history"] = history
        yield "ok"
        yield Answer(text="ok", sources=[])

    monkeypatch.setattr(app_module, "stream_answer", _capture)

    cid = _new_conversation(client)
    _ask(client, cid, "what is the PTO carryover limit?")
    _ask(client, cid, "what about interns?")

    assert seen["history"] == [
        ("user", "what is the PTO carryover limit?"),
        ("assistant", "ok"),
    ]


def test_delete_removes_conversation_and_messages(client):
    cid = _new_conversation(client)
    _ask(client, cid, "x")

    assert client.delete(f"/api/conversations/{cid}").status_code == 204
    assert client.get(f"/api/conversations/{cid}").status_code == 404
    assert client.get("/api/conversations").json() == []


def test_unknown_conversation_is_404(client):
    assert client.get("/api/conversations/missing").status_code == 404
    assert _ask(client, "missing", "hi").status_code == 404
