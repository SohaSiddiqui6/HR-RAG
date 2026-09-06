# docs/

Source policy documents (PDFs) — the corpus the ingester reads when
`DOCS_SOURCE=local` (the default). With `DOCS_SOURCE=supabase` the same files are
pulled from a private Supabase Storage bucket instead and this directory is
unused.

The ingestion manifest — one SHA-256 per PDF already in Chroma, so re-runs only
process new or changed files — lives in Postgres now (`ingested_document`
table), not a JSON file here. To force a full re-ingest, truncate that table.
