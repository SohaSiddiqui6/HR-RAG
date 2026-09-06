"""The Slack escalation backend. The webhook POST is stubbed."""

import httpx

from src.escalation import EscalationRequest, EscalationResult
from src.escalation.slack import SlackEscalation


def test_slack_backend_posts_the_request_to_the_webhook(monkeypatch):
    monkeypatch.setattr("src.config.SLACK_WEBHOOK_URL", "https://hooks.slack.test/x")
    sent: dict = {}

    def _fake_post(url, json, timeout):
        sent["url"] = url
        sent["text"] = json["text"]
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", _fake_post)

    result = SlackEscalation().submit(
        EscalationRequest(
            subject="Standing desk", body="Is it covered?", conversation_id="c1"
        )
    )

    assert result == EscalationResult(channel="slack")
    assert sent["url"] == "https://hooks.slack.test/x"
    assert "Standing desk" in sent["text"]
    assert "Is it covered?" in sent["text"]
