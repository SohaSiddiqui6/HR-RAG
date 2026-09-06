# docs/

Source policy documents (PDFs) - the corpus `python -m src.rag.ingest` reads.

`ingestion_manifest.json` records the SHA-256 of every PDF already ingested into
Chroma Cloud, so re-running ingestion only processes new or changed files. Delete
it to force a full re-ingest.
