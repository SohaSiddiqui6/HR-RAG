"""Authorization boundary: context -> retrieval metadata filter.

There is no auth system yet, so these test the interface and the filter it
produces. Chroma enforces the filter at query time (see rag.retriever.retrieve).
"""

from src.guardrails.authorization import (
    RetrievalContext,
    retrieval_context,
    where_filter,
)


def test_default_context_is_unrestricted():
    ctx = retrieval_context()
    assert ctx.unrestricted
    assert where_filter(ctx) is None


def test_single_claim_becomes_a_flat_filter():
    assert where_filter(RetrievalContext(tenant_id="acme")) == {"tenant_id": "acme"}


def test_multiple_claims_are_and_ed():
    ctx = RetrievalContext(tenant_id="acme", department="people", allowed_roles=("employee",))
    assert where_filter(ctx) == {
        "$and": [
            {"tenant_id": "acme"},
            {"department": "people"},
            {"allowed_roles": {"$in": ["employee"]}},
        ]
    }


def test_unauthorized_tenant_is_excluded_by_the_filter():
    # A caller scoped to "acme" produces a filter that only matches acme's docs;
    # a document tagged tenant_id="globex" cannot satisfy it.
    where = where_filter(RetrievalContext(tenant_id="acme"))
    assert where == {"tenant_id": "acme"}
    assert where != {"tenant_id": "globex"}
