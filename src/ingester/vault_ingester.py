"""
Obsidian vault → ChromaDB ingestion pipeline.

Walk vault for .md files, parse frontmatter, chunk by headers,
embed with nomic-embed-text via Ollama, upsert to persistent ChromaDB.
IDs are derived from (relative_path, chunk_index) so re-ingestion is
idempotent — changed notes update in place, unchanged notes are no-ops.

Usage:
    # From pv-workbench/ with PYTHONPATH=src
    python -m ingester.vault_ingester            # ingest full vault
    python -m ingester.vault_ingester --query "Evans PRR criteria"
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import frontmatter
import chromadb
from chromadb.utils.embedding_functions.ollama_embedding_function import (
    OllamaEmbeddingFunction,
)

# Allow running as script from project root
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    VAULT_PATH, CHROMA_PATH, COLLECTION_NAME,
    EMBED_MODEL, OLLAMA_BASE_URL, CHUNK_SIZE, TOP_K,
)
from ingester.chunker import chunk_note


def _chunk_id(rel_path: Path, chunk_index: int) -> str:
    """Stable 16-char ID for upsert idempotency."""
    key = f"{rel_path}::{chunk_index}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _get_collection(client: chromadb.PersistentClient) -> chromadb.Collection:
    ef = OllamaEmbeddingFunction(
        url=f"{OLLAMA_BASE_URL}/api/embeddings",
        model_name=EMBED_MODEL,
        timeout=120,  # nomic-embed-text can take >60s to load from cold
    )
    return client.get_or_create_collection(COLLECTION_NAME, embedding_function=ef)


def ingest_vault(vault_path: Path = VAULT_PATH) -> dict:
    """
    Walk vault, chunk all .md notes, embed and upsert into ChromaDB.
    Returns ingestion stats.
    """
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = _get_collection(client)

    notes = sorted(vault_path.rglob("*.md"))
    stats = {"notes": 0, "chunks": 0, "skipped": 0}

    for note_path in notes:
        rel = note_path.relative_to(vault_path)
        folder = str(rel.parent) if str(rel.parent) != "." else "root"

        try:
            post = frontmatter.load(note_path)
        except Exception as e:
            print(f"  SKIP {rel}: {e}", file=sys.stderr)
            stats["skipped"] += 1
            continue

        if not post.content.strip():
            stats["skipped"] += 1
            continue

        tags = post.metadata.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        chunks = chunk_note(post.content, max_size=CHUNK_SIZE)
        if not chunks:
            stats["skipped"] += 1
            continue

        ids = [_chunk_id(rel, c.chunk_index) for c in chunks]
        documents = [c.text for c in chunks]
        # Derive jurisdiction booleans from frontmatter field.
        # ICH and BOTH apply to all jurisdictions; FDA/EMA are exclusive.
        jur = post.metadata.get("jurisdiction", "BOTH").upper()
        is_fda = jur in ("FDA", "ICH", "BOTH")
        is_ema = jur in ("EMA", "ICH", "BOTH")

        metadatas = [
            {
                "source_note": str(rel),
                "folder": folder,
                "section_header": c.header,
                "chunk_index": c.chunk_index,
                "tags": json.dumps(tags),
                "title": post.metadata.get("title", note_path.stem),
                "source_ref": post.metadata.get("source", ""),
                "jurisdiction": jur,
                "is_fda": is_fda,
                "is_ema": is_ema,
            }
            for c in chunks
        ]

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        stats["notes"] += 1
        stats["chunks"] += len(chunks)
        print(f"  {rel}: {len(chunks)} chunk(s)")

    print(f"\nDone — {stats['notes']} notes, {stats['chunks']} chunks "
          f"({stats['skipped']} skipped)")
    return stats


def query_vault(
    query: str,
    n_results: int = TOP_K,
    folder: str | None = None,
    jurisdiction: str | None = None,
) -> list[dict]:
    """
    Semantic search over ingested vault.

    Args:
        query:        Natural-language query string
        n_results:    Number of chunks to return
        folder:       Optional vault subfolder filter (e.g. "Guidelines")
        jurisdiction: Optional jurisdiction filter — "FDA", "EMA", or None (both)

    Returns:
        List of dicts: {text, source_note, section_header, folder, distance, jurisdiction}
    """
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = _get_collection(client)

    # Build ChromaDB where clause — combine folder and jurisdiction filters
    conditions = []
    if folder:
        conditions.append({"folder": folder})
    if jurisdiction:
        jur_upper = jurisdiction.upper()
        if jur_upper == "FDA":
            conditions.append({"is_fda": True})
        elif jur_upper == "EMA":
            conditions.append({"is_ema": True})

    if len(conditions) == 0:
        where = None
    elif len(conditions) == 1:
        where = conditions[0]
    else:
        where = {"$and": conditions}

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where,
    )

    hits = []
    for i in range(len(results["documents"][0])):
        meta = results["metadatas"][0][i]
        hits.append({
            "text": results["documents"][0][i],
            "source_note": meta.get("source_note", ""),
            "section_header": meta.get("section_header", ""),
            "folder": meta.get("folder", ""),
            "distance": round(results["distances"][0][i], 4),
            "jurisdiction": meta.get("jurisdiction", "BOTH"),
        })
    return hits


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vault ingester / query tool")
    parser.add_argument("--query", "-q", type=str, help="Run a semantic query instead of ingesting")
    parser.add_argument("--folder", "-f", type=str, help="Filter query to a vault subfolder")
    parser.add_argument("--jurisdiction", "-j", type=str, choices=["FDA", "EMA"], help="Filter by jurisdiction")
    parser.add_argument("--n", type=int, default=TOP_K, help="Number of results")
    args = parser.parse_args()

    if args.query:
        hits = query_vault(args.query, n_results=args.n, folder=args.folder, jurisdiction=args.jurisdiction)
        for i, h in enumerate(hits, 1):
            print(f"\n[{i}] {h['source_note']} › {h['section_header']} (dist={h['distance']})")
            print(h["text"][:400])
    else:
        ingest_vault()
