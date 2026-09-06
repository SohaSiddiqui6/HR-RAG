"""Default escalation backend: log the request, send it nowhere."""

from __future__ import annotations

import logging

from src.escalation import EscalationRequest, EscalationResult

log = logging.getLogger(__name__)


class NullEscalation:
    def submit(self, request: EscalationRequest) -> EscalationResult:
        log.info(
            "HR handoff (not delivered — ESCALATION_BACKEND=none): %s", request.subject
        )
        return EscalationResult(channel="log")
