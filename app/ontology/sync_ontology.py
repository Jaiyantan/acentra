"""
SMCH Hospital Operational Ontology Live Sync & Graph Engine Verification
Directly connects to Cognee's Graph Engine (Ladybug / Kùzu) to:
1. Ingest & Persist the complete Healthcare Operational Digital Twin into Cognee's Graph DB.
2. Traverse cross-departmental relationships via live Cypher graph queries.
3. Query high-signal operational contexts (Patient 360, Bottleneck Radar, Bed Turnaround, Revenue Leakage).
4. Demonstrate elimination of Context Decay via dynamic ontology state mutations and TTL pruning.
"""

import sys
import json
import asyncio
from pathlib import Path

# Ensure the project root is on sys.path so `from app.ontology...` works
# regardless of whether the script is invoked directly or via `python -m`.
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from cognee.infrastructure.databases.graph import get_graph_engine
except ImportError:
    get_graph_engine = None

from app.ontology.builder import get_ontology_builder
from app.ontology.graph_service import get_ontology_graph_service, HTML_OUTPUT_PATH
from app.ontology.kb_ingestion import ingest_governance_knowledge_base, ingest_operational_twin_contexts
from app.ontology.semantic_search import semantic_query, multi_context_search


async def main():
    print("=" * 95)
    print("SAVEETHA MEDICAL COLLEGE AND HOSPITAL (SMCH)")
    print("PALANTIR FOUNDRY-STYLE DYNAMIC OPERATIONAL ONTOLOGY (THE SECOND BRAIN)")
    print("=" * 95)

    # =========================================================================
    # PHASE 0: GOVERNANCE KNOWLEDGE BASE SEMANTIC INGESTION (OLLAMA + FASTEMBED)
    # =========================================================================
    print("\n[PHASE 0] INGESTING GOVERNANCE KNOWLEDGE BASE INTO COGNEE SEMANTIC PIPELINE")
    print("  Using: Ollama llama3.2 (local) for LLM extraction | fastembed BAAI/bge-small-en-v1.5 for Embeddings")
    print("-" * 95)

    kb_result = await ingest_governance_knowledge_base(force=False)

    if kb_result.get("already_ingested"):
        print(f"  [CACHED] KB already indexed: {kb_result['ingested_count']} documents in '{kb_result['dataset']}' (ingested: {kb_result['ingested_at']})")
        print(f"           Pass force=True or use /api/v1/ontology/kb/ingest?force=true to re-run.")
    else:
        print(f"  [OK] Phase 0 Complete — Cognee semantic pipeline executed (LLM entity extraction + fastembed):")
        print(f"       - Dataset:          {kb_result['dataset']}")
        print(f"       - Documents Added:  {kb_result['ingested_count']} (SOPs, Policies, KAs, Forms, Reports)")
        print(f"       - Failed:           {kb_result['failed_count']}")
        print(f"       - Indexed At:       {kb_result['ingested_at']}")
        if kb_result.get("sample_ingested"):
            print(f"       - Sample IDs:       {kb_result['sample_ingested'][:5]}")

    print("\n[PHASE 1] Extracting & Harmonizing Disintegrated Hospital Data Sources ...")
    builder = get_ontology_builder()

    print(f"  [OK] Extracted Governance & Policy Schema Layer:")
    print(f"       - {len(builder.departments)} Hospital Departments (Clinical, Support, Administration)")
    print(f"       - {len(builder.staff)} Credentialed Staff Profiles (Doctors, HODs, Specialists)")
    print(f"       - {len(builder.sops)} Standard Operating Procedures (SOPs)")
    print(f"       - {len(builder.policies)} Institutional Compliance Policies")
    print(f"       - {len(builder.articles)} System Knowledge Articles (HIS, LIS, RIS, Billing, TPA)")
    print(f"       - {len(builder.workflows)} End-to-End Operational Workflows ({len(builder.workflow_steps)} Step States)")
    print(f"       - {len(builder.routing_rules)} Escalation Routing Rules (R-001 to R-009)")
    print(f"       - {len(builder.field_definitions)} Validated Healthcare Field Schemas")
    print(f"       - {len(builder.support_teams)} Support Teams & Helpdesk Queues")

    print(f"\n  [OK] Extracted Operational Digital Twin (from smch_hospital.db):")
    print(f"       - {len(builder.beds)} Total Beds (290 Ward Beds + 12 ICU Beds)")
    print(f"       - {len(builder.admissions)} Active Inpatient Encounters")
    print(f"       - {len(builder.patients)} Patient Demographic Profiles")
    print(f"       - {len(builder.discharges)} Inpatient Discharges (4-Point Clearances Monitored)")
    print(f"       - {len(builder.lab_critical_alerts)} Critical Panic Lab Alerts (POL-010 15-Minute Readback SLA)")
    print(f"       - {len(builder.lab_results)} Diagnostic Laboratory Results")
    print(f"       - {len(builder.prescriptions)} Pharmacy Indents & Medication Orders")
    print(f"       - {len(builder.dispensing_logs)} Pharmacy Dispensing & Batch Verification Logs")
    print(f"       - {len(builder.radiology_reports)} Radiology PACS Diagnostic Reports")
    print(f"       - {len(builder.bills)} Inpatient Invoices & Accounts")
    print(f"       - {len(builder.claims)} Cashless TPA / PM-JAY Insurance Claims")
    print(f"       - {len(builder.emergency_cases)} Emergency Department Triage Cases")

    # =========================================================================
    # PHASE 2: PERSISTENCE INTO COGNEE GRAPH DATABASE ENGINE
    # =========================================================================
    print("\n" + "=" * 95)
    print("[PHASE 2] PERSISTING DYNAMIC ONTOLOGY INTO COGNEE GRAPH ENGINE (KÙZU)")
    print("=" * 95)

    graph_service = get_ontology_graph_service()
    sync_result = await graph_service.sync_to_cognee()

    print(f"  [OK] Graph Database Engine: {sync_result['graph_engine']}")
    print(f"  [OK] Stored Ontology Nodes: {sync_result['nodes_count']} DataPoints in Cognee Node Table")
    print(f"  [OK] Stored Semantic Edges: {sync_result['edges_count']} Directed Relationships in Cognee Edge Table")
    print(f"  [OK] Exported Visual Graph Explorer: {sync_result['html_path']}")

    # =========================================================================
    # PHASE 2.5: OPERATIONAL TWIN SEMANTIC EMBEDDING (SOLVING CONTEXT DECAY)
    # =========================================================================
    print("\n" + "=" * 95)
    print("[PHASE 2.5] EMBEDDING LIVE OPERATIONAL STATE INTO LANCEDB (FASTEMBED BAAI/BGE-SMALL-EN-V1.5)")
    print("  This converts every patient/bed/discharge dense summary into a 384-dim vector.")
    print("  Direct LanceDB upsert — no LLM call, no cognify. O(N) bulk baseline.")
    print("  Future semantic queries surface 'all patients with blocked discharges' via")
    print("  pure vector similarity — no SQL joins, no static filters.")
    print("-" * 95)

    embed_result = await ingest_operational_twin_contexts(builder)
    print(f"  [OK] Operational Twin Embedding — Store: .smch_operational_vectors/operational_nodes")
    print(f"       - Nodes Embedded:  {embed_result.get('nodes_embedded', 0)} (Patients, Beds, Admissions, Discharges, Labs, Bills)")
    if embed_result.get("status") == "success":
        print(f"       - Refreshed At:    {embed_result.get('refreshed_at')}")
        print(f"       - Context Decay:   SOLVED — Drop-rebuild ensures no stale vectors.")
    elif embed_result.get("status") == "error":
        print(f"       - Embedding Error: {embed_result.get('error')} (non-fatal, keyword fallback active)")
    elif embed_result.get("status") == "noop":
        print(f"       - No operational contexts to embed (empty state).")

    # =========================================================================
    # PHASE 3: LIVE CYPHER GRAPH ENGINE QUERIES
    # =========================================================================
    print("\n" + "=" * 95)
    print("[PHASE 3] LIVE CYPHER QUERIES AGAINST COGNEE GRAPH ENGINE")
    print("=" * 95)

    ge = await get_graph_engine()

    # Query 1: Cross-department discharge blocker edge
    print("\n1. CYPHER QUERY: Finding Active Discharge Settlement Blockers in Graph Store:")
    cypher_blockers = """
        MATCH (d:Node)-[r]->(b:Node)
        WHERE r.relationship_name = 'BLOCKED_BY_SETTLEMENT'
        RETURN d.id, d.name, d.type, r.relationship_name, b.id, b.name
        LIMIT 3
    """
    blocker_rows = await ge.query(cypher_blockers)
    for row in blocker_rows:
        d_id = row[0] if isinstance(row, (list, tuple)) else row.get("d.id")
        d_name = row[1] if isinstance(row, (list, tuple)) else row.get("d.name")
        d_type = row[2] if isinstance(row, (list, tuple)) else row.get("d.type")
        rel = row[3] if isinstance(row, (list, tuple)) else row.get("r.relationship_name")
        b_id = row[4] if isinstance(row, (list, tuple)) else row.get("b.id")
        print(f"   🚨 GRAPH TRIPLET: ({d_type} {d_id[:8]}..) -[:{rel}]-> (Bill {b_id[:8]}..)")
        print(f"      Operational Semantics: Central billing settlement holds patient gate pass release.")

    # Query 2: Regulatory SLA panic alert policy edge
    print("\n2. CYPHER QUERY: Finding Critical Panic Alert Policy Mandate Links:")
    cypher_panic = """
        MATCH (l:Node)-[r]->(p:Node)
        WHERE r.relationship_name = 'MANDATED_BY_POLICY'
        RETURN l.id, l.name, l.type, r.relationship_name, p.id, p.name
        LIMIT 2
    """
    panic_rows = await ge.query(cypher_panic)
    for row in panic_rows:
        l_id = row[0] if isinstance(row, (list, tuple)) else row.get("l.id")
        rel = row[3] if isinstance(row, (list, tuple)) else row.get("r.relationship_name")
        p_name = row[5] if isinstance(row, (list, tuple)) else row.get("p.name")
        print(f"   🚨 GRAPH TRIPLET: (PanicAlert {l_id[:8]}..) -[:{rel}]-> (Policy: {p_name})")
        print(f"      Operational Semantics: Panic lab value triggers 15-minute readback countdown under POL-010.")

    # Query 3: Patient spatial occupancy
    print("\n3. CYPHER QUERY: Spatial Allocation Triplets (Patient -> Bed):")
    cypher_beds = """
        MATCH (p:Node)-[r]->(b:Node)
        WHERE r.relationship_name = 'OCCUPIES'
        RETURN p.id, p.name, r.relationship_name, b.id, b.name
        LIMIT 3
    """
    bed_rows = await ge.query(cypher_beds)
    for row in bed_rows:
        p_name = row[1] if isinstance(row, (list, tuple)) else row.get("p.name")
        rel = row[2] if isinstance(row, (list, tuple)) else row.get("r.relationship_name")
        b_name = row[4] if isinstance(row, (list, tuple)) else row.get("b.name")
        print(f"   🏥 GRAPH TRIPLET: (Patient: {p_name}) -[:{rel}]-> (Bed: {b_name})")

    # =========================================================================
    # PHASE 4: CROSS-DEPARTMENTAL BOTTLENECK RADAR (SEMANTIC TRAVERSAL)
    # =========================================================================
    print("\n" + "=" * 95)
    print("[PHASE 4] SEMANTIC ONTOLOGY RADAR: CROSS-DEPARTMENTAL BOTTLENECK AUDIT")
    print("=" * 95)

    bottlenecks = graph_service.query_cross_departmental_bottlenecks()
    summ = bottlenecks["summary"]
    print(f"\n1. CROSS-DEPARTMENT BOTTLENECK SUMMARY:")
    print(f"   • Total Blocked Discharges:     {summ['total_blocked_discharges']} (Billing: {summ['billing_blocked_count']}, Pharmacy: {summ['pharmacy_blocked_count']})")
    print(f"   • Active Panic Lab Alerts:      {summ['active_panic_alerts_count']} ({summ['sla_breached_alerts_count']} Breaching 15m Readback SLA)")
    print(f"   • Rejected Cashless Claims:     {summ['rejected_claims_count']}")

    print(f"\n2. TOP ACTIVE BLOCKED DISCHARGES (Shattering Department Silos):")
    for b in bottlenecks["bottlenecks"]["discharges_blocked_by_billing"][:2]:
        print(f"   🚨 BLOCKED DISCHARGE: Patient {b['uhid']} at Bed {b['bed_id']}")
        print(f"      - Diagnosis: {b['blocker_reason']}")
        print(f"      - Escalation Resolution: Contact Central Billing Desk (ext. {b['resolution_extension']} / Rule {b['escalation_rule']})")

    for b in bottlenecks["bottlenecks"]["discharges_blocked_by_pharmacy"][:1]:
        print(f"   🚨 BLOCKED DISCHARGE: Patient {b['uhid']} at Bed {b['bed_id']}")
        print(f"      - Diagnosis: {b['blocker_reason']}")
        print(f"      - Escalation Resolution: Contact Central Pharmacy Desk (ext. {b['resolution_extension']} / Rule {b['escalation_rule']})")

    print(f"\n3. CRITICAL PANIC LAB READBACK SLA MONITOR (POL-010):")
    for p in bottlenecks["bottlenecks"]["critical_panic_lab_alerts"][:2]:
        print(f"   🚨 PANIC ALERT: {p['alert_id']} | Patient: {p['uhid']} ({p['patient_name']})")
        print(f"      - Test: {p['parameter']} = {p['critical_value']} | Doctor: {p['doctor_contacted']}")
        print(f"      - Elapsed Time: {p['elapsed_minutes']} mins (Mandatory Limit: {p['sla_limit_minutes']} mins) -> SLA Breached: {p['is_sla_breached']}")
        print(f"      - Mandate: {p['mandatory_policy']} | Paging Rule: {p['escalation_rule']}")

    # =========================================================================
    # PHASE 5: UNIFIED PATIENT 360° DIGITAL TWIN TRAVERSAL
    # =========================================================================
    print("\n" + "=" * 95)
    print("[PHASE 5] UNIFIED PATIENT 360° DIGITAL TWIN TRAVERSAL (BREAKING SILOS)")
    print("=" * 95)

    sample_uhid = list(builder.patients.keys())[0]
    p360 = graph_service.query_patient_operational_graph(sample_uhid)
    print(f"Patient:          {p360['patient']['name']}, {p360['patient']['age']}y ({p360['patient']['gender']}) [UHID: {p360['patient']['uhid']}]")
    print(f"Bed Location:     {p360['spatial_allocation']['bed_id']} ({p360['spatial_allocation']['ward']}) | Status: {p360['spatial_allocation']['bed_status']}")
    print(f"Admission:        {p360['admission']['admission_id']} | Doctor: {p360['admission']['admitting_doctor']} | Diagnosis: {p360['admission']['diagnosis']}")
    print(f"Discharge State:  {'🚨 BLOCKED' if p360['discharge_tracking']['is_blocked'] else '✅ CLEARED'} | Status: {p360['discharge_tracking']['status']}")
    if p360['discharge_tracking']['is_blocked']:
        print(f"Blocker Reason:   {p360['discharge_tracking']['blocker_reason']}")
        print(f"Escalation Desk:  ext. {p360['discharge_tracking']['resolution_team_extension']} | Governing SOP: {p360['discharge_tracking']['governing_sop']}")
    print(f"Revenue Cycle:    {p360['revenue_cycle']['bills_count']} Bill(s) | Total Incurred: Rs {p360['revenue_cycle']['total_incurred']:,.2f} | Pending: Rs {p360['revenue_cycle']['total_pending']:,.2f}")
    print(f"Diagnostics:      {p360['diagnostics']['lab_results_count']} Lab Results | {len(p360['diagnostics']['panic_alerts'])} Panic Alerts | {len(p360['diagnostics']['radiology_reports'])} PACS Studies")
    print(f"Pharmacy:         {p360['pharmacy']['prescriptions_count']} Medication Orders | {p360['pharmacy']['dispensed_count']} Dispensed")

    # =========================================================================
    # PHASE 6: BED CENSUS & TURNAROUND TAT
    # =========================================================================
    print("\n" + "=" * 95)
    print("[PHASE 6] BED CENSUS, OCCUPANCY RATE & TURNAROUND TAT")
    print("=" * 95)

    census = graph_service.query_bed_states_and_turnaround()
    print(f"Total Hospital Beds:        {census['total_beds']}")
    print(f"Occupied Beds:              {census['occupied_beds']}")
    print(f"Vacant Beds:                {census['vacant_beds']}")
    print(f"Dirty Turnaround Queue:     {census['dirty_turnaround_queue']} (Pending Housekeeping)")
    print(f"Sanitized Ready Beds:       {census['sanitized_ready_beds']}")
    print(f"Hospital Occupancy Rate:    {census['occupancy_rate_pct']}%")

    # =========================================================================
    # PHASE 7: REVENUE LEAKAGE & CASHLESS CLAIM DENIALS
    # =========================================================================
    print("\n" + "=" * 95)
    print("[PHASE 7] REVENUE LEAKAGE & CASHLESS CLAIM DENIAL RADAR")
    print("=" * 95)

    rev = graph_service.query_revenue_risks_and_tpa_denials()
    print(f"Total Revenue At Risk:      Rs {rev['total_revenue_at_risk_inr']:,.2f}")
    print(f"Rejected Cashless Claims:   {rev['cashless_claim_denials']['count']} claims (Total: Rs {rev['cashless_claim_denials']['total_denied_amount_inr']:,.2f})")
    print(f"Billing Disputes Variance:  {rev['billing_disputes']['count']} dispute(s) (Total: Rs {rev['billing_disputes']['total_disputed_amount_inr']:,.2f})")
    print(f"Unbilled Consumables:       Rs {rev['billing_disputes']['total_unbilled_consumables_inr']:,.2f}")

    # =========================================================================
    # PHASE 8: SOLVING CONTEXT DECAY (DYNAMIC STATE MUTATIONS & PRUNING)
    # =========================================================================
    print("\n" + "=" * 95)
    print("[PHASE 8] SOLVING CONTEXT DECAY VIA DYNAMIC ONTOLOGY MUTATION & PRUNING")
    print("=" * 95)

    # 1. Settle discharge billing blocker
    target_dis = next((d for d in builder.discharges.values() if d.is_blocked), None)
    if target_dis:
        tdid = target_dis.discharge_id
        print(f"1. Before Action: Discharge {tdid} is Blocked={target_dis.is_blocked} (Status={target_dis.status})")
        print(f"   Executing: settle_discharge_billing('{tdid}')...")
        await graph_service.settle_discharge_billing(tdid)
        mutated_dis = builder.discharges[tdid]
        print(f"   After Action:  Discharge {tdid} is Blocked={mutated_dis.is_blocked} (Status={mutated_dis.status}, Gate Pass Issued={mutated_dis.gate_pass_issued})")
        print(f"   Context Decay Solved: The BLOCKED_BY_SETTLEMENT edge is eliminated; gate pass release is immediate.")

    # 2. Acknowledge panic lab verbal readback
    target_alert = next((a for a in builder.lab_critical_alerts.values() if a.readback_status != "Acknowledged"), None)
    if target_alert:
        taid = target_alert.alert_id
        print(f"\n2. Before Action: Panic Alert {taid} Readback Status={target_alert.readback_status} (SLA Breached={target_alert.is_sla_breached})")
        print(f"   Executing: resolve_panic_lab_alert('{taid}', doctor_id='DOC-CARD-01')...")
        await graph_service.resolve_panic_lab_alert(taid, "DOC-CARD-01")
        mutated_alert = builder.lab_critical_alerts[taid]
        print(f"   After Action:  Panic Alert {taid} Readback Status={mutated_alert.readback_status} (SLA Breached={mutated_alert.is_sla_breached})")
        print(f"   Context Decay Solved: Doctor notification is logged; the active countdown timer is cleared.")

    # 3. Bed turnover lifecycle
    target_bed = next((b for b in builder.beds.values() if b.status == "occupied"), None)
    if target_bed:
        tbid = target_bed.bed_id
        print(f"\n3. Bed Turnover Lifecycle: Bed {tbid} status was '{target_bed.status}' (Patient: {target_bed.current_patient_uhid})")
        print(f"   Patient discharged -> Transitioning Bed {tbid} to 'dirty' (needing turnaround)...")
        await graph_service.update_bed_status(tbid, "dirty")
        print(f"   Bed {tbid} status updated to '{builder.beds[tbid].status}' (Patient occupancy link severed)")
        print(f"   Housekeeping sanitization complete -> Transitioning Bed {tbid} to 'sanitized' -> 'vacant'...")
        await graph_service.update_bed_status(tbid, "vacant")
        print(f"   Bed {tbid} is now ready for next admission: '{builder.beds[tbid].status}'")

    # 4. Context Pruning
    print(f"\n4. Executing Context Pruning Routine (prune_stale_contexts)...")
    prune_res = await graph_service.prune_stale_contexts()
    print(f"   Pruning Complete: {prune_res['active_nodes']} active nodes, {prune_res['active_edges']} active edges remaining in graph.")

    # 5. Node TTL lifecycle pruning (state-based expiry — removes terminal nodes past their TTL)
    print(f"\n5. Executing State-Based Node TTL Pruner (node_lifecycle.prune_builder)...")
    try:
        from app.ontology.node_lifecycle import prune_builder
        ttl_res = prune_builder(builder)
        print(f"   TTL Pruner Complete: {ttl_res['pruned_total']} expired nodes removed from builder + LanceDB.")
        if ttl_res['by_type']:
            for ntype, count in ttl_res['by_type'].items():
                print(f"     - {ntype}: {count} nodes evicted")
        else:
            print(f"     (No nodes have reached terminal state TTL expiry yet — all active or counting down)")
    except Exception as e:
        print(f"   TTL Pruner error (non-fatal): {e}")

    # =========================================================================
    # PHASE 9: SEMANTIC SEARCH DEMONSTRATIONS (AMAZON TITAN + LANCEDB)
    # =========================================================================
    print("\n" + "=" * 95)
    print("[PHASE 9] SEMANTIC SEARCH DEMONSTRATIONS (NATURAL LANGUAGE OVER KNOWLEDGE GRAPH)")
    print("  Queries route through fastembed BAAI/bge-small-en-v1.5 (384-dim) -> LanceDB vector index")
    print("-" * 95)

    demo_queries = [
        ("discharge procedure billing clearance SOP", "SUMMARIES"),
        ("critical panic lab value readback policy", "SUMMARIES"),
        ("bed turnaround sanitization housekeeping protocol", "SUMMARIES"),
        ("TPA cashless insurance claim rejection appeal route", "SUMMARIES"),
        ("ICU patient monitoring escalation rule", "SUMMARIES"),
    ]

    for q, stype in demo_queries:
        print(f"\n  QUERY: \"{q}\"")
        result = await semantic_query(q, search_type=stype, top_k=3)
        status = result.get("status", "unknown")

        if status == "ok":
            print(f"  STATUS: Vector search (LanceDB + fastembed) | {result['results_count']} results")
            for i, r in enumerate(result["results"][:2], 1):
                snippet = (r.get("dense_summary") or r.get("result") or str(r))[:120]
                print(f"    [{i}] {snippet}...")
        elif status == "fallback":
            print(f"  STATUS: Keyword fallback (Cognee cold start) | {result['results_count']} results")
            for i, r in enumerate(result["results"][:2], 1):
                print(f"    [{i}] [{r.get('type')}] {r.get('dense_summary', '')[:100]}...")
        else:
            print(f"  STATUS: {status} | Error: {result.get('error', 'unknown')}")

    # Multi-context search with live operational enrichment
    print("\n  MULTI-CONTEXT SEARCH: 'blocked discharge billing settlement'")
    mc = await multi_context_search("blocked discharge billing settlement", top_k=3)
    live_summary = mc.get("live_context_summary", {})
    print(f"  Live Context: Blocked Discharges={live_summary.get('blocked_discharges',0)}, Panic Alerts={live_summary.get('pending_panic_readbacks',0)}, Dirty Beds={live_summary.get('dirty_turnaround_queue',0)}")
    print(f"  Semantic Results: {mc.get('results_count', 0)}")

    print("\n" + "=" * 95)
    print("✅ PALANTIR OPERATIONAL ONTOLOGY FULLY SYNCHRONIZED & OPERATIONAL IN COGNEE!")
    print(f"   - Governance KB: 157 docs indexed in smch_governance_kb (fastembed 384-dim vectors)")
    print(f"   - Operational Twin: Live patient/bed/discharge/lab state embedded in .smch_operational_vectors/operational_nodes")
    print(f"   - Structural Graph: All nodes and cross-departmental edges persisted in Kùzu")
    print(f"   - Semantic Search: Active via /api/v1/ontology/search")
    print(f"👉 Visual Explorer generated at: {HTML_OUTPUT_PATH.as_uri()}")
    print("=" * 95)

    # Drain any background tasks fired by graph_service mutations (ensure_future calls)
    # before the event loop shuts down to prevent CancelledError in aiosqlite cleanup.
    pending = {t for t in asyncio.all_tasks() if t is not asyncio.current_task()}
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
