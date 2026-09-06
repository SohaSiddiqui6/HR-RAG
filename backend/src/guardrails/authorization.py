"""Authorization boundary for retrieval.

The app currently has no authentication — a single implicit user — so
``retrieval_context()`` returns an unrestricted context and retrieval is
unfiltered. This module is the one place to add real access control:

  1. populate :class:`RetrievalContext` from the authenticated caller's claims;
  2. ``where_filter()`` turns that into a Chroma metadata filter;
  3. ingestion stamps the matching metadata (``tenant_id`` etc.) onto each chunk.

Authorization is enforced here, by filtering what retrieval can return — never by
asking the LLM whether the user is allowed to see a document.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalContext:
    """Who is asking, for the purpose of scoping retrieval."""

    tenant_id: str | None = None
    department: str | None = None
    allowed_roles: tuple[str, ...] = ()

    @property
    def unrestricted(self) -> bool:
        return not (self.tenant_id or self.department or self.allowed_roles)


# The current default: one user who may see every document.
SYSTEM_CONTEXT = RetrievalContext()


def retrieval_context() -> RetrievalContext:
    """The current caller's retrieval scope. Wire real auth in here."""
    return SYSTEM_CONTEXT


def where_filter(context: RetrievalContext) -> dict | None:
    """Translate a context into a Chroma ``where`` filter (``None`` = unrestricted)."""
    if context.unrestricted:
        return None

    clauses: list[dict] = []
    if context.tenant_id:
        clauses.append({"tenant_id": context.tenant_id})
    if context.department:
        clauses.append({"department": context.department})
    if context.allowed_roles:
        clauses.append({"allowed_roles": {"$in": list(context.allowed_roles)}})

    return clauses[0] if len(clauses) == 1 else {"$and": clauses}
