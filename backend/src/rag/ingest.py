"""Ingestion pipeline: Docling PDF parsing -> chunking -> Chroma Cloud upsert.

Run as a module:

    python -m src.rag.ingest

or trigger the same pipeline over HTTP with ``POST /api/ingest`` (see
``src.app``). Both paths call :func:`run_ingestion`.

A manifest (``docs/ingestion_manifest.json``) records the SHA-256 of every file
that reached Chroma, so re-runs only process new or changed PDFs. The manifest is
written *after* a successful upsert, never before.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import fitz  # PyMuPDF
from docling.chunking import HybridChunker
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption
from transformers import AutoTokenizer

from src import config
from src.rag.vectorstore import get_collection

BATCH_SIZE = 100


def needs_ocr(pdf_path: Path) -> bool:
    """True when the PDF has no real text layer and must be OCR'd."""
    doc = fitz.open(pdf_path)
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


def load_manifest() -> dict[str, str]:
    if config.MANIFEST_PATH.exists():
        return json.loads(config.MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest: dict[str, str]) -> None:
    config.MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def file_hash(pdf_path: Path) -> str:
    # Hash the bytes, not the name, so an edited PDF is reprocessed.
    return hashlib.sha256(pdf_path.read_bytes()).hexdigest()


def _clean(meta: dict) -> dict:
    # Chroma rejects None metadata values; drop those keys.
    return {k: v for k, v in meta.items() if v is not None}


def chunk_pdf(pdf_path: Path, chunker: HybridChunker) -> list[dict]:
    """Convert and chunk one PDF into upsert-ready records."""
    ocr_needed = needs_ocr(pdf_path)
    result = build_converter(ocr_needed).convert(str(pdf_path))

    records: list[dict] = []
    for chunk in chunker.chunk(dl_doc=result.document):
        text = chunker.contextualize(chunk=chunk)
        prov = chunk.meta.doc_items[0].prov if chunk.meta.doc_items else None
        page_no = prov[0].page_no if prov else None
        records.append(
            {
                "id": hashlib.sha256(f"{pdf_path.name}:{text}".encode()).hexdigest(),
                "document": text,
                "metadata": _clean(
                    {
                        "source": pdf_path.name,
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
    """Scan ``DOCS_DIR``, upsert new/changed PDFs, return a run summary.

    Shared by the CLI (``python -m src.rag.ingest``) and ``POST /api/ingest``.
    Unchanged files (manifest hit) are skipped, so the common case is cheap.
    Raises ``FileNotFoundError`` when the docs directory holds no PDFs.
    """
    pdf_paths = sorted(config.DOCS_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDFs found in {config.DOCS_DIR}")

    manifest = load_manifest()
    chunker = build_chunker()
    collection = get_collection()

    processed: list[str] = []
    skipped: list[str] = []
    records: list[dict] = []
    for pdf_path in pdf_paths:
        digest = file_hash(pdf_path)
        if manifest.get(pdf_path.name) == digest:
            print(f"Skipping {pdf_path.name} (unchanged)")
            skipped.append(pdf_path.name)
            continue

        print(f"Processing {pdf_path.name} ...")
        start = time.time()
        pdf_records = chunk_pdf(pdf_path, chunker)
        records.extend(pdf_records)
        manifest[pdf_path.name] = digest  # staged, committed after upsert
        processed.append(pdf_path.name)
        print(f"  {len(pdf_records)} chunks in {time.time() - start:.1f}s")

    if records:
        upsert(collection, records)
        save_manifest(manifest)

    count = collection.count()
    print(f"Done. Collection count: {count}")
    return {
        "processed": processed,
        "skipped": skipped,
        "chunks_upserted": len(records),
        "collection_count": count,
    }


def main() -> None:
    try:
        run_ingestion()
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
