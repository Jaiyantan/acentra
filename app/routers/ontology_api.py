"""
Live Ontology API Router — Acentra Operations Intelligence Center
Mounts on FastAPI to provide:
1. Live Perspective Graph API (/api/v1/ontology/graph/live) directly from the Dynamic Operational Ontology.
2. Live Bottleneck Radar API (/api/v1/ontology/bottlenecks).
3. Real-time Action Mutations (/api/v1/ontology/action/{action_name}) to solve Context Decay.
4. Semantic Graph Traversal Endpoints (patient, bed turnaround, revenue risks, governance).
5. Interactive Operations Intelligence UI (/ontology).
"""

from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from app.ontology.builder import get_ontology_builder
from app.ontology.explorer import get_ontology_explorer
from app.ontology.graph_service import get_ontology_graph_service

router = APIRouter(tags=["Operational Ontology"])

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_VIS_JS_CANDIDATES = [
    ROOT_DIR / "app" / "static" / "vendor" / "vis-network.min.js",
    ROOT_DIR / "app" / "static" / "vis-network.min.js",
    ROOT_DIR / "vis-network.min.js",
]
VIS_JS_PATH = next((p for p in _VIS_JS_CANDIDATES if p.exists()), _VIS_JS_CANDIDATES[0])


@router.get("/vis-network.min.js")
async def get_vis_js():
    """Serves local standalone vis-network library with zero external CDN dependency."""
    if VIS_JS_PATH.exists():
        return FileResponse(VIS_JS_PATH, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="vis-network.min.js not found locally.")


@router.get("/api/v1/ontology/graph/live")
async def get_live_graph(
    perspective: str = Query("bottlenecks", description="Graph perspective: bottlenecks, patient_360, beds, governance, macro, full_ontology"),
    uhid: Optional[str] = Query(None, description="Patient UHID for patient_360 perspective"),
    ward: Optional[str] = Query(None, description="Ward name for beds perspective")
):
    """
    Returns real-time knowledge graph nodes and edges for the specified operational perspective.
    Blazing fast in-memory execution, eliminating the 2,000-node hairball anti-pattern.
    """
    gs = get_ontology_graph_service()
    return gs.get_perspective_subgraph(
        perspective=perspective,
        uhid=uhid,
        ward=ward
    )


@router.get("/api/v1/ontology/bottlenecks")
async def get_live_bottlenecks():
    """Returns live bottleneck radar for the Operations Intelligence Center."""
    explorer = get_ontology_explorer()
    return explorer.get_cross_departmental_bottlenecks()


@router.post("/api/v1/ontology/action/{action_name}")
async def execute_live_action(action_name: str):
    """
    Executes a governed state mutation in the ontology, solving Context Decay in real time:
    - settle_billing: Billing reconciles unbilled consumables, dissolving DIS-002 blocker and releasing gate pass.
    - resolve_panic: Documents verbal readback under POL-010, extinguishing 15-minute countdown SLA breach.
    - turnaround_bed: Cycles bed state (occupied -> dirty -> sanitized -> vacant).
    - reset_ontology: Restores baseline initial demonstration state.
    """
    builder = get_ontology_builder()
    gs = get_ontology_graph_service()

    if action_name == "settle_billing":
        target_dis = next((d for d in builder.discharges.values() if d.is_blocked and not d.clearance_billing), None)
        if not target_dis:
            target_dis = next((d for d in builder.discharges.values() if d.is_blocked), None)
        if not target_dis:
            return {"status": "noop", "message": "All inpatient discharges already financially cleared."}

        builder.settle_discharge_billing(target_dis.discharge_id)
        # Update standalone visual export
        gs.export_visual_graph()

        return {
            "status": "mutated",
            "action": "settle_billing",
            "message": f"Billing settled for discharge {target_dis.discharge_id}. Blocker dissolved. Gate pass released!",
            "discharge_id": target_dis.discharge_id,
            "gate_pass_issued": True
        }

    elif action_name == "resolve_panic":
        target_alert = next((a for a in builder.lab_critical_alerts.values() if a.readback_status != "Acknowledged"), None)
        if target_alert:
            builder.resolve_panic_lab_alert(target_alert.alert_id, "DOC-CARD-01")
            gs.export_visual_graph()
            return {
                "status": "mutated",
                "action": "resolve_panic",
                "message": f"Verbal readback documented for {target_alert.alert_id} ({target_alert.parameter_name}). POL-010 15m SLA alert cleared!",
                "alert_id": target_alert.alert_id,
                "readback_status": "Acknowledged"
            }

        return {"status": "noop", "message": "No critical lab alerts pending verbal readback."}

    elif action_name == "turnaround_bed":
        target_bed = next((b for b in builder.beds.values() if b.status == "dirty"), None)
        if target_bed:
            builder.update_bed_status(target_bed.bed_id, "vacant")
            gs.export_visual_graph()
            return {
                "status": "mutated",
                "action": "turnaround_bed",
                "bed_id": target_bed.bed_id,
                "message": f"Bed {target_bed.bed_id} sanitized by Housekeeping. Now VACANT and ready for admission!"
            }

        target_occ = next((b for b in builder.beds.values() if b.status == "occupied"), None)
        if target_occ:
            builder.update_bed_status(target_occ.bed_id, "dirty")
            gs.export_visual_graph()
            return {
                "status": "mutated",
                "action": "turnaround_bed",
                "bed_id": target_occ.bed_id,
                "message": f"Patient vacated Bed {target_occ.bed_id}. Shifted to DIRTY turnaround queue!"
            }

        return {"status": "noop", "message": "No beds available for turnaround transition."}

    elif action_name == "reset_ontology":
        builder.ingest_digital_twin()
        gs.export_visual_graph()
        return {
            "status": "reset",
            "action": "reset_ontology",
            "message": "Dynamic ontology baseline state successfully restored."
        }

    raise HTTPException(status_code=400, detail=f"Unknown operational action: {action_name}")


