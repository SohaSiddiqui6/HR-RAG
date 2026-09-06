"""Conversation store + endpoints. RAG is stubbed; DB is in-memory SQLite (conftest)."""

import pytest

from src import app as app_module
from src.rag.chain import Answer

ANSWER = Answer(
    text="5 days [pto-and-leave-policy]",
    sources=[{"source": "pto-and-leave-policy.pdf", "page_no": 1, "headings": "2.2"}],
)


@pytest.fixture(autouse=True)
def _stub_rag(monkeypatch):
    monkeypatch.setattr(app_module, "answer_question", lambda *a, **k: ANSWER)


def test_create_empty_conversation(client):
    body = client.post("/api/conversations", json={}).json()
    assert body["title"] == "New conversation"
    assert body["messages"] == []


def test_create_with_question_answers_and_titles_it(client):
    body = client.post(
        "/api/conversations", json={"question": "What is the PTO carryover limit?"}
    ).json()

    assert body["title"] == "What is the PTO carryover limit?"
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["user", "assistant"]
    assert body["messages"][1]["sources"][0]["source"] == "pto-and-leave-policy.pdf"


def test_list_orders_newest_first_and_get_roundtrips(client):
    first = client.post("/api/conversations", json={"question": "one"}).json()["id"]
    second = client.post("/api/conversations", json={"question": "two"}).json()["id"]

    listed = [c["id"] for c in client.get("/api/conversations").json()]
    assert listed == [second, first]

    fetched = client.get(f"/api/conversations/{first}").json()
    assert fetched["id"] == first
    assert len(fetched["messages"]) == 2


def test_send_message_appends_and_persists(client):
    cid = client.post("/api/conversations", json={"question": "first"}).json()["id"]

    reply = client.post(
        f"/api/conversations/{cid}/messages", json={"question": "follow up"}
    ).json()
    assert reply["user_message"]["content"] == "follow up"
    assert reply["assistant_message"]["role"] == "assistant"

    assert len(client.get(f"/api/conversations/{cid}").json()["messages"]) == 4


def test_delete_removes_conversation_and_messages(client):
    cid = client.post("/api/conversations", json={"question": "x"}).json()["id"]

    assert client.delete(f"/api/conversations/{cid}").status_code == 204
    assert client.get(f"/api/conversations/{cid}").status_code == 404
    assert client.get("/api/conversations").json() == []


def test_unknown_conversation_is_404(client):
    assert client.get("/api/conversations/missing").status_code == 404
    assert (
        client.post("/api/conversations/missing/messages", json={"question": "hi"}).status_code
        == 404
    )
