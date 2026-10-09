"""
SMCH Operational Twin Vector Store
====================================
Direct LanceDB + fastembed store for live operational node embeddings.
Bypasses Cognee's cognify() pipeline entirely for operational data —
the typed OntologyBuilder nodes ARE the ground truth; we only need
their dense_summary fields embedded for semantic retrieval.

fastembed BAAI/bge-small-en-v1.5 (384-dim) runs fully on CPU with no
API keys, no network calls after first model download (~70MB).

Governance documents (SOPs, Policies, KAs) are indexed separately via
Cognee's cognify() pipeline (LLM entity extraction + fastembed embedding).
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = str(ROOT_DIR / ".smch_operational_vectors")
TABLE_NAME = "operational_nodes"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384

_embed_model = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from fastembed import TextEmbedding
        _embed_model = TextEmbedding(EMBED_MODEL)
    return _embed_model


def _embed(texts: List[str]) -> List[List[float]]:
    model = _get_embed_model()
    return [v.tolist() for v in model.embed(texts)]


def _get_db():
    import lancedb
    return lancedb.connect(DB_PATH)


def _get_or_create_table(db):
    import pyarrow as pa
    schema = pa.schema([
        pa.field("id", pa.string()),
        pa.field("node_type", pa.string()),
        pa.field("dense_summary", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), EMBED_DIM)),
        pa.field("updated_at", pa.string()),
    ])
    if TABLE_NAME not in db.table_names():
        return db.create_table(TABLE_NAME, schema=schema)
    return db.open_table(TABLE_NAME)


def upsert_nodes(records: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Batch embed and upsert records into LanceDB.
    records: list of {"id": str, "node_type": str, "dense_summary": str}
    """
    if not records:
        return {"status": "noop", "upserted": 0}

    valid = [r for r in records if r.get("dense_summary")]
    if not valid:
        return {"status": "noop", "upserted": 0}

    vectors = _embed([r["dense_summary"] for r in valid])
    now = datetime.now(timezone.utc).isoformat()

    rows = [
        {
            "id": r["id"],
            "node_type": r["node_type"],
            "dense_summary": r["dense_summary"],
            "vector": v,
            "updated_at": now,
        }
        for r, v in zip(valid, vectors)
    ]

    db = _get_db()
    table = _get_or_create_table(db)

    ids_str = ", ".join(f"'{r['id']}'" for r in valid)
    try:
        table.delete(f"id IN ({ids_str})")
    except Exception:
        pass
    table.add(rows)

    return {"status": "success", "upserted": len(rows)}


def upsert_single_node(node_id: str, node_type: str, dense_summary: str) -> None:
    """
    Upsert one node after a state mutation. O(1) — one embedding call,
    not a full store rebuild. Called from graph_service mutation methods.
    """
    if not dense_summary:
        return
    try:
        upsert_nodes([{"id": node_id, "node_type": node_type, "dense_summary": dense_summary}])
    except Exception:
        pass


def search_operational(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Semantic search over the operational twin store.
    Returns results with live node IDs for cross-referencing against
    OntologyBuilder for real-time state enrichment.
    """
    try:
        db = _get_db()
        if TABLE_NAME not in db.table_names():
            return []

        table = db.open_table(TABLE_NAME)
        if table.count_rows() == 0:
            return []

        query_vec = _embed([query])[0]
        results = table.search(query_vec).limit(top_k).to_list()

        return [
            {
                "id": r["id"],
                "node_type": r["node_type"],
                "dense_summary": r["dense_summary"],
                "score": round(float(1.0 - r.get("_distance", 0.5)), 4),
                "source": "operational",
            }
            for r in results
        ]
    except Exception:
        return []


def clear_operational_store() -> None:
    """Drop the operational nodes table (used before full re-index)."""
    try:
        db = _get_db()
        if TABLE_NAME in db.table_names():
            db.drop_table(TABLE_NAME)
    except Exception:
        pass


def remove_nodes(ids: List[str]) -> Dict[str, Any]:
    """Delete embeddings for expired nodes from LanceDB.

    Called by the node lifecycle pruner after TTL expiry.
    """
    if not ids:
        return {"removed": 0}
    try:
        db = _get_db()
        if TABLE_NAME not in db.table_names():
            return {"removed": 0}
        table = db.open_table(TABLE_NAME)
        id_list = ", ".join(f"'{i}'" for i in ids)
        table.delete(f"id IN ({id_list})")
        return {"removed": len(ids)}
    except Exception as e:
        return {"removed": 0, "error": str(e)}


def get_store_stats() -> Dict[str, Any]:
    """Return row count and model info for the /config endpoint."""
    try:
        db = _get_db()
        if TABLE_NAME not in db.table_names():
            return {"rows": 0, "model": EMBED_MODEL, "dimensions": EMBED_DIM, "ready": False}
        table = db.open_table(TABLE_NAME)
        count = table.count_rows()
        return {"rows": count, "model": EMBED_MODEL, "dimensions": EMBED_DIM, "ready": count > 0}
    except Exception as e:
        return {"rows": 0, "model": EMBED_MODEL, "dimensions": EMBED_DIM, "ready": False, "error": str(e)}
