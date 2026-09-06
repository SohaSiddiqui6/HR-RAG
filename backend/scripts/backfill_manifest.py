"""One-off: backfill the ``ingested_document`` manifest from what's already in Chroma.

Context: the manifest moved from a local ``ingestion_manifest.json`` to a Postgres
table, and the source PDFs moved to a Supabase Storage bucket. The table starts
empty, so ``POST /api/ingest`` would re-parse and re-embed every PDF even though
its chunks are already in the vector store.

This records one row per source PDF — SHA-256 of the *current* bucket bytes plus
the live per-source chunk count — so ingestion treats them as up to date. It
never touches Chroma or calls OpenAI. Safe to re-run; a file whose bytes changed
since it was indexed is skipped here and left for a real ingest.

    uv run python -m scripts.backfill_manifest
"""

from __future__ import annotations

from sqlmodel import Session

from src.db import store
from src.db.session import get_engine, init_db
from src.rag import storage
from src.rag.ingest import file_hash
from src.rag.vectorstore import get_collection

_PAGE = 300  # Chroma Cloud caps a single get() limit at 300


def _source_chunks(collection, source: str) -> tuple[int, bool]:
    """(chunk count, ocr_used) for one source, paginating around the 300 cap."""
    total = 0
    ocr_used = False
    offset = 0
    while True:
        page = collection.get(
            where={"source": source},
            include=["metadatas"],
            limit=_PAGE,
            offset=offset,
        )
        n = len(page["ids"])
        if n and offset == 0 and page["metadatas"]:
            ocr_used = bool(page["metadatas"][0].get("ocr_used", False))
        total += n
        offset += n
        if n < _PAGE:
            return total, ocr_used


def main() -> None:
    init_db()
    docs = storage.get_docs()
    collection = get_collection()

    refs = docs.list_pdfs()
    if not refs:
        raise SystemExit("No source PDFs found — check DOCS_SOURCE / the bucket.")

    recorded = skipped = 0
    with Session(get_engine()) as session:
        existing = store.get_ingest_manifest(session)

        for ref in refs:
            digest = file_hash(docs.fetch_pdf(ref.name))
            if existing.get(ref.name) == digest:
                print(f"  {ref.name}: already recorded")
                continue

            chunk_count, ocr_used = _source_chunks(collection, ref.name)
            if chunk_count == 0:
                print(f"  {ref.name}: 0 chunks in Chroma — leaving for a real ingest")
                skipped += 1
                continue

            store.upsert_ingested_document(
                session, ref.name, digest, chunk_count, ocr_used
            )
            print(f"  {ref.name}: recorded {chunk_count} chunks (ocr={ocr_used})")
            recorded += 1

    print(f"\nDone. {recorded} recorded, {skipped} left for ingest.")
    print(f"Chroma collection count: {collection.count()}")


if __name__ == "__main__":
    main()
