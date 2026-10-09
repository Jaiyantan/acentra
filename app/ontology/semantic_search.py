"""
SMCH Unified Semantic Search
==============================
Merges two semantic indices:

1. Operational twin (vector_store.py — direct LanceDB, fastembed)
   Fast, always fresh (upserted on every mutation via upsert_single_node).
   Results cross-referenced with live OntologyBuilder state.

2. Governance KB (Cognee — Ollama LLM entity extraction + fastembed)
   Rich relational graph over SOPs, Policies, KAs, Workflows.
   Searched via cognee.search() API.

multi_context_search() = operational hit → live state lookup → merged result.
Solves Context Fragmentation (cross-dept links) and Context Decay
(live state attached to every semantic result, never stale embeddings).
"""

import asyncio
from typing import Any, Dict, List


async def semantic_query(
    query: str,
    search_type: str = "SUMMARIES",
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Search the operational vector store (direct fastembed) and the
    Cognee governance index in parallel. Merge results — operational first.
    """
    op_results = []
    gov_results = []

    # 1. Operational twin search (direct LanceDB — always available after sync)
    try:
        from app.ontology.vector_store import search_operational
        loop = asyncio.get_event_loop()
        op_results = await loop.run_in_executor(None, search_operational, query, top_k)
    except Exception:
        op_results = []

    # 2. Governance KB search via Cognee (fastembed + Ollama LLM graph)
    try:
        try:
            from cognee.api.v1.search.types import SearchType as CogneeSearchType
        except ImportError:
            from cognee.modules.search.types import SearchType as CogneeSearchType

        import cognee
        raw = await cognee.search(CogneeSearchType.SUMMARIES, query_text=query)
        if raw:
            for r in raw[:top_k]:
                if isinstance(r, dict):
                    gov_results.append({**r, "source": "governance"})
                elif hasattr(r, "__dict__"):
                    d = {k: v for k, v in r.__dict__.items() if not k.startswith("_")}
                    d["source"] = "governance"
                    gov_results.append(d)
    except Exception:
        gov_results = []

    # 3. Fallback: keyword search over in-memory builder if both empty (cold start)
    if not op_results and not gov_results:
        try:
            from app.ontology.builder import get_ontology_builder
            builder = get_ontology_builder()
            fallback = _keyword_fallback(query, builder, top_k)
        except Exception:
            fallback = []
        return {
            "status": "fallback",
            "query": query,
            "results_count": len(fallback),
            "results": fallback,
            "sources": {"operational": len(fallback), "governance": 0},
        }

    merged = op_results[:top_k] + gov_results[:max(0, top_k - len(op_results))]

    return {
        "status": "ok",
        "query": query,
        "results_count": len(merged),
        "results": merged,
        "sources": {"operational": len(op_results), "governance": len(gov_results)},
    }


def _keyword_fallback(query: str, builder, top_k: int) -> List[Dict[str, Any]]:
    """Keyword scan over dense_summary fields when vector index is cold.

    Uses tokenized word matching: requires ≥2 query tokens (len > 3) to match
    so single-word queries don't flood results, and multi-word queries need
    at least two content words to hit before being included.
    """
    q_words = [w for w in query.lower().split() if len(w) > 3]
    # Require at least 2 word matches for multi-word queries; 1 for very short queries
    min_hits = min(2, len(q_words)) if q_words else 1
    hits = []
    collections = [
        ("PatientNode", builder.patients),
        ("BedNode", builder.beds),
        ("AdmissionNode", builder.admissions),
        ("DischargeNode", builder.discharges),
        ("LabPanicAlertNode", builder.lab_critical_alerts),
        ("LabResultNode", builder.lab_results),
        ("BillNode", builder.bills),
        ("ClaimNode", builder.claims),
        ("SOPNode", builder.sops),
        ("PolicyNode", builder.policies),
        ("KnowledgeArticleNode", builder.articles),
        ("RoutingRuleNode", builder.routing_rules),
    ]
    for node_type, store in collections:
        for key, node in store.items():
            summary = (getattr(node, "dense_summary", "") or "").lower()
            node_id_lower = key.lower()
            combined = summary + " " + node_id_lower
            matched = sum(1 for w in q_words if w in combined)
            if matched >= min_hits:
                hits.append({
                    "id": key,
                    "node_type": node_type,
                    "dense_summary": (getattr(node, "dense_summary", "") or "")[:300],
                    "score": matched / max(len(q_words), 1),
                    "source": "keyword_fallback",
                })
                if len(hits) >= top_k:
                    return hits
    # Sort by relevance score descending
    hits.sort(key=lambda x: x["score"], reverse=True)
    return hits[:top_k]


async def multi_context_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Semantic search with live operational state enrichment.

    For each operational hit, attaches live node state from OntologyBuilder:
    - PatientNode: current bed, discharge status, active blockers
    - DischargeNode: all 4-point clearance flags, gate pass status
    - LabPanicAlertNode: SLA status, elapsed time, readback state
    - BedNode: current occupancy
    - BillNode: pending amount, dispute flags

    Always appends a macro operational snapshot (blocked discharges, panic alerts,
    dirty bed queue, occupied bed count).
    """
    semantic = await semantic_query(query, top_k=top_k)

    try:
        from app.ontology.builder import get_ontology_builder
        builder = get_ontology_builder()

        enriched = []
        for r in semantic.get("results", []):
            node_id = r.get("id", "")
            node_type = r.get("node_type", "")
            live_ctx = _enrich_with_live_state(node_id, node_type, builder)
            enriched.append({**r, **live_ctx})

        blocked = sum(1 for d in builder.discharges.values() if d.is_blocked)
        panics = sum(
            1 for a in builder.lab_critical_alerts.values()
            if a.readback_status != "Acknowledged"
        )
        dirty = sum(1 for b in builder.beds.values() if b.status == "dirty")
        occupied = sum(1 for b in builder.beds.values() if b.status == "occupied")

        return {
            **semantic,
            "results": enriched,
            "live_context_summary": {
                "blocked_discharges": blocked,
                "pending_panic_readbacks": panics,
                "dirty_turnaround_queue": dirty,
                "occupied_beds": occupied,
            },
        }
    except Exception as e:
        semantic["enrichment_error"] = str(e)
        return semantic


def _enrich_with_live_state(node_id: str, node_type: str, builder) -> Dict[str, Any]:
    """Look up live state from OntologyBuilder by node_id and node_type."""
    ctx: Dict[str, Any] = {}

    if node_type == "PatientNode":
        pat = builder.patients.get(node_id)
        if pat:
            bed = builder.beds.get(pat.current_bed_id) if pat.current_bed_id else None
            dis = next((d for d in builder.discharges.values() if d.uhid == node_id), None)
            ctx["live_state"] = {
                "name": pat.name,
                "status": pat.status,
                "current_bed": bed.bed_id if bed else None,
                "bed_status": bed.status if bed else None,
                "discharge_blocked": dis.is_blocked if dis else False,
                "blocker_reason": dis.blocker_reason if dis else None,
            }

    elif node_type == "BedNode":
        bed = builder.beds.get(node_id)
        if bed:
            ctx["live_state"] = {
                "status": bed.status,
                "ward": bed.ward,
                "current_patient": bed.current_patient_uhid,
            }

    elif node_type == "DischargeNode":
        dis = builder.discharges.get(node_id)
        if dis:
            ctx["live_state"] = {
                "is_blocked": dis.is_blocked,
                "blocker_reason": dis.blocker_reason,
                "clearance_billing": dis.clearance_billing,
                "clearance_pharmacy": dis.clearance_pharmacy,
                "clearance_clinical": dis.clearance_clinical,
                "gate_pass_issued": dis.gate_pass_issued,
            }

    elif node_type == "LabPanicAlertNode":
        alert = builder.lab_critical_alerts.get(node_id)
        if alert:
            ctx["live_state"] = {
                "parameter": alert.parameter_name,
                "value": alert.critical_value,
                "readback_status": alert.readback_status,
                "sla_breached": alert.is_sla_breached,
                "elapsed_minutes": alert.elapsed_minutes,
            }

    elif node_type == "BillNode":
        bill = builder.bills.get(node_id)
        if bill:
            ctx["live_state"] = {
                "total": bill.total_amount,
                "pending": bill.pending_amount,
                "has_dispute": bill.has_billing_dispute,
                "unbilled_consumables": bill.unbilled_consumables,
            }

    return ctx
