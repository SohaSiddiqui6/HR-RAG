"""Slack escalation backend: post the request to an incoming webhook."""

from __future__ import annotations

import httpx

from src import config
from src.escalation import EscalationRequest, EscalationResult


class SlackEscalation:
    def submit(self, request: EscalationRequest) -> EscalationResult:
        if not config.SLACK_WEBHOOK_URL:
            raise RuntimeError("ESCALATION_BACKEND=slack but SLACK_WEBHOOK_URL is not set")

        text = (
            f":raising_hand: *HR request — {request.subject}*\n"
            f"{request.body}\n\n"
            f"_via HR-RAG · conversation `{request.conversation_id}`_"
        )
        response = httpx.post(
            config.SLACK_WEBHOOK_URL, json={"text": text}, timeout=10
        )
        response.raise_for_status()
        return EscalationResult(channel="slack")
