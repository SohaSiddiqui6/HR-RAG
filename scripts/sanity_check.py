"""Run the dense and sparse retrieval legs separately for one query.

The hybrid-search bug this pipeline guards against is invisible: dense results
look fine, so hybrid results look fine, while the lexical half quietly returns
nothing. Run this after an ingest and confirm the sparse leg comes back with hits.

    python -m scripts.sanity_check "What is the PTO carryover limit?"
"""

from __future__ import annotations

import sys

from chromadb import K, Knn, Search

from src import config
from src.vectorstore import get_collection


def leg(collection, query: str, key: str | None = None, k: int = 5):
    rank = Knn(query=query, key=key) if key else Knn(query=query)
    search = Search().rank(rank).limit(k).select(K.SCORE, K.METADATA)
    return collection.search(search).rows()[0]


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "What are the company core values?"
    collection = get_collection()

    print(f"Query: {query}")
    print(f"Collection count: {collection.count()}\n")

    print("Dense only:")
    for row in leg(collection, query):
        meta = row["metadata"]
        print(f"  {meta.get('source')} p{meta.get('page_no')}  score={row['score']:.4f}")

    print("\nSparse (BM25) only:")
    sparse_rows = leg(collection, query, key=config.SPARSE_KEY)
    for row in sparse_rows:
        meta = row["metadata"]
        print(f"  {meta.get('source')} p{meta.get('page_no')}  score={row['score']:.4f}")

    if not sparse_rows:
        print("  WARNING: sparse leg returned nothing - the collection may lack "
              "the sparse index in its schema.")


if __name__ == "__main__":
    main()
