"""Where ingestion reads its source PDFs from.

``DOCS_SOURCE=local``   -> the ``docs/`` directory (default; used by tests and
                          local dev, no network).
``DOCS_SOURCE=supabase`` -> a private Supabase Storage bucket, read with the
                          service-role key over the Storage REST API.

Both backends expose the same two calls, so :mod:`src.rag.ingest` doesn't care
which one it got. The per-file SHA-256 manifest lives in Postgres either way
(see ``src.db.store``).
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from src import config

_LIST_PAGE = 100


@dataclass(frozen=True)
class DocRef:
    """A source PDF the ingester can fetch. ``etag`` is a cheap change hint."""

    name: str
    size: int
    etag: str = ""


class LocalDocs:
    """Read PDFs straight off the local filesystem (``config.DOCS_DIR``)."""

    def list_pdfs(self) -> list[DocRef]:
        return [
            DocRef(name=p.name, size=p.stat().st_size)
            for p in sorted(config.DOCS_DIR.glob("*.pdf"))
        ]

    def fetch_pdf(self, name: str) -> bytes:
        return (config.DOCS_DIR / name).read_bytes()


class SupabaseDocs:
    """Read PDFs from a private Supabase Storage bucket via the service role."""

    def __init__(self) -> None:
        if not (config.SUPABASE_URL and config.SUPABASE_SERVICE_ROLE_KEY):
            raise RuntimeError(
                "DOCS_SOURCE=supabase but SUPABASE_URL / "
                "SUPABASE_SERVICE_ROLE_KEY is not set"
            )
        self._base = config.SUPABASE_URL.rstrip("/") + "/storage/v1"
        self._headers = {
            "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
            "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
        }

    def list_pdfs(self) -> list[DocRef]:
        refs: list[DocRef] = []
        offset = 0
        while True:
            resp = httpx.post(
                f"{self._base}/object/list/{config.DOCS_BUCKET}",
                headers=self._headers,
                json={
                    "prefix": config.DOCS_PREFIX,
                    "limit": _LIST_PAGE,
                    "offset": offset,
                    "sortBy": {"column": "name", "order": "asc"},
                },
                timeout=30,
            )
            resp.raise_for_status()
            page = resp.json()
            for obj in page:
                name = obj.get("name", "")
                meta = obj.get("metadata")  # None for pseudo-folders
                if not meta or not name.lower().endswith(".pdf"):
                    continue
                refs.append(
                    DocRef(
                        name=name,
                        size=meta.get("size", 0),
                        etag=(meta.get("eTag") or "").strip('"'),
                    )
                )
            if len(page) < _LIST_PAGE:
                return refs
            offset += len(page)

    def fetch_pdf(self, name: str) -> bytes:
        key = f"{config.DOCS_PREFIX}{name}" if config.DOCS_PREFIX else name
        resp = httpx.get(
            f"{self._base}/object/{config.DOCS_BUCKET}/{key}",
            headers=self._headers,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.content


def get_docs() -> LocalDocs | SupabaseDocs:
    return SupabaseDocs() if config.DOCS_SOURCE == "supabase" else LocalDocs()
