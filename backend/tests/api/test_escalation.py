"""The /escalation endpoint. Delivery is stubbed with the Null backend."""

import pytest

from src import app as app_module
from src import streaming
from src.escalation.null import NullEscalation
from src.rag.chain import Answer, Outcome


def _needs_human_stream(question, history=None, run_config=None, where=None):
    text = "I couldn't find this in the current HR policies."
    yield text
    yield Answer(text=text, outcome=Outcome.NEEDS_HUMAN)


def _answered_stream(question, history=None, run_config=None, where=None):
    yield "Five days."
    yield Answer(
        text="Five days.", outcome=Outcome.ANSWERED, sources=[{"source": "x.pdf"}]
    )


def _conversation_with(client, monkeypatch, stream) -> tuple[str, str]:
    """Create a conversation, ask a question; return (conversation_id, assistant_message_id)."""
    monkeypatch.setattr(streaming, "stream_answer", stream)
    cid = client.post("/api/conversations").json()["id"]
    client.post(
        f"/api/conversations/{cid}/messages/stream", json={"question": "standing desk?"}
    )
    messages = client.get(f"/api/conversations/{cid}").json()["messages"]
    return cid, messages[1]["id"]


@pytest.fixture(autouse=True)
def _null_backend(monkeypatch):
    monkeypatch.setattr(app_module, "get_escalation", NullEscalation)


def test_escalate_a_needs_human_message(client, monkeypatch):
    cid, mid = _conversation_with(client, monkeypatch, _needs_human_stream)

    resp = client.post(
        f"/api/conversations/{cid}/escalation",
        json={"message_id": mid, "subject": "Standing desk reimbursement", "body": "..."},
    )

    assert resp.status_code == 200
    assert resp.json() == {"channel": "log", "reference": None, "url": None}

    message = client.get(f"/api/conversations/{cid}").json()["messages"][1]
    assert message["escalation"]["channel"] == "log"


def test_escalation_is_idempotent(client, monkeypatch):
    cid, mid = _conversation_with(client, monkeypatch, _needs_human_stream)
    body = {"message_id": mid, "subject": "s", "body": "b"}

    first = client.post(f"/api/conversations/{cid}/escalation", json=body).json()
    second = client.post(f"/api/conversations/{cid}/escalation", json=body).json()

    assert first == second


def test_cannot_escalate_an_answered_message(client, monkeypatch):
    cid, mid = _conversation_with(client, monkeypatch, _answered_stream)

    resp = client.post(
        f"/api/conversations/{cid}/escalation",
        json={"message_id": mid, "subject": "s", "body": "b"},
    )
    assert resp.status_code == 409


def test_unknown_message_is_404(client):
    cid = client.post("/api/conversations").json()["id"]
    resp = client.post(
        f"/api/conversations/{cid}/escalation",
        json={"message_id": "missing", "subject": "s", "body": "b"},
    )
    assert resp.status_code == 404
