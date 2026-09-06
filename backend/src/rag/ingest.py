"""Ingestion pipeline: PDF fetch -> Docling parsing -> chunking -> Chroma upsert.

Run as a module:

    python -m src.rag.ingest

or trigger the same pipeline over HTTP with ``POST /api/ingest`` (see
``src.app``). Both paths call :func:`run_ingestion`.

Source PDFs come from :mod:`src.rag.storage` (the local ``docs/`` dir or a
Supabase Storage bucket, per ``DOCS_SOURCE``). The manifest — one SHA-256 per
file that reached Chroma — lives in Postgres (``ingested_document`` table), so
re-runs only process new or changed PDFs. Each file's manifest row is written
*after* its own upsert, never before.
"""

from __future__ import annotations

import hashlib
import time
from io import BytesIO

import fitz  # PyMuPDF
from docling.chunking import HybridChunker
from docling.datamodel.base_models import DocumentStream
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption
from sqlmodel import Session
from transformers import AutoTokenizer

from src import config
from src.db import store
from src.db.session import get_engine
from src.rag import storage
from src.rag.vectorstore import get_collection

BATCH_SIZE = 100


def needs_ocr(data: bytes) -> bool:
    """True when the PDF has no real text layer and must be OCR'd."""
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        return all(not page.get_text().strip() for page in doc)
    finally:
        doc.close()


def build_converter(ocr_needed: bool) -> DocumentConverter:
    options = PdfPipelineOptions()
    options.do_ocr = ocr_needed
    options.do_table_structure = True
    options.table_structure_options.mode = TableFormerMode.FAST
    return DocumentConverter(
        format_options={"pdf": PdfFormatOption(pipeline_options=options)}
    )


def build_chunker() -> HybridChunker:
    tokenizer = AutoTokenizer.from_pretrained(config.CHUNK_TOKENIZER)
    return HybridChunker(
        tokenizer=tokenizer,
        max_tokens=config.CHUNK_MAX_TOKENS,
        merge_peers=True,
    )


def file_hash(data: bytes) -> str:
    # Hash the bytes, not the name, so an edited PDF is reprocessed.
    return hashlib.sha256(data).hexdigest()


def _clean(meta: dict) -> dict:
    # Chroma rejects None metadata values; drop those keys.
    return {k: v for k, v in meta.items() if v is not None}


def chunk_pdf(name: str, data: bytes, chunker: HybridChunker) -> list[dict]:
    """Convert and chunk one PDF (raw bytes) into upsert-ready records."""
    ocr_needed = needs_ocr(data)
    source = DocumentStream(name=name, stream=BytesIO(data))
    result = build_converter(ocr_needed).convert(source)

    records: list[dict] = []
    for chunk in chunker.chunk(dl_doc=result.document):
        text = chunker.contextualize(chunk=chunk)
        prov = chunk.meta.doc_items[0].prov if chunk.meta.doc_items else None
        page_no = prov[0].page_no if prov else None
        records.append(
            {
                "id": hashlib.sha256(f"{name}:{text}".encode()).hexdigest(),
                "document": text,
                "metadata": _clean(
                    {
                        "source": name,
                        "headings": ", ".join(chunk.meta.headings)
                        if chunk.meta.headings
                        else "",
                        "page_no": page_no,
                        "ocr_used": ocr_needed,
                    }
                ),
            }
        )
    return records


def upsert(collection, records: list[dict]) -> None:
    """Batched upsert; deterministic ids keep re-runs idempotent."""
    for start in range(0, len(records), BATCH_SIZE):
        batch = records[start : start + BATCH_SIZE]
        collection.upsert(
            ids=[r["id"] for r in batch],
            documents=[r["document"] for r in batch],
            metadatas=[r["metadata"] for r in batch],
        )
        print(f"  upserted {min(start + BATCH_SIZE, len(records))}/{len(records)}")


def run_ingestion() -> dict:
    """Fetch source PDFs, upsert new/changed ones, return a run summary.

    Shared by the CLI (``python -m src.rag.ingest``) and ``POST /api/ingest``.
    Files whose SHA-256 matches their manifest row are skipped. Each processed
    file is upserted and its manifest row committed before moving on, so a run
    that fails partway keeps the work it already finished.

    Raises ``FileNotFoundError`` when the source holds no PDFs.
    """
    docs = storage.get_docs()
    refs = docs.list_pdfs()
    if not refs:
        raise FileNotFoundError(f"No PDFs found (DOCS_SOURCE={config.DOCS_SOURCE})")

    collection = get_collection()
    chunker: HybridChunker | None = None  # built lazily — a full-skip run needs none

    processed: list[str] = []
    skipped: list[str] = []
    chunks_upserted = 0

    with Session(get_engine()) as session:
        manifest = store.get_ingest_manifest(session)

        for ref in refs:
            data = docs.fetch_pdf(ref.name)
            digest = file_hash(data)
            if manifest.get(ref.name) == digest:
                print(f"Skipping {ref.name} (unchanged)")
                skipped.append(ref.name)
                continue

            print(f"Processing {ref.name} ...")
            start = time.time()
            if chunker is None:
                chunker = build_chunker()
            records = chunk_pdf(ref.name, data, chunker)
            upsert(collection, records)
            ocr_used = bool(records) and records[0]["metadata"].get("ocr_used", False)
            store.upsert_ingested_document(
                session, ref.name, digest, len(records), ocr_used
            )
            processed.append(ref.name)
            chunks_upserted += len(records)
            print(f"  {len(records)} chunks in {time.time() - start:.1f}s")

    count = collection.count()
    print(f"Done. Collection count: {count}")
    return {
        "processed": processed,
        "skipped": skipped,
        "chunks_upserted": chunks_upserted,
        "collection_count": count,
    }


def main() -> None:
    try:
        run_ingestion()
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
