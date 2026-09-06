"""Human handoff: when the pipeline can't answer an HR question, route it to a person.

``get_escalation()`` returns the configured backend (``ESCALATION_BACKEND``):
``NullEscalation`` by default (logs only), ``SlackEscalation`` when a webhook is
set. A new backend (Jira, email, …) is one file implementing ``submit()`` —
``EscalationResult`` already carries a ``reference`` / ``url`` for backends that
create a trackable ticket.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src import config


@dataclass
class EscalationRequest:
    subject: str
    body: str
    conversation_id: str


@dataclass
class EscalationResult:
    channel: str  # "slack" | "log"
    reference: str | None = None
    url: str | None = None


class Escalation(Protocol):
    def submit(self, request: EscalationRequest) -> EscalationResult: ...


def get_escalation() -> Escalation:
    if config.ESCALATION_BACKEND == "slack":
        from src.escalation.slack import SlackEscalation

        return SlackEscalation()

    from src.escalation.null import NullEscalation

    return NullEscalation()


__all__ = ["Escalation", "EscalationRequest", "EscalationResult", "get_escalation"]
