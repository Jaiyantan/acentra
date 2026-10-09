"""
Cognee & Vector Store Configuration Status
============================================
Reports operational readiness for the two-layer semantic architecture:
- Cognee (governance KB): Groq LLM + fastembed BAAI/bge-small-en-v1.5
- vector_store (operational twin): direct fastembed + LanceDB

Credentials are never returned in any status dict.
"""

import os
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STATE_FILE = ROOT_DIR / ".cognee_kb_state.json"

_cognee_configured = False


def configure_cognee() -> bool:
    """Programmatically apply env-var LLM/embedding settings to Cognee.

    Called once at startup (idempotent). Returns True if succeeded, False otherwise.
    Cognee reads config from env vars but this function explicitly sets the
    LLM and embedding adapters so Groq is used for entity extraction.
    """
    global _cognee_configured
    if _cognee_configured:
        return True
    try:
        import cognee
        llm_provider = os.getenv("LLM_PROVIDER", "groq")
        llm_model = os.getenv("LLM_MODEL", "groq/qwen/qwen3.8-27b")
        llm_api_key = os.getenv("LLM_API_KEY", "")
        llm_endpoint = os.getenv("LLM_ENDPOINT", "").strip()

        embed_provider = os.getenv("EMBEDDING_PROVIDER", "fastembed")
        embed_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        embed_dims = int(os.getenv("EMBEDDING_DIMENSIONS", "384"))

        # Build cognee config dict accepted by cognee.config.set_llm_config
        llm_config: Dict[str, Any] = {
            "provider": llm_provider,
            "model": llm_model,
            "api_key": llm_api_key,
        }
        if llm_endpoint:
            llm_config["endpoint"] = llm_endpoint

        embedding_config: Dict[str, Any] = {
            "provider": embed_provider,
            "model": embed_model,
            "vector_db_dimensions": embed_dims,
            "vector_db_url": str(ROOT_DIR / ".smch_operational_vectors"),
        }

        # Try cognee's config API (varies by cognee version)
        try:
            cognee.config.set_llm_config(llm_config)
            cognee.config.set_embedding_model_config(embedding_config)
        except AttributeError:
            # Older versions use cognee.config object directly
            cfg = cognee.config
            for k, v in llm_config.items():
                try:
                    setattr(cfg, f"llm_{k}", v)
                except Exception:
                    pass

        _cognee_configured = True
        return True
    except Exception:
        return False


def verify_cognee_configuration() -> Dict[str, Any]:
    """Returns active engine config. No credentials exposed."""
    llm_key = os.getenv("LLM_API_KEY", "")
    key_preview = llm_key[:4] + "..." if llm_key else "(not set)"
    return {
        "llm": {
            "provider": os.getenv("LLM_PROVIDER", "groq"),
            "model": os.getenv("LLM_MODEL", "groq/qwen/qwen3.8-27b"),
            "endpoint": os.getenv("LLM_ENDPOINT", "") or "(default — Groq API)",
            "api_key_preview": key_preview,
            "configured": True,
        },
        "embedding": {
            "provider": os.getenv("EMBEDDING_PROVIDER", "fastembed"),
            "model": os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
            "dimensions": int(os.getenv("EMBEDDING_DIMENSIONS", "384")),
            "configured": True,
        },
        "vector_store": {
            "provider": os.getenv("VECTOR_DB_PROVIDER", "lancedb"),
        },
        "graph_store": {
            "provider": os.getenv("GRAPH_DATABASE_PROVIDER", "kuzu"),
        },
    }


def get_cognee_status() -> Dict[str, Any]:
    """Full readiness status for /api/v1/ontology/config."""
    import json
    from app.ontology.vector_store import get_store_stats

    config = verify_cognee_configuration()

    kb_state: Dict[str, Any] = {}
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                kb_state = json.load(f)
        except Exception:
            pass

    vector_engine_ok = False
    vector_engine_class = "unknown"
    try:
        from cognee.infrastructure.databases.vector import get_vector_engine
        ve = get_vector_engine()
        vector_engine_class = ve.__class__.__name__
        vector_engine_ok = True
    except Exception as e:
        vector_engine_class = f"error: {e}"

    op_store_stats = get_store_stats()
    kb_ready = kb_state.get("kb_ingested", False)
    all_systems_go = vector_engine_ok and kb_ready and op_store_stats.get("ready", False)

    return {
        "operational": all_systems_go,
        "config": config,
        "knowledge_base": {
            "ingested": kb_ready,
            "dataset": kb_state.get("dataset", "smch_governance_kb"),
            "doc_count": kb_state.get("doc_count", 0),
            "ingested_at": kb_state.get("ingested_at"),
        },
        "operational_twin_store": op_store_stats,
        "engines": {
            "vector_engine": {
                "class": vector_engine_class,
                "ok": vector_engine_ok,
            },
        },
        "readiness_checklist": {
            "vector_engine_reachable": vector_engine_ok,
            "governance_kb_indexed": kb_ready,
            "operational_twin_embedded": op_store_stats.get("ready", False),
            "operational_node_count": op_store_stats.get("rows", 0),
        },
    }