@router.get("/api/v1/ontology/patient/{uhid}")
async def get_patient_operational_context(uhid: str):
    """Returns 360-degree stitched operational digital twin context for a patient."""
    gs = get_ontology_graph_service()
    res = gs.query_patient_operational_graph(uhid)
    if res.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=res["message"])
    return res


@router.get("/api/v1/ontology/beds/turnaround")
async def get_bed_turnaround_status(ward: Optional[str] = None):
    """Returns real-time ward bed capacity, turnaround queue, and occupancy rate."""
    gs = get_ontology_graph_service()
    return gs.query_bed_states_and_turnaround(ward=ward)


@router.get("/api/v1/ontology/revenue/risks")
async def get_revenue_risks():
    """Returns cashless claim denials, billing disputes, and revenue leakage at risk."""
    gs = get_ontology_graph_service()
    return gs.query_revenue_risks_and_tpa_denials()


@router.get("/api/v1/ontology/governance/{entity_or_workflow_id}")
async def get_governance_rules(entity_or_workflow_id: str):
    """Returns governing SOPs, policies, required fields, and approval checkpoints."""
    gs = get_ontology_graph_service()
    return gs.query_governance_rules_for_state(entity_or_workflow_id)


@router.get("/api/v1/ontology/search")
async def semantic_search(
    q: str = Query(..., description="Natural-language query to search across the hospital knowledge graph"),
    search_type: str = Query("SUMMARIES", description="Cognee SearchType: SUMMARIES, CHUNKS, GRAPH_COMPLETION, INSIGHTS"),
    top_k: int = Query(5, ge=1, le=20, description="Maximum number of results to return"),
    enrich: bool = Query(True, description="Enrich results with live operational context from the digital twin"),
):
    """
    Semantic search across the SMCH Knowledge Graph.
    Uses fastembed BAAI/bge-small-en-v1.5 (384-dim) via direct LanceDB for operational data,
    and Cognee's index (Ollama LLM + fastembed) for governance KB.
    """
    from app.ontology.semantic_search import semantic_query, multi_context_search

    if enrich:
        return await multi_context_search(q, top_k=top_k)
    return await semantic_query(q, search_type=search_type, top_k=top_k)


@router.post("/api/v1/ontology/kb/ingest")
async def trigger_kb_ingestion(
    force: bool = Query(False, description="Force re-ingestion even if KB was previously indexed"),
):
    """
    Triggers ingestion of all 157 governance documents from knowledge_base/index/
    through Cognee's full semantic pipeline (Ollama LLM entity extraction + fastembed).
    Safe to call multiple times — skips if already ingested unless force=true.
    """
    from app.ontology.kb_ingestion import ingest_governance_knowledge_base

    result = await ingest_governance_knowledge_base(force=force)
    return result


@router.post("/api/v1/ontology/sync")
async def trigger_full_sync():
    """
    Runs the complete Knowledge Graph pipeline:
    1. Re-syncs all nodes and edges to Kùzu (structural graph)
    2. Re-embeds the live operational twin state into LanceDB (semantic layer)
    3. Exports updated Command Center HTML

    Use this after bulk DB loads or to recover from a stale state.
    """
    gs = get_ontology_graph_service()
    return await gs.sync_full_pipeline()


@router.get("/api/v1/ontology/config")
async def get_ontology_config():
    """
    Returns the current Cognee engine configuration and readiness status.
    Shows which AI provider, model, and vector/graph databases are active.
    AWS credentials are never returned — only presence is confirmed.
    """
    from app.ontology.cognee_config import get_cognee_status

    return get_cognee_status()


@router.get("/ontology", response_class=HTMLResponse)
async def get_ontology_dashboard():
    """
    Serves the SMCH Acentra Operations Intelligence Center.
    Interactive, perspective-based, live operational graph explorer.
    """
    gs = get_ontology_graph_service()
    return HTMLResponse(content=gs.generate_command_center_html(initial_perspective="bottlenecks"))
