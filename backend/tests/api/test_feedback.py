"""The /feedback endpoint forwards a thumbs rating to Langfuse as a score."""

from src import app as app_module


def test_feedback_records_a_user_feedback_score(client, monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(
        app_module.tracing,
        "score",
        lambda trace_id, name, value, data_type: calls.append(
            (trace_id, name, value, data_type)
        ),
    )

    resp = client.post("/api/feedback", json={"trace_id": "t-1", "helpful": True})

    assert resp.status_code == 204
    assert calls == [("t-1", "user_feedback", 1.0, "BOOLEAN")]


def test_thumbs_down_is_zero(client, monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(
        app_module.tracing,
        "score",
        lambda *args: calls.append(args),
    )

    client.post("/api/feedback", json={"trace_id": "t-2", "helpful": False})

    assert calls[0] == ("t-2", "user_feedback", 0.0, "BOOLEAN")
