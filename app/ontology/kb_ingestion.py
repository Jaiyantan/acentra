"""
SMCH Knowledge Base Ingestion Pipeline
=======================================
Two separate ingestion pipelines:

1. ingest_governance_knowledge_base()
   157 JSON documents (SOPs, Policies, KAs, Forms, Reports) → Cognee cognify pipeline.
   LLM (Ollama/llama3.2) extracts entities + relationships from governance text.
   fastembed BAAI/bge-small-en-v1.5 embeds them into Cognee's LanceDB index.
   Runs once and caches via .cognee_kb_state.json.

2. ingest_operational_twin_contexts(builder)
   Live patient/bed/discharge/lab dense_summaries → direct LanceDB via vector_store.
   NO LLM call. NO cognify. Just fastembed → upsert.
   Called at full sync for bulk O(N) baseline; incremental O(1) updates
   happen via upsert_single_node() after each mutation.
"""

import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import cognee

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
KB_DIR = ROOT_DIR / "knowledge_base"
INDEX_DIR = KB_DIR / "index"
STATE_FILE = ROOT_DIR / ".cognee_kb_state.json"

DATASET_GOVERNANCE = "smch_governance_kb"


def _load_kb_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_kb_state(state: Dict[str, Any]) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def _build_document_text(card: Dict[str, Any], file_id: str) -> str:
    parts = [
        f"Document: {file_id}",
        f"Title: {card.get('title', 'Unknown Document')}",
        f"Category: {card.get('category', 'document')}",
        f"Department: {card.get('department', 'Hospital Operations')}",
        f"Version: {card.get('version', '1.0')}",
    ]
    if card.get("applicable_roles"):
        roles = card["applicable_roles"]
        parts.append(f"Applicable Roles: {', '.join(roles) if isinstance(roles, list) else str(roles)}")
    if card.get("tags"):
        tags = card["tags"]
        parts.append(f"Tags: {', '.join(tags) if isinstance(tags, list) else str(tags)}")
    if card.get("content"):
        parts.append(f"Content: {card['content']}")
    if card.get("source_citation"):
        parts.append(f"Citation: {card['source_citation']}")
    return "\n".join(parts)


async def ingest_governance_knowledge_base(force: bool = False) -> Dict[str, Any]:
    """
    Ingest all SOPs, Policies, KAs, Forms, Reports through Cognee's full semantic pipeline.
    LLM extracts entities/relationships; fastembed embeds them into Cognee's LanceDB index.
    Uses state file to skip re-ingestion unless force=True.
    """
    state = _load_kb_state()
    if not force and state.get("kb_ingested") and state.get("dataset") == DATASET_GOVERNANCE:
        return {
            "status": "ok",
            "dataset": DATASET_GOVERNANCE,
            "ingested_count": state.get("doc_count", 0),
            "failed_count": 0,
            "already_ingested": True,
            "ingested_at": state.get("ingested_at"),
        }

    if not INDEX_DIR.exists():
        return {
            "status": "error",
            "message": f"knowledge_base/index not found at {INDEX_DIR}",
            "dataset": DATASET_GOVERNANCE,
            "ingested_count": 0,
            "failed_count": 0,
            "already_ingested": False,
        }

    # Configure Cognee to use the Groq LLM from env vars before cognify
    try:
        from app.ontology.cognee_config import configure_cognee
        configure_cognee()
    except Exception:
        pass

    index_files = list(INDEX_DIR.glob("*.json"))
    ingested_ids = []
    failed = []

    for idx_file in index_files:
        try:
            with open(idx_file, "r", encoding="utf-8") as f:
                card = json.load(f)
            file_id = card.get("file_id", idx_file.stem)
            text = _build_document_text(card, file_id)
            await cognee.add(text, dataset_name=DATASET_GOVERNANCE)
            ingested_ids.append(file_id)
        except Exception as e:
            failed.append({"file": idx_file.name, "error": str(e)})

    if ingested_ids:
        try:
            await cognee.cognify(datasets=[DATASET_GOVERNANCE])
        except Exception as e:
            failed.append({"phase": "cognify", "error": str(e)})

    ingested_at = datetime.now(timezone.utc).isoformat()
    _save_kb_state({
        "kb_ingested": len(ingested_ids) > 0,
        "dataset": DATASET_GOVERNANCE,
        "doc_count": len(ingested_ids),
        "ingested_at": ingested_at,
    })

    return {
        "status": "success" if ingested_ids else "partial",
        "dataset": DATASET_GOVERNANCE,
        "ingested_count": len(ingested_ids),
        "failed_count": len(failed),
        "already_ingested": False,
        "ingested_at": ingested_at,
        "sample_ingested": ingested_ids[:10],
        "failed_details": failed[:5],
    }


async def ingest_operational_twin_contexts(builder) -> Dict[str, Any]:
    """
    Embed all live operational node dense_summaries directly into LanceDB.
    NO cognify. NO LLM call. fastembed → upsert via vector_store.

    Solving Context Decay: stale embeddings replaced on every full sync
    because we drop-then-rebuild the table from current OntologyBuilder state.
    Incremental per-mutation updates happen via upsert_single_node() in graph_service.
    """
    from app.ontology.vector_store import upsert_nodes, clear_operational_store

    clear_operational_store()

    records = []
    collections = [
        ("PatientNode", builder.patients),
        ("BedNode", builder.beds),
        ("AdmissionNode", builder.admissions),
        ("DischargeNode", builder.discharges),
        ("LabPanicAlertNode", builder.lab_critical_alerts),
        ("LabResultNode", builder.lab_results),
        ("BillNode", builder.bills),
        ("ClaimNode", builder.claims),
        ("PrescriptionNode", builder.prescriptions),
        ("EmergencyCaseNode", builder.emergency_cases),
    ]

    for node_type, store in collections:
        for node_id, node in store.items():
            ds = getattr(node, "dense_summary", "") or ""
            if ds:
                records.append({"id": node_id, "node_type": node_type, "dense_summary": ds})

    if not records:
        return {"status": "noop", "nodes_embedded": 0}

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, upsert_nodes, records)

    return {
        "status": result["status"],
        "nodes_embedded": result.get("upserted", 0),
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
    }
