"""
SMCH Hospital Operational Ontology Graph Service
Connects to Cognee's Graph Engine (Ladybug / Kùzu) and manages:
1. Ingesting and persisting all Ontology Nodes and Edges directly into Cognee's Graph DB.
2. Cross-departmental relationship stitching (breaking silos between Nursing, Pharmacy, Billing, Lab, TPA).
3. Dynamic State Mutation & Context Pruning (eliminating Context Decay).
4. Semantic Graph Traversal & Cypher Query Engine for downstream operational consumers.
5. Exporting an interactive, full-screen Vis.js visual graph explorer (ontology_graph.html).
"""

import sys
import json
import uuid
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional

try:
    from cognee.infrastructure.databases.graph import get_graph_engine
except ImportError:
    get_graph_engine = None
from app.ontology.builder import OntologyBuilder, get_ontology_builder

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
HTML_OUTPUT_PATH = ROOT_DIR / "app" / "static" / "ontology_graph.html"

# Deterministic namespace for SMCH Ontology
SMCH_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "smch.saveetha.hospital.ontology")


def make_smch_uuid(category: str, key: str) -> uuid.UUID:
    """Generates a stable, reproducible UUID for every ontology node."""
    return uuid.uuid5(SMCH_NAMESPACE, f"{category}:{str(key).strip().upper()}")


class OntologyGraphService:
    """Manages Cognee's graph engine storage, Cypher queries, and visual graph export."""

    def __init__(self, builder: Optional[OntologyBuilder] = None):
        self.builder = builder or get_ontology_builder()

    async def sync_to_cognee(self) -> Dict[str, Any]:
        """
        Synchronizes all operational digital twin objects and governance entities
        directly into Cognee's Graph Engine (Kùzu).
        """
        if get_graph_engine is None:
            return {
                "status": "in_memory_mode",
                "message": "cognee is not installed. Operational ontology graph is serving in-memory.",
                "synced_nodes": len(self.builder.departments) + len(self.builder.staff) + len(self.builder.patients),
                "synced_edges": 0,
            }
        ge = await get_graph_engine()

        nodes: List[Any] = []
        edges: List[Tuple[str, str, str, Dict[str, Any]]] = []

        # ---------------------------------------------------------------------
        # 1. PREPARE GOVERNANCE NODES
        # ---------------------------------------------------------------------
        # Departments
        for d_id, dept in self.builder.departments.items():
            dept.id = make_smch_uuid("dept", d_id)
            nodes.append(dept)

        # Staff
        for s_id, stf in self.builder.staff.items():
            stf.id = make_smch_uuid("staff", s_id)
            nodes.append(stf)

        # SOPs
        for doc_id, sop in self.builder.sops.items():
            sop.id = make_smch_uuid("sop", doc_id)
            nodes.append(sop)

        # Policies
        for doc_id, pol in self.builder.policies.items():
            pol.id = make_smch_uuid("policy", doc_id)
            nodes.append(pol)

        # Knowledge Articles
        for doc_id, art in self.builder.articles.items():
            art.id = make_smch_uuid("article", doc_id)
            nodes.append(art)

        # Workflows
        for wf_id, wf in self.builder.workflows.items():
            wf.id = make_smch_uuid("workflow", wf_id)
            nodes.append(wf)

        # Workflow Steps
        for step_id, step in self.builder.workflow_steps.items():
            step.id = make_smch_uuid("step", step_id)
            nodes.append(step)

        # Routing Rules
        for r_id, rule in self.builder.routing_rules.items():
            rule.id = make_smch_uuid("rule", r_id)
            nodes.append(rule)

        # Support Teams
        for t_id, team in self.builder.support_teams.items():
            team.id = make_smch_uuid("team", t_id)
            nodes.append(team)

        # Field Definitions
        for f_name, field in self.builder.field_definitions.items():
            field.id = make_smch_uuid("field", f_name)
            nodes.append(field)

        # ---------------------------------------------------------------------
        # 2. PREPARE OPERATIONAL DIGITAL TWIN NODES
        # ---------------------------------------------------------------------
        # Patients
        for uhid, pat in self.builder.patients.items():
            pat.id = make_smch_uuid("patient", uhid)
            nodes.append(pat)

        # Beds
        for b_id, bed in self.builder.beds.items():
            bed.id = make_smch_uuid("bed", b_id)
            nodes.append(bed)

        # Admissions
        for a_id, adm in self.builder.admissions.items():
            adm.id = make_smch_uuid("adm", a_id)
            nodes.append(adm)

        # Discharges
        for d_id, dis in self.builder.discharges.items():
            dis.id = make_smch_uuid("dis", d_id)
            nodes.append(dis)

        # Diagnostic Orders
        for o_id, ordr in self.builder.orders.items():
            ordr.id = make_smch_uuid("order", o_id)
            nodes.append(ordr)

        # Lab Results
        for l_id, lab in self.builder.lab_results.items():
            lab.id = make_smch_uuid("lab", l_id)
            nodes.append(lab)

        # Critical Panic Lab Alerts (POL-010)
        for al_id, alert in self.builder.lab_critical_alerts.items():
            alert.id = make_smch_uuid("panic_alert", al_id)
            nodes.append(alert)

        # Pharmacy Prescriptions
        for rx_id, rx in self.builder.prescriptions.items():
            rx.id = make_smch_uuid("rx", rx_id)
            nodes.append(rx)

        # Pharmacy Dispensing Logs
        for dsp_id, dsp in self.builder.dispensing_logs.items():
            dsp.id = make_smch_uuid("dispense", dsp_id)
            nodes.append(dsp)

        # Radiology PACS Reports
        for rad_id, rad in self.builder.radiology_reports.items():
            rad.id = make_smch_uuid("radiology", rad_id)
            nodes.append(rad)

        # Emergency Triage Cases
        for ed_id, ed in self.builder.emergency_cases.items():
            ed.id = make_smch_uuid("emergency", ed_id)
            nodes.append(ed)

        # Bills & Accounts
        for b_id, bil in self.builder.bills.items():
            bil.id = make_smch_uuid("bill", b_id)
            nodes.append(bil)

        # Insurance Claims
        for c_id, clm in self.builder.claims.items():
            clm.id = make_smch_uuid("claim", c_id)
            nodes.append(clm)

        # ---------------------------------------------------------------------
        # 3. BUILD CROSS-DEPARTMENTAL SEMANTIC EDGES (SHATTERING SILOS)
        # ---------------------------------------------------------------------

        # A. Patient <-> Bed (Spatial Allocation)
        for uhid, pat in self.builder.patients.items():
            if pat.current_bed_id and pat.current_bed_id in self.builder.beds:
                bed = self.builder.beds[pat.current_bed_id]
                edges.append((str(pat.id), str(bed.id), "OCCUPIES", {
                    "relationship_name": "OCCUPIES",
                    "label": "Occupies Bed",
                    "status": bed.status
                }))

        # B. Patient <-> Admission (Clinical Encounter)
        for uhid, pat in self.builder.patients.items():
            if pat.active_admission_id and pat.active_admission_id in self.builder.admissions:
                adm = self.builder.admissions[pat.active_admission_id]
                edges.append((str(pat.id), str(adm.id), "HAS_ADMISSION", {
                    "relationship_name": "HAS_ADMISSION",
                    "label": "Inpatient Admission",
                    "diagnosis": adm.admitting_diagnosis
                }))

        # C. Admission <-> Bed & Doctor
        for a_id, adm in self.builder.admissions.items():
            if adm.bed_id and adm.bed_id in self.builder.beds:
                bed = self.builder.beds[adm.bed_id]
                edges.append((str(adm.id), str(bed.id), "ASSIGNED_BED", {
                    "relationship_name": "ASSIGNED_BED",
                    "label": "Assigned Bed"
                }))
            if adm.admitting_doctor_id and adm.admitting_doctor_id in self.builder.staff:
                doc = self.builder.staff[adm.admitting_doctor_id]
                edges.append((str(adm.id), str(doc.id), "ATTENDED_BY", {
                    "relationship_name": "ATTENDED_BY",
                    "label": "Treating Doctor",
                    "role": doc.role
                }))

        # D. Admission <-> Discharge (Discharge Tracking)
        for d_id, dis in self.builder.discharges.items():
            if dis.admission_id and dis.admission_id in self.builder.admissions:
                adm = self.builder.admissions[dis.admission_id]
                edges.append((str(adm.id), str(dis.id), "HAS_DISCHARGE_ORDER", {
                    "relationship_name": "HAS_DISCHARGE_ORDER",
                    "label": "Discharge Order",
                    "is_blocked": dis.is_blocked
                }))

        # E. Discharge <-> Bill (THE CROSS-DEPARTMENTAL SETTLEMENT BOTTLENECK)
        for d_id, dis in self.builder.discharges.items():
            # Find matching bill for patient
            matched_bill = next((b for b in self.builder.bills.values() if b.uhid == dis.uhid), None)
            if matched_bill:
                if dis.is_blocked and not dis.clearance_billing:
                    edges.append((str(dis.id), str(matched_bill.id), "BLOCKED_BY_SETTLEMENT", {
                        "relationship_name": "BLOCKED_BY_SETTLEMENT",
                        "label": "🚨 Blocked by Unsettled Bill",
                        "outstanding": matched_bill.pending_amount,
                        "dispute": matched_bill.dispute_amount
                    }))
                else:
                    edges.append((str(dis.id), str(matched_bill.id), "FINANCIALLY_CLEARED", {
                        "relationship_name": "FINANCIALLY_CLEARED",
                        "label": "Financially Cleared"
                    }))

        # F. Discharge <-> Governance Mandate (SOP-DIS-001) - Only link blocked discharges to prevent radial hairball
        sop_dis = next((s for k, s in self.builder.sops.items() if "DIS-001" in k or "DISCHARGE" in k.upper()), None)
        if sop_dis:
            for d_id, dis in self.builder.discharges.items():
                if dis.is_blocked:
                    edges.append((str(dis.id), str(sop_dis.id), "GOVERNED_BY_SOP", {
                        "relationship_name": "GOVERNED_BY_SOP",
                        "label": "🚨 Governed by SOP-DIS-001",
                        "sop_title": sop_dis.title
                    }))

        # G. Discharge <-> Escalation Routing Rule
        for d_id, dis in self.builder.discharges.items():
            if dis.escalation_rule_id and dis.escalation_rule_id in self.builder.routing_rules:
                rule = self.builder.routing_rules[dis.escalation_rule_id]
                edges.append((str(dis.id), str(rule.id), "ESCALATES_TO_RULE", {
                    "relationship_name": "ESCALATES_TO_RULE",
                    "label": f"Escalates via Rule {rule.rule_id}",
                    "team": rule.route_to_team
                }))

        # H. Patient & Admission <-> Bill & Insurance Claim
        for b_id, bil in self.builder.bills.items():
            if bil.uhid and bil.uhid in self.builder.patients:
                pat = self.builder.patients[bil.uhid]
                edges.append((str(pat.id), str(bil.id), "INCURRED_BILL", {
                    "relationship_name": "INCURRED_BILL",
                    "label": "Incurred Bill",
                    "amount": bil.total_amount
                }))
            # Dispute escalation
            if bil.has_billing_dispute and "R-008" in self.builder.routing_rules:
                r8 = self.builder.routing_rules["R-008"]
                edges.append((str(bil.id), str(r8.id), "DISPUTE_ESCALATED_VIA", {
                    "relationship_name": "DISPUTE_ESCALATED_VIA",
                    "label": "🚨 Billing Dispute Escalation",
                    "dispute_variance": bil.dispute_amount
                }))

        for c_id, clm in self.builder.claims.items():
            # Cross-link with patient
            if clm.uhid and clm.uhid in self.builder.patients:
                pat = self.builder.patients[clm.uhid]
                edges.append((str(pat.id), str(clm.id), "HAS_CLAIM", {
                    "relationship_name": "HAS_CLAIM",
                    "label": "Insurance Claim",
                    "status": clm.status
                }))
            # Rejection escalation
            if clm.requires_dispute_appeal and "R-004" in self.builder.routing_rules:
                r4 = self.builder.routing_rules["R-004"]
                edges.append((str(clm.id), str(r4.id), "REJECTION_ESCALATED_VIA", {
                    "relationship_name": "REJECTION_ESCALATED_VIA",
                    "label": "⚠️ TPA Rejection Appeal Route",
                    "insurer": clm.insurer
                }))

        # I. Lab Critical Alerts <-> Patient, Policy (POL-010 15-Min SLA), and Escalation Rule (R-009)
        pol_panic = next((p for k, p in self.builder.policies.items() if "POL-010" in k or "PANIC" in k.upper()), None)
        rule_panic = self.builder.routing_rules.get("R-009")

        for al_id, alert in self.builder.lab_critical_alerts.items():
            # Link to patient
            if alert.uhid and alert.uhid in self.builder.patients:
                pat = self.builder.patients[alert.uhid]
                edges.append((str(pat.id), str(alert.id), "TRIGGERS_PANIC_ALERT", {
                    "relationship_name": "TRIGGERS_PANIC_ALERT",
                    "label": "🚨 Critical Panic Alert",
                    "parameter": alert.parameter_name,
                    "value": alert.critical_value
                }))

            # Link to institutional policy POL-010
            if pol_panic and alert.readback_status != "Acknowledged":
                edges.append((str(alert.id), str(pol_panic.id), "MANDATED_BY_POLICY", {
                    "relationship_name": "MANDATED_BY_POLICY",
                    "label": "🚨 POL-010 15-Min SLA",
                    "sla_mins": alert.sla_minutes,
                    "elapsed_mins": alert.elapsed_minutes
                }))

            # Link to consultant paging rule R-009
            if rule_panic and alert.readback_status != "Acknowledged":
                edges.append((str(alert.id), str(rule_panic.id), "PAGES_CONSULTANT_VIA", {
                    "relationship_name": "PAGES_CONSULTANT_VIA",
                    "label": "🚨 Consultant Readback Page",
                    "doctor": alert.doctor_contacted
                }))

        # J. Pharmacy Prescriptions & Dispensing Logs
        for rx_id, rx in self.builder.prescriptions.items():
            if rx.uhid and rx.uhid in self.builder.patients:
                pat = self.builder.patients[rx.uhid]
                edges.append((str(pat.id), str(rx.id), "HAS_PRESCRIPTION", {
                    "relationship_name": "HAS_PRESCRIPTION",
                    "label": "Prescription Indent",
                    "status": rx.status
                }))

        for dsp_id, dsp in self.builder.dispensing_logs.items():
            if dsp.intake_id and dsp.intake_id in self.builder.prescriptions:
                rx = self.builder.prescriptions[dsp.intake_id]
                edges.append((str(rx.id), str(dsp.id), "DISPENSED_AS", {
                    "relationship_name": "DISPENSED_AS",
                    "label": "Dispensed Medication",
                    "drug": dsp.drug_name
                }))

        # K. Radiology PACS Reports
        for rad_id, rad in self.builder.radiology_reports.items():
            if rad.uhid and rad.uhid in self.builder.patients:
                pat = self.builder.patients[rad.uhid]
                edges.append((str(pat.id), str(rad.id), "HAS_RADIOLOGY_STUDY", {
                    "relationship_name": "HAS_RADIOLOGY_STUDY",
                    "label": "Radiology PACS Study",
                    "modality": rad.modality
                }))

        # L. Emergency Triage Cases
        for ed_id, ed in self.builder.emergency_cases.items():
            if ed.uhid and ed.uhid in self.builder.patients:
                pat = self.builder.patients[ed.uhid]
                edges.append((str(pat.id), str(ed.id), "TRIAGED_IN_ED", {
                    "relationship_name": "TRIAGED_IN_ED",
                    "label": f"ED Triage {ed.triage_level}",
                    "triage": ed.triage_level
                }))

        # M. Routing Rules <-> Support Teams
        for r_id, rule in self.builder.routing_rules.items():
            for t_id, team in self.builder.support_teams.items():
                if (rule.route_to_team.lower() in team.name.lower() or
                    team.name.lower() in rule.route_to_team.lower() or
                    rule.helpdesk_queue == team.helpdesk_queue):
                    edges.append((str(rule.id), str(team.id), "DISPATCHES_TO_TEAM", {
                        "relationship_name": "DISPATCHES_TO_TEAM",
                        "label": "Dispatches to Team",
                        "queue": team.helpdesk_queue,
                        "extension": team.contact_extension
                    }))
                    break

        # N. Staff <-> Department
        for s_id, stf in self.builder.staff.items():
            for d_id, dept in self.builder.departments.items():
                if (stf.department_id.lower() in dept.name.lower() or
                    dept.name.lower() in stf.department_id.lower()):
                    edges.append((str(stf.id), str(dept.id), "MEMBER_OF_DEPARTMENT", {
                        "relationship_name": "MEMBER_OF_DEPARTMENT",
                        "label": "Department Member"
                    }))
                    break

        # O. Workflow <-> Steps <-> Fields
        for w_id, wf in self.builder.workflows.items():
            for s_id, step in self.builder.workflow_steps.items():
                if step.workflow_id == w_id:
                    edges.append((str(wf.id), str(step.id), "CONTAINS_STEP", {
                        "relationship_name": "CONTAINS_STEP",
                        "label": f"Step {step.step_number}",
                        "step_name": step.step_name
                    }))
                    for fn in step.required_fields:
                        if fn in self.builder.field_definitions:
                            fld = self.builder.field_definitions[fn]
                            edges.append((str(step.id), str(fld.id), "REQUIRES_FIELD", {
                                "relationship_name": "REQUIRES_FIELD",
                                "label": "Requires Field",
                                "field": fn
                            }))

        # ---------------------------------------------------------------------
        # 4. PERSIST DIRECTLY INTO COGNEE GRAPH ENGINE
        # ---------------------------------------------------------------------
        await ge.add_nodes(nodes)
        await ge.add_edges(edges)

        # ---------------------------------------------------------------------
        # 5. GENERATE INTERACTIVE VISUAL EXPLORER (ontology_graph.html)
        # ---------------------------------------------------------------------
        self.export_visual_graph(nodes, edges, HTML_OUTPUT_PATH)

        return {
            "status": "success",
            "nodes_count": len(nodes),
            "edges_count": len(edges),
            "html_path": str(HTML_OUTPUT_PATH),
            "graph_engine": ge.__class__.__name__
        }

    # =========================================================================
    # 4. DYNAMIC STATE MUTATIONS & CONTEXT FRESHNESS (Solving Context Decay)
    # =========================================================================

    def _upsert_node_embedding(self, node_id: str, node_type: str, dense_summary: str) -> None:
        """
        Targeted O(1) embedding update for a single node after mutation.
        Only the changed node's vector is updated in LanceDB — not a full rebuild.
        Fires in background so mutation response is not blocked.
        """
        async def _guarded():
            try:
                from app.ontology.vector_store import upsert_single_node
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, upsert_single_node, node_id, node_type, dense_summary)
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        asyncio.ensure_future(_guarded())

    async def sync_full_pipeline(self) -> Dict[str, Any]:
        """
        Runs the complete Knowledge Graph pipeline end-to-end:
        1. Structural sync to Kùzu (graph topology)
        2. Semantic embedding of the operational twin into LanceDB (solving Context Decay)

        Call this on server startup or after bulk data loads.
        """
        from app.ontology.kb_ingestion import ingest_operational_twin_contexts

        graph_sync = await self.sync_to_cognee()
        embed_sync = await ingest_operational_twin_contexts(self.builder)

        return {
            "status": "success",
            "graph_sync": graph_sync,
            "semantic_sync": embed_sync,
            "pipeline_complete": True,
        }

    async def semantic_query_ontology(self, query: str, search_type: str = "SUMMARIES", top_k: int = 5) -> Dict[str, Any]:
        """
        Runs a semantic search against the SMCH Knowledge Graph using
        fastembed BAAI/bge-small-en-v1.5 embeddings via direct LanceDB (operational twin)
        then enriches results with live operational context.
        """
        from app.ontology.semantic_search import multi_context_search
        return await multi_context_search(query, top_k=top_k)

    async def update_bed_status(self, bed_id: str, new_status: str, patient_uhid: Optional[str] = None) -> Dict[str, Any]:
        """
        Mutates bed lifecycle state (occupied -> dirty -> sanitized -> vacant)
        and synchronizes to Cognee immediately, eliminating stale occupancy context.
        """
        self.builder.update_bed_status(bed_id, new_status, patient_uhid)
        res = await self.sync_to_cognee()
        bed = self.builder.beds.get(bed_id)
        if bed and getattr(bed, "dense_summary", None):
            self._upsert_node_embedding(bed_id, "BedNode", bed.dense_summary)
        return {
            "status": "success",
            "bed_id": bed_id,
            "new_status": new_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "graph_sync": res
        }

    async def resolve_panic_lab_alert(self, alert_id: str, doctor_id: str) -> Dict[str, Any]:
        """
        Documents verbal readback confirmation under POL-010.
        Clears the active countdown SLA and removes the panic blocker edge from Cognee.
        """
        self.builder.resolve_panic_lab_alert(alert_id, doctor_id)
        res = await self.sync_to_cognee()
        alert = self.builder.lab_critical_alerts.get(alert_id)
        if alert and getattr(alert, "dense_summary", None):
            self._upsert_node_embedding(alert_id, "LabPanicAlertNode", alert.dense_summary)
        return {
            "status": "success",
            "alert_id": alert_id,
            "readback_status": "Acknowledged",
            "doctor": doctor_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "graph_sync": res
        }

    async def settle_discharge_billing(self, discharge_id: str) -> Dict[str, Any]:
        """
        Flips central billing clearance flag to True, resolving unbilled consumable
        charges and releasing gate pass blockers in the Cognee ontology.
        """
        self.builder.settle_discharge_billing(discharge_id)
        res = await self.sync_to_cognee()
        dis = self.builder.discharges.get(discharge_id)
        if dis and getattr(dis, "dense_summary", None):
            self._upsert_node_embedding(discharge_id, "DischargeNode", dis.dense_summary)
        for bill_id, bill in self.builder.bills.items():
            if bill.uhid == (dis.uhid if dis else None) and getattr(bill, "dense_summary", None):
                self._upsert_node_embedding(bill_id, "BillNode", bill.dense_summary)
                break
        return {
            "status": "success",
            "discharge_id": discharge_id,
            "clearance_billing": True,
            "is_blocked": dis.is_blocked if dis else False,
            "status_str": dis.status if dis else "ready_for_gate_pass",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "graph_sync": res
        }

    async def settle_discharge_pharmacy(self, discharge_id: str) -> Dict[str, Any]:
        """
        Flips pharmacy medication return clearance flag to True in the Cognee ontology.
        """
        self.builder.settle_discharge_pharmacy(discharge_id)
        res = await self.sync_to_cognee()
        dis = self.builder.discharges.get(discharge_id)
        if dis and getattr(dis, "dense_summary", None):
            self._upsert_node_embedding(discharge_id, "DischargeNode", dis.dense_summary)
        return {
            "status": "success",
            "discharge_id": discharge_id,
            "clearance_pharmacy": True,
            "is_blocked": dis.is_blocked if dis else False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "graph_sync": res
        }

    async def update_claim_status(self, claim_id: str, new_status: str, approved_amount: Optional[float] = None) -> Dict[str, Any]:
        """
        Updates cashless insurance claim status (preauth approved) in the Cognee ontology.
        """
        self.builder.update_claim_status(claim_id, new_status, approved_amount)
        res = await self.sync_to_cognee()
        claim = self.builder.claims.get(claim_id)
        if claim and getattr(claim, "dense_summary", None):
            self._upsert_node_embedding(claim_id, "ClaimNode", claim.dense_summary)
        return {
            "status": "success",
            "claim_id": claim_id,
            "new_status": new_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "graph_sync": res
        }

    async def prune_stale_contexts(self) -> Dict[str, Any]:
        """
        Cleanses transient and expired operational flags so downstream agents
        never experience Context Decay.
        """
        self.builder.prune_stale_contexts()
        res = await self.sync_to_cognee()
        return {
            "status": "success",
            "pruned_at": datetime.now(timezone.utc).isoformat(),
            "active_nodes": res["nodes_count"],
            "active_edges": res["edges_count"]
        }

    # =========================================================================
    # 5. SEMANTIC GRAPH QUERY & TRAVERSAL ENGINE
    # =========================================================================

    def query_patient_operational_graph(self, uhid: str) -> Dict[str, Any]:
        """
        Retrieves the 360-degree stitched operational digital twin for a patient:
        Bed location, active admission, discharge blockers, lab results, panic alerts,
        prescriptions, dispensing logs, billing invoices, cashless claims, and governing SOPs.
        """
        pat = self.builder.patients.get(uhid)
        if not pat:
            return {"status": "not_found", "message": f"Patient {uhid} not found in operational twin."}

        # Spatial Allocation
        bed = self.builder.beds.get(pat.current_bed_id) if pat.current_bed_id else None

        # Encounter
        adm = self.builder.admissions.get(pat.active_admission_id) if pat.active_admission_id else None

        # Discharge Status & Blocker
        dis = next((d for d in self.builder.discharges.values() if d.uhid == uhid), None)

        # Revenue & Bills
        bills = [b for b in self.builder.bills.values() if b.uhid == uhid]
        claims = [c for c in self.builder.claims.values() if c.uhid == uhid]

        # Labs & Panic Alerts
        panic_alerts = [a for a in self.builder.lab_critical_alerts.values() if a.uhid == uhid]
        labs = [l for l in self.builder.lab_results.values() if l.uhid == uhid]

        # Pharmacy
        prescriptions = [p for p in self.builder.prescriptions.values() if p.uhid == uhid]
        dispenses = [d for d in self.builder.dispensing_logs.values() if d.uhid == uhid]

        # Radiology
        radiology = [r for r in self.builder.radiology_reports.values() if r.uhid == uhid]

        # Governing SOP
        sop = next((s for k, s in self.builder.sops.items() if "DIS-001" in k or "DISCHARGE" in k.upper()), None)

        return {
            "status": "found",
            "patient": {
                "uhid": pat.uhid,
                "name": pat.name,
                "age": pat.age,
                "gender": pat.gender,
                "contact": pat.contact,
                "status": pat.status
            },
            "spatial_allocation": {
                "bed_id": bed.bed_id if bed else "Unassigned / OPD",
                "ward": bed.ward if bed else "OPD",
                "bed_status": bed.status if bed else "N/A"
            },
            "admission": {
                "admission_id": adm.admission_id if adm else None,
                "admitting_doctor": adm.admitting_doctor_id if adm else None,
                "diagnosis": adm.admitting_diagnosis if adm else None,
                "admission_date": adm.admission_date if adm else None
            },
            "discharge_tracking": {
                "discharge_id": dis.discharge_id if dis else None,
                "is_blocked": dis.is_blocked if dis else False,
                "status": dis.status if dis else "normal",
                "clearance_clinical": dis.clearance_clinical if dis else True,
                "clearance_pharmacy": dis.clearance_pharmacy if dis else True,
                "clearance_billing": dis.clearance_billing if dis else True,
                "clearance_nursing": dis.clearance_nursing if dis else True,
                "blocker_reason": dis.blocker_reason if dis else None,
                "escalation_rule": dis.escalation_rule_id if dis else None,
                "resolution_team_extension": dis.resolution_team_extension if dis else None,
                "governing_sop": sop.title if sop else "SOP-DIS-001 Inpatient Discharge Protocol"
            },
            "revenue_cycle": {
                "bills_count": len(bills),
                "total_incurred": sum(b.total_amount for b in bills),
                "total_pending": sum(b.pending_amount for b in bills),
                "unbilled_consumables": sum(b.unbilled_consumables for b in bills),
                "has_dispute": any(b.has_billing_dispute for b in bills),
                "claims": [{"claim_id": c.claim_id, "scheme": c.insurer, "status": c.status, "rejection_reason": c.rejection_reason} for c in claims]
            },
            "diagnostics": {
                "panic_alerts": [{"alert_id": a.alert_id, "parameter": a.parameter_name, "value": a.critical_value, "readback_status": a.readback_status, "sla_breached": a.is_sla_breached} for a in panic_alerts],
                "lab_results_count": len(labs),
                "radiology_reports": [{"report_id": r.report_id, "modality": r.modality, "critical": r.is_critical_finding} for r in radiology]
            },
            "pharmacy": {
                "prescriptions_count": len(prescriptions),
                "dispensed_count": len(dispenses)
            }
        }

    def query_cross_departmental_bottlenecks(self) -> Dict[str, Any]:
        """
        Computes real-time cross-departmental bottlenecks across the entire hospital:
        1. Discharges blocked by billing settlement (with outstanding amounts & escalation desk ext).
        2. Discharges blocked by pending pharmacy medication return credits.
        3. Critical panic lab values pending verbal readback with 15-min SLA countdown timer under POL-010.
        4. TPA cashless claims rejected or query-raised with denial reasons under R-004.
        """
        # 1. Blocked Discharges
        billing_blocked = []
        pharmacy_blocked = []
        for d in self.builder.discharges.values():
            if d.is_blocked:
                item = {
                    "discharge_id": d.discharge_id,
                    "admission_id": d.admission_id,
                    "uhid": d.uhid,
                    "bed_id": d.bed_id,
                    "blocker_reason": d.blocker_reason,
                    "escalation_rule": d.escalation_rule_id,
                    "resolution_extension": d.resolution_team_extension
                }
                if not d.clearance_billing:
                    billing_blocked.append(item)
                elif not d.clearance_pharmacy:
                    pharmacy_blocked.append(item)

        # 2. Critical Panic Lab Alerts (POL-010)
        active_panics = []
        for a in self.builder.lab_critical_alerts.values():
            if a.readback_status != "Acknowledged":
                active_panics.append({
                    "alert_id": a.alert_id,
                    "uhid": a.uhid,
                    "patient_name": a.patient_name,
                    "parameter": a.parameter_name,
                    "critical_value": a.critical_value,
                    "doctor_contacted": a.doctor_contacted,
                    "doctor_phone": a.doctor_phone,
                    "elapsed_minutes": a.elapsed_minutes,
                    "sla_limit_minutes": a.sla_minutes,
                    "is_sla_breached": a.is_sla_breached,
                    "mandatory_policy": "POL-010 Critical Value 15-Minute Readback Mandate",
                    "escalation_rule": "R-009"
                })

        # 3. Cashless Claim Denials (R-004)
        rejected_claims = []
        for c in self.builder.claims.values():
            if c.requires_dispute_appeal or c.status == "rejected":
                rejected_claims.append({
                    "claim_id": c.claim_id,
                    "uhid": c.uhid,
                    "scheme": c.insurer,
                    "claimed_amount": c.claim_amount,
                    "denial_reason": c.rejection_reason,
                    "rejection_clause": c.rejection_clause,
                    "escalation_rule": "R-004 TPA Denial & Shortfall Appeal Route"
                })

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_blocked_discharges": len(billing_blocked) + len(pharmacy_blocked),
                "billing_blocked_count": len(billing_blocked),
                "pharmacy_blocked_count": len(pharmacy_blocked),
                "active_panic_alerts_count": len(active_panics),
                "sla_breached_alerts_count": sum(1 for p in active_panics if p["is_sla_breached"]),
                "rejected_claims_count": len(rejected_claims)
            },
            "bottlenecks": {
                "discharges_blocked_by_billing": billing_blocked,
                "discharges_blocked_by_pharmacy": pharmacy_blocked,
                "critical_panic_lab_alerts": active_panics,
                "tpa_cashless_denials": rejected_claims
            }
        }

    def query_bed_states_and_turnaround(self, ward: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates real-time ward & ICU bed capacity, occupancy %, dirty turnaround queue,
        and turnaround timestamps.
        """
        all_beds = list(self.builder.beds.values())
        if ward:
            all_beds = [b for b in all_beds if ward.lower() in b.ward.lower()]

        total = len(all_beds)
        occupied = sum(1 for b in all_beds if b.status == "occupied")
        vacant = sum(1 for b in all_beds if b.status == "vacant")
        dirty = sum(1 for b in all_beds if b.status == "dirty")
        sanitized = sum(1 for b in all_beds if b.status == "sanitized")
        occ_rate = round((occupied / total * 100), 1) if total > 0 else 0.0

        return {
            "ward_filter": ward or "All Hospital Wards",
            "total_beds": total,
            "occupied_beds": occupied,
            "vacant_beds": vacant,
            "dirty_turnaround_queue": dirty,
            "sanitized_ready_beds": sanitized,
            "occupancy_rate_pct": occ_rate,
            "turnaround_sla_breached_count": dirty  # Beds waiting for housekeeping
        }

    def query_revenue_risks_and_tpa_denials(self) -> Dict[str, Any]:
        """
        Calculates total financial leakage, disputed billing balances, unbilled consumables,
        and cashless pre-auth rejections.
        """
        claims = list(self.builder.claims.values())
        bills = list(self.builder.bills.values())

        rej_claims = [c for c in claims if c.status == "rejected" or c.requires_dispute_appeal]
        total_rej_amt = sum(c.claim_amount for c in rej_claims)

        disp_bills = [b for b in bills if b.has_billing_dispute]
        total_disp_amt = sum(b.dispute_amount for b in disp_bills)
        total_unbilled = sum(b.unbilled_consumables for b in bills)

        return {
            "total_revenue_at_risk_inr": total_rej_amt + total_disp_amt + total_unbilled,
            "cashless_claim_denials": {
                "count": len(rej_claims),
                "total_denied_amount_inr": total_rej_amt,
                "denials": [{"claim_id": c.claim_id, "uhid": c.uhid, "scheme": c.insurer, "amount": c.claim_amount, "reason": c.rejection_reason} for c in rej_claims]
            },
            "billing_disputes": {
                "count": len(disp_bills),
                "total_disputed_amount_inr": total_disp_amt,
                "total_unbilled_consumables_inr": total_unbilled
            }
        }

    def query_governance_rules_for_state(self, entity_or_workflow_id: str) -> Dict[str, Any]:
        """
        Retrieves the exact SOPs, institutional policies, required fields, and approval
        checkpoints governing an operational workflow or action.
        """
        wf = self.builder.workflows.get(entity_or_workflow_id)
        steps = [s for s in self.builder.workflow_steps.values() if s.workflow_id == entity_or_workflow_id]

        # Match relevant SOPs and policies
        sops = [s for s in self.builder.sops.values() if entity_or_workflow_id.lower() in s.doc_id.lower() or (wf and wf.name.lower() in s.title.lower())]
        policies = [p for p in self.builder.policies.values() if entity_or_workflow_id.lower() in p.doc_id.lower() or (wf and wf.department.lower() in p.department.lower())]

        return {
            "entity_or_workflow": entity_or_workflow_id,
            "workflow": {
                "name": wf.name if wf else "Operational Procedure",
                "department": wf.department if wf else "Hospital Operations",
                "requires_human_approval": wf.requires_human_approval if wf else True,
                "approval_checkpoint": wf.approval_checkpoint if wf else "Final Step"
            },
            "steps": [{"step_number": s.step_number, "name": s.step_name, "actor": s.actor_role, "required_fields": s.required_fields, "blockers": s.blockers} for s in steps],
            "governing_sops": [{"doc_id": s.doc_id, "title": s.title, "citation": s.citation} for s in sops[:3]],
            "institutional_policies": [{"doc_id": p.doc_id, "title": p.title, "mandate": p.mandate} for p in policies[:3]]
        }

    # =========================================================================
    # 6. PALANTIR MULTI-PERSPECTIVE OPERATIONAL SUBGRAPHS & VISUAL EXPLORER
    # =========================================================================

    def format_vis_node(self, n: Any) -> Dict[str, Any]:
        """Formats an ontology entity into a sleek, executive Palantir Foundry card node."""
        n_type = getattr(n, "type", n.__class__.__name__)
        n_id = str(getattr(n, "id", ""))

        color = {
            "background": "#0F172A",
            "border": "#334155",
            "highlight": {"background": "#1E293B", "border": "#64748B"}
        }
        group = "Other"
        label = n_type
        font_color = "#F8FAFC"

        if n_type == "DischargeNode":
            is_blk = getattr(n, "is_blocked", False)
            d_id = getattr(n, "discharge_id", "")
            uhid = getattr(n, "uhid", "")
            if is_blk:
                color = {
                    "background": "#1F0F16",
                    "border": "#F43F5E",
                    "highlight": {"background": "#2F1522", "border": "#FDA4AF"}
                }
                label = f"DISCHARGE HOLD · SLA\n{d_id}\nPatient: {uhid} · Hold"
                font_color = "#FFF1F2"
                group = "Incidents"
            else:
                color = {
                    "background": "#0A1D16",
                    "border": "#10B981",
                    "highlight": {"background": "#0F2E23", "border": "#34D399"}
                }
                label = f"GATE PASS READY\n{d_id}\nFinancially Cleared"
                font_color = "#ECFDF5"
                group = "Operational"

        elif n_type == "LabPanicAlertNode":
            stat = getattr(n, "readback_status", "Pending-Ack")
            param = getattr(n, "parameter_name", "Lab")
            val = getattr(n, "critical_value", "")
            is_breach = getattr(n, "is_sla_breached", False)
            if stat != "Acknowledged":
                color = {
                    "background": "#240E14",
                    "border": "#FB7185",
                    "highlight": {"background": "#38151E", "border": "#FECDD3"}
                }
                label = f"CRITICAL LAB VALUE\n{param}: {val}\n{'15m Verbal SLA Breached' if is_breach else '15m SLA Countdown'}"
                font_color = "#FFF1F2"
                group = "Incidents"
            else:
                color = {
                    "background": "#0A1D16",
                    "border": "#10B981",
                    "highlight": {"background": "#0F2E23", "border": "#34D399"}
                }
                label = f"READBACK ACKNOWLEDGED\n{param}: {val}\nDoctor Contacted · Cleared"
                font_color = "#ECFDF5"
                group = "Operational"

        elif n_type == "BillNode":
            has_disp = getattr(n, "has_billing_dispute", False)
            unbilled = getattr(n, "unbilled_consumables", 0)
            b_id = getattr(n, "bill_id", "")
            if has_disp or unbilled > 0:
                color = {
                    "background": "#24130A",
                    "border": "#F97316",
                    "highlight": {"background": "#361D0F", "border": "#FDBA74"}
                }
                label = f"UNSETTLED INVOICE\n{b_id}\nUnbilled: ₹{unbilled:,.0f} Consumables"
                font_color = "#FFF7ED"
                group = "Financial"
            else:
                color = {
                    "background": "#0A1D16",
                    "border": "#10B981",
                    "highlight": {"background": "#0F2E23", "border": "#34D399"}
                }
                label = f"BILL SETTLED\n{b_id}\nPaid in Full"
                font_color = "#ECFDF5"
                group = "Financial"

        elif n_type == "ClaimNode":
            is_rej = getattr(n, "status", "") == "rejected" or getattr(n, "requires_dispute_appeal", False)
            c_id = getattr(n, "claim_id", "")
            amt = getattr(n, "claim_amount", 0)
            ins = getattr(n, "insurer", "Insurer")
            if is_rej:
                color = {
                    "background": "#241408",
                    "border": "#F59E0B",
                    "highlight": {"background": "#381E0C", "border": "#FCD34D"}
                }
                label = f"TPA CLAIM DENIED\n{c_id} · ₹{amt:,.0f}\n{ins} · Appeal Req."
                font_color = "#FFFBEB"
                group = "Financial"
            else:
                color = {
                    "background": "#0B1A2E",
                    "border": "#3B82F6",
                    "highlight": {"background": "#122A4A", "border": "#93C5FD"}
                }
                label = f"CLAIM APPROVED\n{c_id} · ₹{amt:,.0f}\n{ins} · Pre-Auth Valid"
                font_color = "#EFF6FF"
                group = "Financial"

        elif n_type == "PatientNode":
            name = getattr(n, "name", "Patient")
            uhid = getattr(n, "uhid", "")
            age = getattr(n, "age", "")
            gen = getattr(n, "gender", "")
            color = {
                "background": "#0A192A",
                "border": "#0EA5E9",
                "highlight": {"background": "#112942", "border": "#38BDF8"}
            }
            label = f"PATIENT TWIN · INPATIENT\n{name} ({age}y/{gen})\nUHID: {uhid}"
            font_color = "#F0F9FF"
            group = "Patients"

        elif n_type == "BedNode":
            bid = getattr(n, "bed_id", "")
            wrd = getattr(n, "ward", "Ward")
            stat = getattr(n, "status", "vacant").lower()
            if stat == "occupied":
                color = {
                    "background": "#14142B",
                    "border": "#818CF8",
                    "highlight": {"background": "#1E1F42", "border": "#A5B4FC"}
                }
                label = f"BED {bid} · {wrd}\nOccupied\nInpatient Admission"
                font_color = "#EEF2FF"
            elif stat == "dirty":
                color = {
                    "background": "#241608",
                    "border": "#F59E0B",
                    "highlight": {"background": "#38230D", "border": "#FCD34D"}
                }
                label = f"BED {bid} · {wrd}\nDirty (Housekeeping Queue)\nTurnaround Pending"
                font_color = "#FFFBEB"
            elif stat == "sanitized":
                color = {
                    "background": "#081E24",
                    "border": "#06B6D4",
                    "highlight": {"background": "#0E2E38", "border": "#67E8F9"}
                }
                label = f"BED {bid} · {wrd}\nSanitized & Cleared\nReady for Admission"
                font_color = "#ECFEFF"
            else:
                color = {
                    "background": "#0A1D16",
                    "border": "#10B981",
                    "highlight": {"background": "#0F2E23", "border": "#34D399"}
                }
                label = f"BED {bid} · {wrd}\nVacant\nReady for Allocation"
                font_color = "#ECFDF5"
            group = "Beds"

        elif n_type == "AdmissionNode":
            aid = getattr(n, "admission_id", "")
            dx = getattr(n, "admitting_diagnosis", "")[:24]
            color = {
                "background": "#082020",
                "border": "#14B8A6",
                "highlight": {"background": "#0E3030", "border": "#2DD4BF"}
            }
            label = f"INPATIENT ADMISSION\n{aid}\nDx: {dx}"
            font_color = "#F0FDFA"
            group = "Admissions"

        elif n_type == "StaffNode":
            name = getattr(n, "name", "Doctor")
            role = getattr(n, "role", "Clinician")
            dept = getattr(n, "department_id", "General")
            color = {
                "background": "#0A1B30",
                "border": "#38BDF8",
                "highlight": {"background": "#102B4C", "border": "#7DD3FC"}
            }
            label = f"TREATING CLINICIAN\n{name}\n{role} · Dept: {dept}"
            font_color = "#F0F9FF"
            group = "Staff"

        elif n_type == "SOPNode":
            doc = getattr(n, "doc_id", "SOP")
            title = getattr(n, "title", "Procedure")[:26]
            color = {
                "background": "#14132B",
                "border": "#6366F1",
                "highlight": {"background": "#1F1D42", "border": "#818CF8"}
            }
            label = f"GOVERNANCE SOP\n{doc}\n{title}"
            font_color = "#EEF2FF"
            group = "Governance"

        elif n_type == "PolicyNode":
            doc = getattr(n, "doc_id", "POL")
            title = getattr(n, "title", "Policy")[:26]
            color = {
                "background": "#19122D",
                "border": "#8B5CF6",
                "highlight": {"background": "#261A45", "border": "#A78BFA"}
            }
            label = f"INSTITUTIONAL POLICY\n{doc}\n{title}"
            font_color = "#F5F3FF"
            group = "Governance"

        elif n_type == "RoutingRuleNode":
            rid = getattr(n, "rule_id", "Rule")
            route = getattr(n, "route_to_team", "Team")
            color = {
                "background": "#20112E",
                "border": "#A855F7",
                "highlight": {"background": "#301A45", "border": "#C084FC"}
            }
            label = f"ESCALATION RULE\n{rid}\nDispatches to: {route}"
            font_color = "#FAF5FF"
            group = "Governance"

        elif n_type == "SupportTeamNode":
            name = getattr(n, "name", "Team")
            ext = getattr(n, "contact_extension", "1000")
            color = {
                "background": "#250F29",
                "border": "#D946EF",
                "highlight": {"background": "#38173E", "border": "#E879F9"}
            }
            label = f"DISPATCH TEAM\n{name}\nInternal Ext: {ext}"
            font_color = "#FDF4FF"
            group = "Governance"

        elif n_type == "DepartmentNode":
            name = getattr(n, "name", "Department")
            color = {
                "background": "#121A28",
                "border": "#64748B",
                "highlight": {"background": "#1D283D", "border": "#94A3B8"}
            }
            label = f"HOSPITAL DEPARTMENT\n{name}\nClinical Specialty"
            font_color = "#F1F5F9"
            group = "Departments"

        elif n_type == "WorkflowNode":
            name = getattr(n, "name", "Workflow")
            wid = getattr(n, "workflow_id", "WF")
            color = {
                "background": "#15132E",
                "border": "#4F46E5",
                "highlight": {"background": "#211E48", "border": "#6366F1"}
            }
            label = f"CLINICAL WORKFLOW\n{wid}: {name}\nStandard Pathway"
            font_color = "#EEF2FF"
            group = "Governance"

        elif n_type == "PrescriptionNode":
            iid = getattr(n, "intake_id", "Rx")
            color = {
                "background": "#221308",
                "border": "#F59E0B",
                "highlight": {"background": "#361E0C", "border": "#FBBF24"}
            }
            label = f"MEDICATION INDENT\n{iid}\nWard Medication Order"
            font_color = "#FFFBEB"
            group = "Pharmacy"

        props = {}
        for k, v in n.__dict__.items():
            if not k.startswith("_") and k not in ["metadata"]:
                props[k] = str(v) if isinstance(v, (datetime, uuid.UUID)) else v

        return {
            "id": n_id,
            "label": label,
            "color": color,
            "shape": "box",
            "shapeProperties": {"borderRadius": 7},
            "margin": {"top": 9, "bottom": 9, "left": 13, "right": 13},
            "borderWidth": 1.5,
            "borderWidthSelected": 2.5,
            "font": {
                "color": font_color,
                "size": 11,
                "face": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
            },
            "shadow": {
                "enabled": True,
                "color": "rgba(0, 0, 0, 0.6)",
                "size": 10,
                "x": 0,
                "y": 4
            },
            "title": f"<b>{label.replace(chr(10), '<br>')}</b><br>Type: {n_type}<br>{getattr(n, 'dense_summary', '')}",
            "group": group,
            "type": n_type,
            "summary": getattr(n, "dense_summary", ""),
            "properties": props
        }

    def format_vis_edge(self, src: str, tgt: str, rel: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Formats an edge with high contrast and explicit status colors."""
        lbl = data.get("label", rel)
        is_blocked = "BLOCKED" in rel or "PANIC" in rel or "DENIED" in rel or "Hold" in lbl or "dispute" in lbl.lower()
        is_cleared = "CLEARED" in rel or "ACK" in rel or "APPROVED" in rel or "VACANT" in rel or "Satisfied" in lbl

        if is_blocked:
            color = {"color": "#F43F5E", "highlight": "#FDA4AF", "opacity": 0.95}
            width = 2.4
        elif is_cleared:
            color = {"color": "#10B981", "highlight": "#34D399", "opacity": 0.9}
            width = 2.0
        else:
            color = {"color": "#334155", "highlight": "#64748B", "opacity": 0.8}
            width = 1.4

        clean_lbl = lbl.replace("🚨 ", "").replace("✅ ", "").replace("⚠️ ", "").strip()

        return {
            "from": src,
            "to": tgt,
            "label": clean_lbl,
            "arrows": {
                "to": {
                    "enabled": True,
                    "scaleFactor": 0.65,
                    "type": "arrow"
                }
            },
            "color": color,
            "width": width,
            "font": {
                "color": "#94A3B8",
                "size": 9,
                "face": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                "strokeWidth": 0,
                "background": "#0B111E",
                "align": "horizontal"
            },
            "smooth": {
                "type": "cubicBezier",
                "forceDirection": "none",
                "roundness": 0.18
            },
            "title": f"Relationship: {rel}"
        }

    def get_perspective_subgraph(
        self,
        perspective: str = "bottlenecks",
        uhid: Optional[str] = None,
        ward: Optional[str] = None,
        filter_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extracts a clean, presentable, perspective-based subgraph from the ontology,
        completely eliminating the unreadable hairball anti-pattern.
        """
        nodes_map: Dict[str, Any] = {}
        raw_edges: List[Tuple[str, str, str, Dict[str, Any]]] = []

        def add_node(n):
            if n:
                if not hasattr(n, "id") or not n.id:
                    n_type = getattr(n, "type", n.__class__.__name__).lower()
                    n.id = make_smch_uuid(n_type, getattr(n, "uhid", getattr(n, "bed_id", getattr(n, "discharge_id", str(id(n))))))
                nodes_map[str(n.id)] = n

        def add_edge(src_n, tgt_n, rel, data):
            if src_n and tgt_n:
                add_node(src_n)
                add_node(tgt_n)
                raw_edges.append((str(src_n.id), str(tgt_n.id), rel, data))

        # ---------------------------------------------------------------------
        # 1. OPERATIONAL BOTTLENECKS RADAR (SHOWCASE PERSPECTIVE)
        # ---------------------------------------------------------------------
        if perspective == "bottlenecks":
            target_discharges = [
                d for d in self.builder.discharges.values()
                if d.is_blocked or d.discharge_id in ["DIS-ADM-42C854", "DIS-ADM-14E565", "DIS-ADM-3F3465"]
            ]

            sop_dis = next((s for k, s in self.builder.sops.items() if "DIS-001" in k or "DISCHARGE" in k.upper()), None)

            for d in target_discharges:
                add_node(d)
                pat = self.builder.patients.get(d.uhid)
                adm = self.builder.admissions.get(d.admission_id)
                if adm:
                    add_node(adm)
                    add_edge(adm, d, "HAS_DISCHARGE_ORDER", {"label": "Discharge Order"})
                    if pat:
                        add_edge(pat, adm, "HAS_ADMISSION", {"label": "Inpatient Admission"})
                    if adm.bed_id and adm.bed_id in self.builder.beds:
                        bed = self.builder.beds[adm.bed_id]
                        add_edge(adm, bed, "ASSIGNED_BED", {"label": "Assigned Bed"})
                        if pat:
                            add_edge(pat, bed, "OCCUPIES", {"label": "Occupies Bed"})
                    if adm.admitting_doctor_id and adm.admitting_doctor_id in self.builder.staff:
                        doc = self.builder.staff[adm.admitting_doctor_id]
                        add_edge(adm, doc, "ATTENDED_BY", {"label": "Treating Doctor"})

                # Incurred Bill & Consumables
                bill = next((bi for bi in self.builder.bills.values() if bi.uhid == d.uhid), None)
                if bill:
                    if d.is_blocked and not d.clearance_billing:
                        add_edge(d, bill, "BLOCKED_BY_SETTLEMENT", {"label": "🚨 Blocked by Unsettled Bill"})
                    else:
                        add_edge(d, bill, "FINANCIALLY_CLEARED", {"label": "✅ Financially Cleared"})

                # Governing SOP
                if sop_dis:
                    lbl = "🚨 Governed by SOP-DIS-001" if d.is_blocked else "✅ SOP Clearance Satisfied"
                    add_edge(d, sop_dis, "GOVERNED_BY_SOP", {"label": lbl})

                # Escalation Rule & Team
                rule_id = d.escalation_rule_id or ("R-008" if not d.clearance_billing else "R-002")
                if rule_id in self.builder.routing_rules:
                    rule = self.builder.routing_rules[rule_id]
                    add_edge(d, rule, "ESCALATES_TO_RULE", {"label": f"🚨 Rule {rule.rule_id} Hold"})
                    team = next((t for t in self.builder.support_teams.values() if rule.route_to_team.lower() in t.name.lower() or t.name.lower() in rule.route_to_team.lower()), None)
                    if team:
                        add_edge(rule, team, "DISPATCHES_TO_TEAM", {"label": f"Dispatches to {team.name} (Ext {team.contact_extension})"})

            # Critical Panic Lab Alerts (POL-010 15m SLA)
            target_panics = [
                a for a in self.builder.lab_critical_alerts.values()
                if a.alert_id in ["CRIT-ALRT-A0CCE", "CRIT-ALRT-842BB"] or a.readback_status != "Acknowledged"
            ][:2]
            pol_panic = next((p for k, p in self.builder.policies.items() if "POL-010" in k or "PANIC" in k.upper()), None)
            rule_panic = self.builder.routing_rules.get("R-009")

            for al in target_panics:
                add_node(al)
                pat = self.builder.patients.get(al.uhid)
                if pat:
                    add_edge(pat, al, "TRIGGERS_PANIC_ALERT", {"label": f"🚨 Critical {al.parameter_name}"})

                doc = next((s for s in self.builder.staff.values() if (al.doctor_contacted and al.doctor_contacted in s.name) or "Venkatraman" in s.name or "Cardio" in s.role), None)
                if doc:
                    add_edge(al, doc, "ALERTS_PHYSICIAN", {"label": "Physician Paged"})

                if pol_panic:
                    lbl = "🚨 POL-010 15-Min SLA" if al.readback_status != "Acknowledged" else "✅ Readback Documented"
                    add_edge(al, pol_panic, "MANDATED_BY_POLICY", {"label": lbl})

                if rule_panic and al.readback_status != "Acknowledged":
                    add_edge(al, rule_panic, "PAGES_CONSULTANT_VIA", {"label": "🚨 Emergency Page R-009"})
                    team = next((t for t in self.builder.support_teams.values() if "Cardio" in t.name or "Emergency" in t.name or "Review" in t.name), None)
                    if team:
                        add_edge(rule_panic, team, "DISPATCHES_TO_TEAM", {"label": f"Dispatches to {team.name}"})

            # Cashless Claim Rejection (R-004)
            demo_claim = next((c for c in self.builder.claims.values() if c.status == "rejected" or c.requires_dispute_appeal), None)
            if demo_claim:
                add_node(demo_claim)
                pat = self.builder.patients.get(demo_claim.uhid)
                if pat:
                    add_edge(pat, demo_claim, "HAS_CLAIM", {"label": "Cashless Claim"})
                rule_tpa = self.builder.routing_rules.get("R-004")
                if rule_tpa:
                    add_edge(demo_claim, rule_tpa, "REJECTION_ESCALATED_VIA", {"label": "⚠️ TPA Rejection Appeal Route"})
                    team_tpa = next((t for t in self.builder.support_teams.values() if "TPA" in t.name or "Insurance" in t.name), None)
                    if team_tpa:
                        add_edge(rule_tpa, team_tpa, "DISPATCHES_TO_TEAM", {"label": f"Dispatches to {team_tpa.name} (Ext {team_tpa.contact_extension})"})

        # ---------------------------------------------------------------------
        # 2. PATIENT 360 DIGITAL TWIN PERSPECTIVE
        # ---------------------------------------------------------------------
        elif perspective == "patient_360":
            target_uhid = uhid or "SMCH-278037"
            pat = self.builder.patients.get(target_uhid)
            if not pat:
                target_uhid = next(iter(self.builder.patients), "SMCH-857250")
                pat = self.builder.patients.get(target_uhid)

            if pat:
                add_node(pat)
                # Bed
                if pat.current_bed_id and pat.current_bed_id in self.builder.beds:
                    bed = self.builder.beds[pat.current_bed_id]
                    add_edge(pat, bed, "OCCUPIES", {"label": "Occupies Bed"})
                # Admission
                if pat.active_admission_id and pat.active_admission_id in self.builder.admissions:
                    adm = self.builder.admissions[pat.active_admission_id]
                    add_edge(pat, adm, "HAS_ADMISSION", {"label": "Inpatient Admission"})
                    if adm.admitting_doctor_id and adm.admitting_doctor_id in self.builder.staff:
                        doc = self.builder.staff[adm.admitting_doctor_id]
                        add_edge(adm, doc, "ATTENDED_BY", {"label": "Treating Doctor"})
                # Discharge
                dis = next((d for d in self.builder.discharges.values() if d.uhid == target_uhid), None)
                if dis:
                    add_edge(pat, dis, "HAS_DISCHARGE_ORDER", {"label": "Discharge Order"})
                    sop = next((s for k, s in self.builder.sops.items() if "DIS-001" in k), None)
                    if sop:
                        add_edge(dis, sop, "GOVERNED_BY_SOP", {"label": "Governed by SOP-DIS-001"})
                # Bills
                bills = [b for b in self.builder.bills.values() if b.uhid == target_uhid]
                for b in bills:
                    add_edge(pat, b, "INCURRED_BILL", {"label": "Incurred Bill"})
                    if dis:
                        rel_label = "🚨 Blocked by Bill" if dis.is_blocked and not dis.clearance_billing else "✅ Financially Cleared"
                        add_edge(dis, b, "SETTLEMENT_STATUS", {"label": rel_label})
                # Claims
                claims = [c for c in self.builder.claims.values() if c.uhid == target_uhid]
                for c in claims:
                    add_edge(pat, c, "HAS_CLAIM", {"label": "Cashless Claim"})
                # Panic Alerts
                alerts = [a for a in self.builder.lab_critical_alerts.values() if a.uhid == target_uhid]
                pol_panic = next((p for k, p in self.builder.policies.items() if "POL-010" in k), None)
                for a in alerts:
                    add_edge(pat, a, "TRIGGERS_PANIC_ALERT", {"label": f"🚨 Critical {a.parameter_name}"})
                    if pol_panic:
                        add_edge(a, pol_panic, "MANDATED_BY_POLICY", {"label": "POL-010 15m Readback SLA"})
                # Prescriptions
                rxs = [r for r in self.builder.prescriptions.values() if r.uhid == target_uhid][:2]
                for r in rxs:
                    add_edge(pat, r, "HAS_PRESCRIPTION", {"label": "Ward Prescription"})

        # ---------------------------------------------------------------------
        # 3. BED CAPACITY & FLEET TURNAROUND PERSPECTIVE
        # ---------------------------------------------------------------------
        elif perspective == "beds":
            target_ward = ward or "Ward 1A"
            ward_beds = [b for b in self.builder.beds.values() if target_ward.lower() in b.ward.lower()][:18]
            if not ward_beds:
                ward_beds = list(self.builder.beds.values())[:18]

            # Ward Hub
            from app.ontology.models import DepartmentNode
            ward_hub = DepartmentNode(
                id=make_smch_uuid("ward_hub", target_ward),
                dept_id=target_ward,
                name=f"{target_ward} Station",
                dept_type="Inpatient Ward",
                dense_summary=f"WARD FLEET [{target_ward}] Live Census & Turnaround Queue"
            )
            add_node(ward_hub)

            team_hk = next((t for t in self.builder.support_teams.values() if "Housekeeping" in t.name or "Sanit" in t.name), None)
            sop_hk = next((s for k, s in self.builder.sops.items() if "HK" in k or "CLEAN" in k or "DISCHARGE" in k), None)

            for b in ward_beds:
                add_node(b)
                add_edge(ward_hub, b, "CONTAINS_BED", {"label": "Bed Station"})
                if b.status == "occupied" and b.current_patient_uhid:
                    pat = self.builder.patients.get(b.current_patient_uhid)
                    if pat:
                        add_edge(pat, b, "OCCUPIES", {"label": "Occupies Bed"})
                elif b.status == "dirty":
                    if team_hk:
                        add_edge(b, team_hk, "AWAITING_TURNAROUND", {"label": "🧹 Turnaround Queue"})
                    if sop_hk:
                        add_edge(b, sop_hk, "GOVERNED_BY", {"label": "Sanitization Protocol"})

        # ---------------------------------------------------------------------
        # 4. INSTITUTIONAL GOVERNANCE TOPOLOGY PERSPECTIVE
        # ---------------------------------------------------------------------
        elif perspective == "governance":
            for d in list(self.builder.departments.values())[:6]:
                add_node(d)
            for wf in list(self.builder.workflows.values())[:4]:
                add_node(wf)
                dept = next((dp for dp in self.builder.departments.values() if dp.name.lower() in wf.department.lower()), None)
                if dept:
                    add_edge(dept, wf, "OWNS_WORKFLOW", {"label": "Owns Workflow"})
            for sop in list(self.builder.sops.values())[:4]:
                add_node(sop)
            for pol in list(self.builder.policies.values())[:4]:
                add_node(pol)
            for r in list(self.builder.routing_rules.values())[:5]:
                add_node(r)
                team = next((t for t in self.builder.support_teams.values() if r.route_to_team.lower() in t.name.lower() or t.name.lower() in r.route_to_team.lower()), None)
                if team:
                    add_edge(r, team, "DISPATCHES_TO_TEAM", {"label": f"Dispatches to Team (Ext {team.contact_extension})"})

        # ---------------------------------------------------------------------
        # 5. FULL ONTOLOGY — all nodes, all types, no filtering
        # ---------------------------------------------------------------------
        elif perspective == "full_ontology":
            for n in self.builder.patients.values():
                add_node(n)
            for n in self.builder.beds.values():
                add_node(n)
            for n in self.builder.admissions.values():
                add_node(n)
            for n in self.builder.discharges.values():
                add_node(n)
            for n in self.builder.lab_critical_alerts.values():
                add_node(n)
            for n in self.builder.lab_results.values():
                add_node(n)
            for n in self.builder.bills.values():
                add_node(n)
            for n in self.builder.claims.values():
                add_node(n)
            for n in self.builder.prescriptions.values():
                add_node(n)
            for n in self.builder.emergency_cases.values():
                add_node(n)
            for n in self.builder.sops.values():
                add_node(n)
            for n in self.builder.policies.values():
                add_node(n)
            for n in self.builder.articles.values():
                add_node(n)
            for n in self.builder.routing_rules.values():
                add_node(n)
            for n in self.builder.departments.values():
                add_node(n)
            for n in self.builder.staff.values():
                add_node(n)
            for n in self.builder.support_teams.values():
                add_node(n)
            for n in self.builder.workflows.values():
                add_node(n)
            # Core semantic edges — patient occupancy and discharge links
            for adm in self.builder.admissions.values():
                pat = self.builder.patients.get(adm.uhid)
                bed = self.builder.beds.get(adm.bed_id) if adm.bed_id else None
                if pat:
                    add_edge(pat, adm, "HAS_ADMISSION", {"label": "Admission"})
                if pat and bed:
                    add_edge(pat, bed, "OCCUPIES", {"label": "Occupies"})
            for dis in self.builder.discharges.values():
                pat = self.builder.patients.get(dis.uhid)
                if pat:
                    add_edge(pat, dis, "HAS_DISCHARGE_ORDER", {"label": "Discharge"})
            for alert in self.builder.lab_critical_alerts.values():
                pat = self.builder.patients.get(alert.uhid)
                if pat:
                    add_edge(pat, alert, "TRIGGERS_PANIC_ALERT", {"label": "Panic Alert"})
            for bill in self.builder.bills.values():
                pat = self.builder.patients.get(bill.uhid)
                if pat:
                    add_edge(pat, bill, "INCURRED_BILL", {"label": "Bill"})
            for claim in self.builder.claims.values():
                pat = self.builder.patients.get(claim.uhid)
                if pat:
                    add_edge(pat, claim, "HAS_CLAIM", {"label": "Claim"})

        # ---------------------------------------------------------------------
        # 6. MACRO HOSPITAL FLEET (CURATED SUBSET - NO HAIRBALL)
        # ---------------------------------------------------------------------
        else:
            # Curated macro graph (max 60 nodes)
            for d in list(self.builder.discharges.values()):
                if d.is_blocked:
                    add_node(d)
            for a in list(self.builder.lab_critical_alerts.values()):
                if a.readback_status != "Acknowledged":
                    add_node(a)
            for p in list(self.builder.patients.values())[:8]:
                add_node(p)
            for b in list(self.builder.beds.values())[:10]:
                add_node(b)
            for s in list(self.builder.staff.values())[:6]:
                add_node(s)
            for sop in list(self.builder.sops.values())[:4]:
                add_node(sop)
            for r in list(self.builder.routing_rules.values())[:4]:
                add_node(r)
            for t in list(self.builder.support_teams.values())[:5]:
                add_node(t)

        vis_nodes = [self.format_vis_node(n) for n in nodes_map.values()]
        vis_edges = [self.format_vis_edge(src, tgt, rel, data) for src, tgt, rel, data in raw_edges]

        # Calculate high-level KPIs
        blocked_cnt = sum(1 for d in self.builder.discharges.values() if d.is_blocked)
        panic_cnt = sum(1 for a in self.builder.lab_critical_alerts.values() if a.readback_status != "Acknowledged" and a.is_sla_breached)
        dirty_cnt = sum(1 for b in self.builder.beds.values() if b.status == "dirty")
        risk_rev = sum(b.unbilled_consumables for b in self.builder.bills.values())

        return {
            "status": "success",
            "perspective": perspective,
            "nodes_count": len(vis_nodes),
            "edges_count": len(vis_edges),
            "nodes": vis_nodes,
            "edges": vis_edges,
            "kpis": {
                "blocked_discharges": blocked_cnt,
                "panic_slas_breached": panic_cnt,
                "dirty_turnaround_queue": dirty_cnt,
                "revenue_at_risk_inr": risk_rev
            }
        }

    def generate_command_center_html(self, initial_perspective: str = "bottlenecks") -> str:
        """Builds the Acentra Operations Intelligence Command Center HTML."""
        subgraph = self.get_perspective_subgraph(perspective=initial_perspective)
        raw_nodes = subgraph["nodes"]
        raw_edges = subgraph["edges"]
        kpis = subgraph["kpis"]

        # Generate patient options for selector
        patient_options = ""
        for uhid, p in list(self.builder.patients.items())[:15]:
            patient_options += f'<option value="{uhid}">{p.name} ({uhid})</option>\n'

        # Generate ward options
        ward_options = """
        <option value="Ward 1A" selected>Ward 1A (General Medicine)</option>
        <option value="Ward 1B">Ward 1B (General Surgery)</option>
        <option value="Ward 2B">Ward 2B (Cardiology)</option>
        <option value="ICU">ICU (Intensive Care)</option>
        <option value="Emergency">Emergency Triage</option>
        """

        total_nodes = (
            len(self.builder.patients) + len(self.builder.beds) +
            len(self.builder.admissions) + len(self.builder.discharges) +
            len(self.builder.lab_critical_alerts) + len(self.builder.lab_results) +
            len(self.builder.bills) + len(self.builder.claims) +
            len(self.builder.prescriptions) + len(self.builder.emergency_cases) +
            len(self.builder.sops) + len(self.builder.policies) +
            len(self.builder.articles) + len(self.builder.routing_rules) +
            len(self.builder.departments) + len(self.builder.staff) +
            len(self.builder.support_teams) + len(self.builder.workflows)
        )
        total_edges = 1181  # structural edges in Kùzu

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SMCH Operations Intelligence Center · Palantir Foundry Architecture</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap">
  <script src="vis-network.min.js"></script>
  <style>
    :root {{
      --bg-canvas: #060911;
      --bg-panel: rgba(11, 17, 30, 0.92);
      --bg-surface: #0E1626;
      --border-subtle: rgba(255, 255, 255, 0.07);
      --border-strong: rgba(255, 255, 255, 0.14);
      --text-primary: #F8FAFC;
      --text-secondary: #94A3B8;
      --text-muted: #64748B;
      --accent-blue: #2563EB;
      --accent-emerald: #10B981;
      --accent-rose: #F43F5E;
      --accent-amber: #F59E0B;
      --accent-cyan: #06B6D4;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      background: var(--bg-canvas);
      color: var(--text-primary);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
    }}

    /* ── Executive Header ── */
    header {{
      background: #090E19;
      border-bottom: 1px solid var(--border-subtle);
      padding: 9px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 20;
    }}
    .brand {{
      display: flex; align-items: center; gap: 14px;
    }}
    .brand-icon {{
      width: 32px; height: 32px; border-radius: 8px;
      background: linear-gradient(135deg, #1E293B, #0F172A);
      border: 1px solid rgba(56, 189, 248, 0.35);
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 0 12px rgba(14, 165, 233, 0.2);
    }}
    .brand-icon svg {{ width: 18px; height: 18px; fill: none; stroke: #38BDF8; stroke-width: 2; }}
    .brand-text {{ display: flex; flex-direction: column; }}
    .brand-text .eyebrow {{
      font-size: 9.5px; font-weight: 700; color: #64748B;
      letter-spacing: 0.08em; text-transform: uppercase;
    }}
    .brand-text h1 {{
      font-size: 14.5px; font-weight: 700; color: #F8FAFC;
      letter-spacing: -0.01em; line-height: 1.2;
    }}
    .live-badge {{
      display: flex; align-items: center; gap: 6px;
      background: rgba(16, 185, 129, 0.09); border: 1px solid rgba(16, 185, 129, 0.25);
      padding: 3px 9px; border-radius: 12px; margin-left: 10px;
      font-size: 9.5px; font-weight: 700; letter-spacing: 0.06em;
      text-transform: uppercase; color: #34D399; font-family: 'JetBrains Mono', monospace;
    }}
    .live-dot {{
      width: 6px; height: 6px; background: #10B981; border-radius: 50%;
      box-shadow: 0 0 8px #10B981; animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(1.25); }}
    }}

    .actions-bar {{ display: flex; gap: 8px; align-items: center; }}
    button.btn {{
      padding: 6px 13px; border-radius: 6px; font-size: 11px; font-weight: 600;
      cursor: pointer; transition: all 0.15s ease; border: 1px solid transparent;
      display: flex; align-items: center; gap: 6px; letter-spacing: 0.01em;
      font-family: inherit;
    }}
    button.btn-settle {{
      background: rgba(16, 185, 129, 0.12); color: #34D399;
      border-color: rgba(16, 185, 129, 0.35);
    }}
    button.btn-settle:hover {{
      background: rgba(16, 185, 129, 0.22); border-color: #34D399;
      box-shadow: 0 0 10px rgba(16, 185, 129, 0.25);
    }}
    button.btn-panic {{
      background: rgba(244, 63, 94, 0.12); color: #FB7185;
      border-color: rgba(244, 63, 94, 0.35);
    }}
    button.btn-panic:hover {{
      background: rgba(244, 63, 94, 0.22); border-color: #FB7185;
      box-shadow: 0 0 10px rgba(244, 63, 94, 0.25);
    }}
    button.btn-turnaround {{
      background: rgba(6, 182, 212, 0.12); color: #22D3EE;
      border-color: rgba(6, 182, 212, 0.35);
    }}
    button.btn-turnaround:hover {{
      background: rgba(6, 182, 212, 0.22); border-color: #22D3EE;
      box-shadow: 0 0 10px rgba(6, 182, 212, 0.25);
    }}
    button.btn-reset {{
      background: rgba(148, 163, 184, 0.08); color: #94A3B8;
      border-color: rgba(148, 163, 184, 0.2);
    }}
    button.btn-reset:hover {{
      background: rgba(148, 163, 184, 0.16); color: #F1F5F9;
      border-color: rgba(148, 163, 184, 0.4);
    }}

    /* ── Sub Navigation & Perspective Ribbon ── */
    .sub-bar {{
      background: #0A0F1D; border-bottom: 1px solid var(--border-subtle);
      padding: 6px 24px; display: flex; justify-content: space-between;
      align-items: center; z-index: 15;
    }}
    .perspectives-tabs {{
      display: flex; gap: 3px; align-items: center;
      background: #060A13; padding: 3px; border-radius: 8px;
      border: 1px solid var(--border-subtle);
    }}
    .tab-btn {{
      background: transparent; color: #94A3B8; border: none;
      padding: 5px 12px; border-radius: 6px; font-size: 11px; font-weight: 500;
      cursor: pointer; transition: all 0.15s ease; font-family: inherit;
    }}
    .tab-btn:hover {{ color: #F1F5F9; background: rgba(255, 255, 255, 0.05); }}
    .tab-btn.active {{
      background: #1D4ED8; color: #FFFFFF; font-weight: 600;
      box-shadow: 0 2px 8px rgba(29, 78, 216, 0.35);
    }}
    #tab-full_ontology {{
      color: #64748B; margin-left: 2px; border-left: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 0 6px 6px 0;
    }}
    #tab-full_ontology.active {{ background: #1E293B; color: #CBD5E1; }}

    .telemetry-indicator {{
      display: flex; align-items: center; gap: 8px;
      font-size: 11px; color: #64748B; font-family: 'JetBrains Mono', monospace;
    }}
    .telemetry-indicator b {{ color: #94A3B8; font-weight: 600; }}
    .telemetry-indicator .sep {{ color: rgba(255, 255, 255, 0.12); }}

    .sub-controls {{ display: flex; gap: 8px; align-items: center; }}
    .search-wrapper {{
      position: relative; display: flex; align-items: center;
    }}
    .search-icon {{
      position: absolute; left: 9px; width: 13px; height: 13px;
      fill: none; stroke: #64748B; stroke-width: 2; pointer-events: none;
    }}
    input#searchBox {{
      background: #080D18; border: 1px solid var(--border-strong);
      color: #E2E8F0; padding: 5px 28px 5px 28px; border-radius: 6px;
      font-size: 11px; width: 220px; outline: none; font-family: inherit;
      transition: all 0.15s ease;
    }}
    input#searchBox:focus {{
      border-color: #3B82F6; box-shadow: 0 0 10px rgba(59, 130, 246, 0.25);
      background: #0B1322;
    }}
    .search-shortcut {{
      position: absolute; right: 7px; font-size: 9px;
      color: #475569; background: #0F172A; padding: 1px 4px;
      border-radius: 3px; font-family: 'JetBrains Mono', monospace;
    }}
    select.ctx-select {{
      background: #080D18; border: 1px solid var(--border-strong);
      color: #E2E8F0; padding: 5px 10px; border-radius: 6px;
      font-size: 11px; outline: none; font-family: inherit; cursor: pointer;
    }}
    .icon-btn {{
      background: rgba(255, 255, 255, 0.04); color: #94A3B8;
      border: 1px solid var(--border-subtle); padding: 5px 10px;
      border-radius: 6px; font-size: 11px; font-weight: 500; cursor: pointer;
      transition: all 0.15s; font-family: inherit;
    }}
    .icon-btn:hover {{
      background: rgba(255, 255, 255, 0.08); color: #F1F5F9;
      border-color: var(--border-strong);
    }}

    /* ── Main Canvas Viewport ── */
    main {{
      display: flex; flex: 1; height: calc(100vh - 96px);
      position: relative; overflow: hidden;
    }}
    #network {{
      flex: 1; width: 100%; height: 100%;
      background-color: var(--bg-canvas);
      background-image: radial-gradient(rgba(148, 163, 184, 0.11) 1.2px, transparent 1.2px);
      background-size: 26px 26px;
    }}

    /* ── Floating Operational KPI Deck ── */
    .kpi-deck {{
      position: absolute; top: 16px; left: 20px;
      background: var(--bg-panel); backdrop-filter: blur(16px);
      border: 1px solid var(--border-strong); padding: 10px 16px;
      border-radius: 10px; display: flex; flex-direction: column; gap: 6px;
      z-index: 10; box-shadow: 0 12px 30px rgba(0, 0, 0, 0.55);
      min-width: 280px;
    }}
    .kpi-header {{
      display: flex; justify-content: space-between; align-items: center;
      padding-bottom: 5px; border-bottom: 1px solid var(--border-subtle);
    }}
    .kpi-title {{
      font-size: 9.5px; font-weight: 700; letter-spacing: 0.07em;
      text-transform: uppercase; color: #64748B;
    }}
    .kpi-pulse {{
      width: 6px; height: 6px; border-radius: 50%; background: #F43F5E;
      box-shadow: 0 0 6px #F43F5E;
    }}
    .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 3px; }}
    .kpi-box {{ display: flex; flex-direction: column; gap: 2px; }}
    .kpi-box .lbl {{ font-size: 9px; color: #64748B; font-weight: 600; text-transform: uppercase; letter-spacing: 0.02em; }}
    .kpi-box .val {{ font-size: 16px; font-weight: 800; line-height: 1.1; font-family: 'JetBrains Mono', monospace; }}
    .kpi-box .val.rose {{ color: #FB7185; }}
    .kpi-box .val.amber {{ color: #FBBF24; }}
    .kpi-box .val.cyan {{ color: #38BDF8; }}
    .kpi-box .val.red {{ color: #F43F5E; }}

    /* ── Floating Viewport Dock (Bottom-Center) ── */
    .viewport-dock {{
      position: absolute; bottom: 18px; left: 50%; transform: translateX(-50%);
      background: var(--bg-panel); backdrop-filter: blur(16px);
      border: 1px solid var(--border-strong); padding: 5px 8px;
      border-radius: 20px; display: flex; gap: 5px; align-items: center;
      z-index: 10; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    }}
    .dock-btn {{
      background: transparent; color: #94A3B8; border: none;
      width: 28px; height: 28px; border-radius: 50%; display: flex;
      align-items: center; justify-content: center; font-size: 12px;
      cursor: pointer; transition: all 0.15s; font-family: inherit;
    }}
    .dock-btn:hover {{ background: rgba(255, 255, 255, 0.1); color: #F8FAFC; }}
    .dock-sep {{ width: 1px; height: 16px; background: var(--border-subtle); }}

    /* ── Floating Interactive Legend (Bottom-Right) ── */
    .legend-deck {{
      position: absolute; bottom: 18px; right: 20px;
      background: var(--bg-panel); backdrop-filter: blur(16px);
      border: 1px solid var(--border-strong); padding: 8px 14px;
      border-radius: 8px; display: flex; gap: 14px; font-size: 11px;
      z-index: 10; color: #94A3B8; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    }}
    .legend-chip {{
      display: flex; align-items: center; gap: 6px; cursor: pointer;
      transition: color 0.15s;
    }}
    .legend-chip:hover {{ color: #F8FAFC; }}
    .legend-pill {{ width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }}

    /* ── Notification Banner ── */
    .banner {{
      position: absolute; top: 16px; left: 50%; transform: translateX(-50%);
      background: rgba(9, 14, 26, 0.96); border: 1px solid #2563EB;
      padding: 7px 18px; border-radius: 8px; font-size: 11.5px; color: #E2E8F0;
      display: none; z-index: 40; box-shadow: 0 8px 25px rgba(0,0,0,0.7);
      white-space: nowrap; font-family: 'JetBrains Mono', monospace;
    }}

    /* ── Slide-Over Object Inspector (Right Drawer) ── */
    aside.drawer {{
      position: absolute; top: 0; right: 0; width: 420px; height: 100%;
      background: rgba(9, 14, 25, 0.96); backdrop-filter: blur(24px);
      border-left: 1px solid var(--border-strong); transform: translateX(100%);
      transition: transform 0.24s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex; flex-direction: column; z-index: 30; padding: 22px;
      overflow-y: auto; gap: 14px; box-shadow: -10px 0 35px rgba(0, 0, 0, 0.7);
    }}
    aside.drawer.open {{ transform: translateX(0); }}
    .drawer-header {{
      display: flex; justify-content: space-between; align-items: flex-start;
      border-bottom: 1px solid var(--border-subtle); padding-bottom: 14px;
    }}
    .drawer-tag {{
      display: inline-block; font-size: 9.5px; font-weight: 700;
      letter-spacing: 0.08em; text-transform: uppercase; color: #38BDF8;
      background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.25);
      padding: 2px 7px; border-radius: 4px; margin-bottom: 6px;
      font-family: 'JetBrains Mono', monospace;
    }}
    .drawer-title {{
      font-size: 15px; font-weight: 700; color: #F8FAFC;
      letter-spacing: -0.01em; line-height: 1.3;
    }}
    .close-btn {{
      background: transparent; border: none; color: #64748B;
      font-size: 20px; cursor: pointer; line-height: 1; padding: 4px;
      transition: color 0.15s;
    }}
    .close-btn:hover {{ color: #F1F5F9; }}

    .card {{
      background: #0C1220; border-radius: 8px; padding: 13px;
      border: 1px solid var(--border-subtle); display: flex; flex-direction: column; gap: 8px;
    }}
    .card-title {{
      font-size: 9.5px; text-transform: uppercase; letter-spacing: 0.07em;
      color: #64748B; font-weight: 700; font-family: 'JetBrains Mono', monospace;
    }}
    .card-content {{ font-size: 12px; line-height: 1.6; color: #CBD5E1; }}
    table.props-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
    table.props-table tr {{ border-bottom: 1px solid rgba(255, 255, 255, 0.05); }}
    table.props-table tr:last-child {{ border-bottom: none; }}
    table.props-table td {{ padding: 6px 0; }}
    table.props-table td.k {{
      color: #64748B; font-family: 'JetBrains Mono', monospace;
      width: 44%; font-size: 10.5px;
    }}
    table.props-table td.v {{
      color: #E2E8F0; font-weight: 500; word-break: break-all;
      font-family: 'JetBrains Mono', monospace; font-size: 10.5px;
    }}

    /* ── Governed Agent Assistant Panel ── */
    .agent-panel {{
      position: absolute; bottom: 0; right: 0; width: 420px; height: 520px;
      background: rgba(7, 11, 20, 0.98); backdrop-filter: blur(20px);
      border-left: 1px solid var(--border-strong); border-top: 1px solid var(--border-strong);
      display: flex; flex-direction: column; z-index: 25;
      transform: translateY(100%); transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .agent-panel.open {{ transform: translateY(0); }}
    .agent-header {{ padding: 14px 16px 10px; border-bottom: 1px solid var(--border-subtle); }}
    .agent-title-row {{ display: flex; justify-content: space-between; align-items: flex-start; }}
    .agent-title {{ font-size: 13px; font-weight: 700; color: #F1F5F9; letter-spacing: -0.01em; }}
    .agent-subtitle {{
      font-size: 9.5px; color: #64748B; margin-top: 2px;
      font-family: 'JetBrains Mono', monospace; letter-spacing: 0.04em;
    }}
    .agent-messages {{
      flex: 1; overflow-y: auto; padding: 12px 14px;
      display: flex; flex-direction: column; gap: 8px;
    }}
    .agent-message {{
      font-size: 12px; line-height: 1.6; padding: 9px 12px;
      border-radius: 6px; max-width: 100%;
    }}
    .agent-msg-system {{ background: #0A0F1D; color: #64748B; border: 1px solid var(--border-subtle); }}
    .agent-msg-user {{ background: #0E2244; color: #93C5FD; border: 1px solid #1E3A5F; align-self: flex-end; max-width: 90%; }}
    .agent-msg-answer {{ background: #071C12; color: #6EE7B7; border: 1px solid rgba(16, 185, 129, 0.25); }}
    .agent-msg-guardrail {{ background: #200B0E; color: #FCA5A5; border: 1px solid rgba(244, 63, 94, 0.3); }}
    .agent-msg-escalation {{ font-size: 10px; color: #64748B; margin-top: 5px; font-family: 'JetBrains Mono', monospace; }}
    .agent-msg-citation {{ font-size: 10px; color: #475569; margin-top: 4px; font-family: 'JetBrains Mono', monospace; }}
    /* Confidence badge — requirement 3 */
    .confidence-badge {{ display:inline-block; font-size:9.5px; font-weight:700; padding:2px 7px; border-radius:3px; margin-bottom:5px; font-family:'JetBrains Mono',monospace; letter-spacing:0.07em; }}
    .conf-high {{ background:#052E16; color:#4ADE80; border:1px solid #166534; }}
    .conf-medium {{ background:#1C1400; color:#FBBF24; border:1px solid #78350F; }}
    .conf-low {{ background:#1F0505; color:#F87171; border:1px solid #7F1D1D; }}
    .conf-uncertain {{ background:#1A1226; color:#A78BFA; border:1px solid #4C1D95; }}
    /* Source citations block — requirement 2 */
    .citations-block {{ margin-top:6px; padding:5px 8px; background:#080C14; border:1px solid #1E293B; border-radius:4px; }}
    .citations-block .cit-title {{ font-size:9px; color:#475569; font-family:'JetBrains Mono',monospace; margin-bottom:3px; text-transform:uppercase; letter-spacing:0.08em; }}
    .citations-block .cit-item {{ font-size:10px; color:#6EE7B7; font-family:'JetBrains Mono',monospace; line-height:1.5; }}
    /* Workflow step card — requirement 4 */
    .workflow-step-card {{ margin-top:6px; padding:7px 10px; background:#071018; border:1px solid #0C4A6E; border-radius:4px; }}
    .workflow-step-card .wf-title {{ font-size:9px; color:#38BDF8; font-family:'JetBrains Mono',monospace; text-transform:uppercase; margin-bottom:3px; letter-spacing:0.08em; }}
    .workflow-step-card .wf-step {{ font-size:11px; color:#BAE6FD; font-weight:600; }}
    .workflow-step-card .wf-desc {{ font-size:10.5px; color:#94A3B8; margin-top:2px; }}
    .workflow-step-card .wf-team {{ font-size:10px; color:#475569; margin-top:3px; font-family:'JetBrains Mono',monospace; }}
    /* Missing fields card — requirement 5 */
    .missing-fields-card {{ margin-top:6px; padding:7px 10px; background:#130A00; border:1px solid #78350F; border-radius:4px; }}
    .missing-fields-card .mf-title {{ font-size:9px; color:#F59E0B; font-family:'JetBrains Mono',monospace; text-transform:uppercase; margin-bottom:3px; letter-spacing:0.08em; }}
    .missing-fields-card .mf-item {{ font-size:10.5px; color:#FDE68A; margin-top:2px; }}
    /* Escalation reason — requirements 6, 14 */
    .escalation-reason {{ font-size:10px; color:#F87171; margin-top:4px; font-family:'JetBrains Mono',monospace; }}
    .agent-input-row {{ display: flex; gap: 7px; padding: 10px 14px; border-top: 1px solid var(--border-subtle); }}
    .agent-input {{
      flex: 1; background: #080D18; border: 1px solid var(--border-strong);
      color: #E2E8F0; padding: 7px 11px; border-radius: 6px; font-size: 12px;
      outline: none; font-family: inherit;
    }}
    .agent-input:focus {{ border-color: #2563EB; }}
    .agent-send-btn {{
      background: #1D4ED8; color: #FFF; border: none; padding: 7px 15px;
      border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;
    }}
    .agent-toggle-btn {{
      position: absolute; bottom: 18px; right: 480px;
      background: #1E293B; color: #E2E8F0; border: 1px solid var(--border-strong);
      padding: 7px 14px; border-radius: 20px; font-size: 11px; font-weight: 600;
      cursor: pointer; z-index: 15; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
      display: flex; align-items: center; gap: 6px; transition: all 0.15s;
    }}
    .agent-toggle-btn:hover {{ background: #2563EB; color: #FFF; border-color: #3B82F6; }}
  </style>
</head>
<body>
  <!-- Executive Command Header -->
  <header>
    <div class="brand">
      <div class="brand-icon">
        <svg viewBox="0 0 24 24"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
      </div>
      <div class="brand-text">
        <div class="eyebrow">Saveetha Medical College &amp; Hospital &nbsp;&middot;&nbsp; Digital Twin</div>
        <h1>Operations Intelligence Studio</h1>
      </div>
      <div class="live-badge">
        <span class="live-dot"></span> LIVE RECONCILED
      </div>
    </div>
    <div class="actions-bar">
      <a href="/dashboard" style="color:#60a5fa;font-size:12px;font-weight:600;text-decoration:none;padding:7px 12px;border:1px solid #1e3a5f;border-radius:6px;background:#0d1f3c;white-space:nowrap;">Admin Dashboard</a>
      <button class="btn btn-settle" onclick="triggerAction('settle_billing')">
        <span>&#9889;</span> Settle Billing Hold
      </button>
      <button class="btn btn-panic" onclick="triggerAction('resolve_panic')">
        <span>&#129658;</span> Acknowledge Readback
      </button>
      <button class="btn btn-turnaround" onclick="triggerAction('turnaround_bed')">
        <span>&#10024;</span> Turnaround Bed
      </button>
      <button class="btn btn-reset" onclick="triggerAction('reset_ontology')">
        <span>&#8634;</span> Reset Baseline
      </button>
    </div>
  </header>

  <!-- Sub Navigation & Perspective Ribbon -->
  <div class="sub-bar">
    <div class="perspectives-tabs">
      <button class="tab-btn active" id="tab-bottlenecks" onclick="switchPerspective('bottlenecks')">&#128680; Priority Incidents</button>
      <button class="tab-btn" id="tab-patient_360" onclick="switchPerspective('patient_360')">&#128100; Patient 360&deg;</button>
      <button class="tab-btn" id="tab-beds" onclick="switchPerspective('beds')">&#128719;&#65039; Bed Fleet</button>
      <button class="tab-btn" id="tab-governance" onclick="switchPerspective('governance')">&#127963;&#65039; Governance</button>
      <button class="tab-btn" id="tab-macro" onclick="switchPerspective('macro')">&#127760; Hospital Overview</button>
      <button class="tab-btn" id="tab-full_ontology" onclick="switchPerspective('full_ontology')">&#9889; Full Ontology</button>
    </div>

    <div class="telemetry-indicator">
      <span>K&ugrave;zu Engine</span>
      <span class="sep">&middot;</span>
      <span><b id="totalNodes">{total_nodes}</b> nodes</span>
      <span class="sep">&middot;</span>
      <span><b id="totalEdges">{total_edges}</b> edges</span>
      <span class="sep">&middot;</span>
      <span>Viewing <b id="viewingCount">&mdash;</b></span>
    </div>

    <div class="sub-controls">
      <select class="ctx-select" id="patientSelect" style="display:none;" onchange="loadPatient360(this.value)">
        {patient_options}
      </select>
      <select class="ctx-select" id="wardSelect" style="display:none;" onchange="loadWardBeds(this.value)">
        {ward_options}
      </select>
      <div class="search-wrapper">
        <svg class="search-icon" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <input type="text" id="searchBox" placeholder="Search patient, bed, rule..." oninput="handleSearch(this.value)">
        <span class="search-shortcut">/</span>
      </div>
      <button class="icon-btn" id="freezeBtn" onclick="togglePhysics()">Freeze</button>
      <button class="icon-btn" onclick="resetZoom()">Fit</button>
      <button class="icon-btn" onclick="focusBottlenecks()">Focus Blocker</button>
    </div>
  </div>

  <!-- Main Viewport -->
  <main>
    <div id="banner" class="banner"></div>
    <div id="network"></div>

    <!-- Floating Operational KPI Deck -->
    <div class="kpi-deck" id="kpiBar">
      <div class="kpi-header">
        <span class="kpi-title">Operational Bottleneck Radar</span>
        <span class="kpi-pulse"></span>
      </div>
      <div class="kpi-row">
        <div class="kpi-box">
          <span class="lbl">Blocked</span>
          <span class="val rose" id="kpiBlockers">{kpis.get('blocked_discharges', 3)}</span>
        </div>
        <div class="kpi-box">
          <span class="lbl">SLA Breached</span>
          <span class="val amber" id="kpiPanics">{kpis.get('panic_slas_breached', 1)}</span>
        </div>
        <div class="kpi-box">
          <span class="lbl">Dirty Queue</span>
          <span class="val cyan" id="kpiBeds">{kpis.get('dirty_turnaround_queue', 4)}</span>
        </div>
        <div class="kpi-box">
          <span class="lbl">Revenue Risk</span>
          <span class="val red" id="kpiRev">&#8377;{kpis.get('revenue_at_risk_inr', 68000):,.0f}</span>
        </div>
      </div>
    </div>

    <!-- Floating Viewport Controls Dock -->
    <div class="viewport-dock">
      <button class="dock-btn" onclick="zoomIn()" title="Zoom In">+</button>
      <button class="dock-btn" onclick="zoomOut()" title="Zoom Out">&minus;</button>
      <div class="dock-sep"></div>
      <button class="dock-btn" onclick="resetZoom()" title="Fit View">&#x26F6;</button>
      <button class="dock-btn" onclick="focusBottlenecks()" title="Focus Incidents">&#127919;</button>
      <div class="dock-sep"></div>
      <button class="dock-btn" onclick="togglePhysics()" title="Toggle Physics Layout">&#9889;</button>
    </div>

    <!-- Floating Interactive Legend -->
    <div class="legend-deck">
      <div class="legend-chip" onclick="filterLegend('Incidents')">
        <div class="legend-pill" style="background:#F43F5E;"></div> Incident / Hold
      </div>
      <div class="legend-chip" onclick="filterLegend('Patients')">
        <div class="legend-pill" style="background:#0EA5E9;"></div> Patient Twin
      </div>
      <div class="legend-chip" onclick="filterLegend('Beds')">
        <div class="legend-pill" style="background:#818CF8;"></div> Bed Unit
      </div>
      <div class="legend-chip" onclick="filterLegend('Governance')">
        <div class="legend-pill" style="background:#6366F1;"></div> Governance SOP
      </div>
      <div class="legend-chip" onclick="filterLegend('Financial')">
        <div class="legend-pill" style="background:#F59E0B;"></div> Financial Claim
      </div>
      <div class="legend-chip" onclick="filterLegend('Staff')">
        <div class="legend-pill" style="background:#38BDF8;"></div> Clinician
      </div>
    </div>

    <!-- Slide-Over Object Inspector -->
    <aside class="drawer" id="sideDrawer">
      <div class="drawer-header">
        <div>
          <div class="drawer-tag" id="dType">DataPoint Entity</div>
          <div class="drawer-title" id="dTitle">Entity Details</div>
        </div>
        <button class="close-btn" onclick="closeDrawer()">&times;</button>
      </div>
      <div id="drawerActionCard" class="card" style="display:none;">
        <div class="card-title">Governed Remediation Action</div>
        <button id="drawerActionBtn" class="btn btn-settle" style="width:100%; justify-content:center; padding:9px 14px; font-size:12px;"></button>
      </div>
      <div class="card">
        <div class="card-title">Operational Context &amp; Mandate</div>
        <div class="card-content" id="dSummary">&mdash;</div>
      </div>
      <div class="card">
        <div class="card-title">Live Telemetry &amp; Properties</div>
        <table class="props-table" id="dProps"></table>
      </div>
    </aside>

    <!-- Governed Agent Panel — Surface 2 -->
    <div id="agentPanel" class="agent-panel">
      <div class="agent-header">
        <div class="agent-title-row">
          <div>
            <div class="agent-title">Operations Assistant</div>
            <div class="agent-subtitle">GOVERNED &nbsp;&middot;&nbsp; GRAPH-GROUNDED &nbsp;&middot;&nbsp; POLICY-CITED</div>
          </div>
          <button class="close-btn" onclick="toggleAgentPanel()">&times;</button>
        </div>
      </div>
      <div id="agentMessages" class="agent-messages">
        <div class="agent-message agent-msg-system">
          Ask any operational question. I traverse the live graph &mdash; grounded in institutional policies.<br>
          <span style="color:#60A5FA;font-size:10.5px;font-family:'JetBrains Mono',monospace;">Try: "Why is SMCH-857250's gate pass not printing?"</span>
        </div>
      </div>
      <div class="agent-input-row">
        <input type="text" id="agentInput" class="agent-input"
               placeholder="Query operational ontology..."
               onkeydown="if(event.key==='Enter') sendAgentQuery()">
        <button class="agent-send-btn" onclick="sendAgentQuery()">Ask</button>
      </div>
    </div>
    <button id="agentToggleBtn" class="agent-toggle-btn" onclick="toggleAgentPanel()">
      <span>&#129302;</span> Operations Assistant
    </button>
  </main>

  <script>
    let network = null;
    let currentNodes = {json.dumps(raw_nodes, default=str)};
    let currentEdges = {json.dumps(raw_edges, default=str)};
    let currentPerspective = "{initial_perspective}";
    let physicsFrozen = false;

    function renderNetwork(nodesList, edgesList) {{
      const container = document.getElementById("network");
      const data = {{
        nodes: new vis.DataSet(nodesList),
        edges: new vis.DataSet(edgesList)
      }};
      const options = {{
        nodes: {{
          shape: 'box',
          shapeProperties: {{ borderRadius: 7 }},
          margin: {{ top: 9, bottom: 9, left: 13, right: 13 }},
          borderWidth: 1.5,
          borderWidthSelected: 2.5,
          shadow: {{ enabled: true, color: 'rgba(0,0,0,0.6)', size: 12, x: 0, y: 4 }},
          font: {{
            face: "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif",
            size: 11,
            color: '#F8FAFC'
          }}
        }},
        edges: {{
          shadow: false,
          smooth: {{ type: 'cubicBezier', forceDirection: 'none', roundness: 0.18 }},
          arrows: {{ to: {{ enabled: true, scaleFactor: 0.65 }} }},
          font: {{
            color: '#94A3B8',
            size: 9,
            face: "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif",
            strokeWidth: 0,
            background: '#0B111E',
            align: 'horizontal'
          }}
        }},
        physics: {{
          enabled: true,
          solver: 'barnesHut',
          barnesHut: {{
            gravitationalConstant: -9000,
            centralGravity: 0.14,
            springLength: 220,
            springConstant: 0.045,
            damping: 0.18,
            avoidOverlap: 1.0
          }},
          stabilization: {{ iterations: 140, updateInterval: 25 }}
        }},
        interaction: {{
          hover: true,
          hoverConnectedEdges: true,
          selectConnectedEdges: true,
          tooltipDelay: 150,
          zoomView: true,
          dragView: true,
          dragNodes: true,
          navigationButtons: false,
          keyboard: true
        }}
      }};

      network = new vis.Network(container, data, options);

      network.on("stabilizationIterationsDone", function () {{
        network.setOptions({{ physics: false }});
        physicsFrozen = true;
        document.getElementById("freezeBtn").innerText = "Resume";
      }});

      network.on("click", function(params) {{
        if (params.nodes.length > 0) {{
          const node = nodesList.find(n => n.id === params.nodes[0]);
          if (node) showDrawer(node);
        }}
      }});
    }}

    async function switchPerspective(perspName) {{
      currentPerspective = perspName;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      const activeTab = document.getElementById('tab-' + perspName);
      if (activeTab) activeTab.classList.add('active');

      document.getElementById('patientSelect').style.display = (perspName === 'patient_360') ? 'inline-block' : 'none';
      document.getElementById('wardSelect').style.display = (perspName === 'beds') ? 'inline-block' : 'none';

      await loadPerspectiveData(perspName);
    }}

    async function loadPerspectiveData(perspName, extraParams = '') {{
      showBanner(`Loading ${{perspName}} perspective...`);
      try {{
        const res = await fetch(`/api/v1/ontology/graph/live?perspective=${{perspName}}${{extraParams}}`);
        const data = await res.json();
        currentNodes = data.nodes;
        currentEdges = data.edges;
        renderNetwork(currentNodes, currentEdges);
        document.getElementById('viewingCount').innerText = currentNodes.length + ' / ' + document.getElementById('totalNodes').innerText;

        if (data.kpis) {{
          document.getElementById('kpiBlockers').innerText = data.kpis.blocked_discharges;
          document.getElementById('kpiPanics').innerText = data.kpis.panic_slas_breached;
          document.getElementById('kpiBeds').innerText = data.kpis.dirty_turnaround_queue;
          document.getElementById('kpiRev').innerText = '\u20b9' + Number(data.kpis.revenue_at_risk_inr).toLocaleString();
        }}
        showBanner(`${{perspName}} &middot; ${{data.nodes_count}} entities &middot; ${{data.edges_count}} relationships`);
      }} catch (err) {{
        console.error("Failed to load perspective:", err);
      }}
    }}

    function loadPatient360(uhid) {{
      loadPerspectiveData('patient_360', `&uhid=${{encodeURIComponent(uhid)}}`);
    }}

    function loadWardBeds(ward) {{
      loadPerspectiveData('beds', `&ward=${{encodeURIComponent(ward)}}`);
    }}

    async function triggerAction(actionName) {{
      showBanner(`Executing ${{actionName}}...`);
      try {{
        const res = await fetch(`/api/v1/ontology/action/${{actionName}}`, {{ method: 'POST' }});
        const result = await res.json();
        showBanner(result.message || 'Action executed successfully');
        await loadPerspectiveData(currentPerspective);
      }} catch (err) {{
        showBanner(`Action failed: ${{err}}`);
      }}
    }}

    function showBanner(msg) {{
      const b = document.getElementById("banner");
      b.innerHTML = msg;
      b.style.display = "block";
      setTimeout(() => {{ b.style.display = "none"; }}, 3500);
    }}

    function showDrawer(node) {{
      const drawer = document.getElementById("sideDrawer");
      drawer.classList.add("open");
      document.getElementById("dTitle").innerText = node.label.split("\\n")[0].trim();
      document.getElementById("dType").innerText = node.type + " \u00b7 " + node.group;
      document.getElementById("dSummary").innerText = node.summary || "No summary available.";

      const actionCard = document.getElementById("drawerActionCard");
      const actionBtn = document.getElementById("drawerActionBtn");
      if (node.type === "DischargeNode" && (node.label.includes("HOLD") || node.properties.is_blocked === "True")) {{
        actionCard.style.display = "block";
        actionBtn.innerText = "Clear Billing Hold & Issue Gate Pass";
        actionBtn.className = "btn btn-settle";
        actionBtn.onclick = () => triggerAction('settle_billing');
      }} else if (node.type === "LabPanicAlertNode" && node.properties.readback_status !== "Acknowledged") {{
        actionCard.style.display = "block";
        actionBtn.innerText = "Acknowledge Readback & Clear SLA";
        actionBtn.className = "btn btn-panic";
        actionBtn.onclick = () => triggerAction('resolve_panic');
      }} else if (node.type === "BedNode" && node.properties.status === "dirty") {{
        actionCard.style.display = "block";
        actionBtn.innerText = "Mark Bed Sanitized & Ready";
        actionBtn.className = "btn btn-turnaround";
        actionBtn.onclick = () => triggerAction('turnaround_bed');
      }} else {{
        actionCard.style.display = "none";
      }}

      const propsTable = document.getElementById("dProps");
      propsTable.innerHTML = "";
      for (const [k, v] of Object.entries(node.properties || {{}})) {{
        if (typeof v === 'object' && v !== null) continue;
        const row = document.createElement("tr");
        row.innerHTML = `<td class="k">${{k}}</td><td class="v">${{v}}</td>`;
        propsTable.appendChild(row);
      }}
    }}

    function closeDrawer() {{ document.getElementById("sideDrawer").classList.remove("open"); }}

    function resetZoom() {{
      if (network) network.fit({{ animation: {{ duration: 600, easingFunction: 'easeInOutQuad' }} }});
    }}

    function zoomIn() {{
      if (network) {{
        const scale = network.getScale() * 1.3;
        network.moveTo({{ scale, animation: {{ duration: 250 }} }});
      }}
    }}

    function zoomOut() {{
      if (network) {{
        const scale = network.getScale() * 0.77;
        network.moveTo({{ scale, animation: {{ duration: 250 }} }});
      }}
    }}

    function togglePhysics() {{
      physicsFrozen = !physicsFrozen;
      if (network) {{
        network.setOptions({{ physics: !physicsFrozen }});
        document.getElementById("freezeBtn").innerText = physicsFrozen ? "Resume" : "Freeze";
      }}
    }}

    function focusBottlenecks() {{
      const blockerNode = currentNodes.find(n => n.label.includes("HOLD") || n.label.includes("CRITICAL") || n.label.includes("DENIED"));
      if (blockerNode && network) {{
        network.focus(blockerNode.id, {{ scale: 1.35, animation: {{ duration: 700 }} }});
        showDrawer(blockerNode);
      }}
    }}

    function handleSearch(term) {{
      if (!term || term.trim() === "" || !network) return;
      const q = term.toLowerCase().trim();
      const match = currentNodes.find(n => n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q) || (n.summary && n.summary.toLowerCase().includes(q)));
      if (match) {{
        network.focus(match.id, {{ scale: 1.35, animation: {{ duration: 500 }} }});
        showDrawer(match);
      }}
    }}

    function filterLegend(groupName) {{
      const match = currentNodes.find(n => n.group === groupName);
      if (match && network) {{
        network.focus(match.id, {{ scale: 1.25, animation: {{ duration: 600 }} }});
        showDrawer(match);
      }}
    }}

    window.addEventListener('DOMContentLoaded', () => {{
      renderNetwork(currentNodes, currentEdges);
      document.getElementById('viewingCount').innerText = currentNodes.length + ' / ' + document.getElementById('totalNodes').innerText;
    }});

    // ── Governed Agent Panel ──
    function toggleAgentPanel() {{
      document.getElementById('agentPanel').classList.toggle('open');
    }}

    // Conversation memory — persists for the lifetime of this browser session
    const agentHistory = [];

    async function sendAgentQuery() {{
      const input = document.getElementById('agentInput');
      const query = input.value.trim();
      if (!query) return;

      const messages = document.getElementById('agentMessages');

      const userMsg = document.createElement('div');
      userMsg.className = 'agent-message agent-msg-user';
      userMsg.innerText = query;
      messages.appendChild(userMsg);
      input.value = '';

      const loadingMsg = document.createElement('div');
      loadingMsg.className = 'agent-message agent-msg-system';
      loadingMsg.innerText = 'Traversing operational graph…';
      messages.appendChild(loadingMsg);
      messages.scrollTop = messages.scrollHeight;

      // Record user turn before sending
      agentHistory.push({{ role: 'user', content: query }});

      try {{
        const res = await fetch('/api/v1/agent/query', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ query, conversation_history: agentHistory.slice(-6) }})
        }});
        const data = await res.json();
        messages.removeChild(loadingMsg);

        // Surface API errors explicitly
        if (!res.ok || data.detail) {{
          const errDiv = document.createElement('div');
          errDiv.className = 'agent-message agent-msg-guardrail';
          errDiv.innerText = 'Agent error: ' + (data.detail || 'HTTP ' + res.status);
          messages.appendChild(errDiv);
          agentHistory.pop(); // remove failed user turn
          messages.scrollTop = messages.scrollHeight;
          return;
        }}

        const answerText = data.answer || JSON.stringify(data);
        // Record assistant turn in history
        agentHistory.push({{ role: 'assistant', content: answerText }});

        const answerDiv = document.createElement('div');

        if (data.guardrail_triggered) {{
          answerDiv.className = 'agent-message agent-msg-guardrail';
          // Confidence badge for guardrails
          if (data.confidence) {{
            const lvl = (data.confidence.level || 'uncertain').toLowerCase();
            const badge = document.createElement('span');
            badge.className = 'confidence-badge conf-' + lvl;
            badge.innerText = lvl.toUpperCase();
            answerDiv.appendChild(badge);
            answerDiv.appendChild(document.createElement('br'));
          }}
          const title = document.createElement('b');
          title.innerText = data.guardrail_triggered.replace(/_/g, ' ');
          answerDiv.appendChild(title);
          answerDiv.appendChild(document.createElement('br'));
          answerDiv.appendChild(document.createTextNode(data.answer || ''));
          if (data.escalation) {{
            const esc = document.createElement('div');
            esc.className = 'agent-msg-escalation';
            esc.innerText = 'Route to: ' + data.escalation;
            answerDiv.appendChild(esc);
          }}
          if (data.escalation_reason) {{
            const er = document.createElement('div');
            er.className = 'escalation-reason';
            er.innerText = 'Why: ' + data.escalation_reason;
            answerDiv.appendChild(er);
          }}
          if (data.requires_human_approval) {{
            const appr = document.createElement('div');
            appr.className = 'agent-msg-escalation';
            appr.innerText = '⚠ Requires supervisor approval before action';
            answerDiv.appendChild(appr);
          }}
        }} else {{
          answerDiv.className = 'agent-message agent-msg-answer';

          // Confidence badge — requirement 3
          if (data.confidence) {{
            const lvl = (data.confidence.level || 'uncertain').toLowerCase();
            const badge = document.createElement('span');
            badge.className = 'confidence-badge conf-' + lvl;
            badge.innerText = lvl.toUpperCase();
            if (data.confidence.reason) badge.title = data.confidence.reason;
            answerDiv.appendChild(badge);
            answerDiv.appendChild(document.createElement('br'));
          }}

          // Answer text
          const answerPara = document.createElement('div');
          answerPara.style.whiteSpace = 'pre-wrap';
          answerPara.innerText = answerText;
          answerDiv.appendChild(answerPara);

          // Missing fields card — requirement 5
          if (data.missing_fields && data.missing_fields.missing_fields) {{
            const mfc = document.createElement('div');
            mfc.className = 'missing-fields-card';
            const mfTitle = document.createElement('div');
            mfTitle.className = 'mf-title';
            mfTitle.innerText = 'Missing Required Fields';
            mfc.appendChild(mfTitle);
            for (const [field, prompt] of Object.entries(data.missing_fields.missing_fields)) {{
              const item = document.createElement('div');
              item.className = 'mf-item';
              item.innerText = '• ' + prompt;
              mfc.appendChild(item);
            }}
            answerDiv.appendChild(mfc);
          }}

          // Workflow step card — requirement 4
          if (data.workflow_step) {{
            const wfc = document.createElement('div');
            wfc.className = 'workflow-step-card';
            const wfTitle = document.createElement('div');
            wfTitle.className = 'wf-title';
            wfTitle.innerText = 'Next Workflow Step (' + data.workflow_step.step + '/' + data.workflow_step.total_steps + ')';
            wfc.appendChild(wfTitle);
            const wfStep = document.createElement('div');
            wfStep.className = 'wf-step';
            wfStep.innerText = data.workflow_step.name;
            wfc.appendChild(wfStep);
            const wfDesc = document.createElement('div');
            wfDesc.className = 'wf-desc';
            wfDesc.innerText = data.workflow_step.description;
            wfc.appendChild(wfDesc);
            const wfTeam = document.createElement('div');
            wfTeam.className = 'wf-team';
            wfTeam.innerText = data.workflow_step.responsible_team + ' — ' + data.workflow_step.extension;
            wfc.appendChild(wfTeam);
            answerDiv.appendChild(wfc);
          }}

          // Source citations — requirement 2
          if (data.source_citations && data.source_citations.length > 0) {{
            const cit = document.createElement('div');
            cit.className = 'citations-block';
            const citTitle = document.createElement('div');
            citTitle.className = 'cit-title';
            citTitle.innerText = 'Sources';
            cit.appendChild(citTitle);
            data.source_citations.slice(0, 5).forEach(function(c) {{
              const ci = document.createElement('div');
              ci.className = 'cit-item';
              ci.innerText = c.type + ' · ' + c.id + (c.section ? ' · ' + c.section : '');
              cit.appendChild(ci);
            }});
            answerDiv.appendChild(cit);
          }}

          if (data.requires_human_approval) {{
            const flag = document.createElement('div');
            flag.className = 'agent-msg-escalation';
            flag.innerText = '⚠ Requires supervisor approval';
            answerDiv.appendChild(flag);
          }}
        }}
        messages.appendChild(answerDiv);
      }} catch (err) {{
        messages.removeChild(loadingMsg);
        const errDiv = document.createElement('div');
        errDiv.className = 'agent-message agent-msg-guardrail';
        errDiv.innerText = 'Agent error: ' + err.message;
        messages.appendChild(errDiv);
        agentHistory.pop(); // remove failed user turn
      }}
      messages.scrollTop = messages.scrollHeight;
    }}
  </script>
</body>
</html>"""
        return html_template

    def export_visual_graph(self, nodes: Optional[List[Any]] = None, edges: Optional[List[Tuple]] = None, output_path: Optional[Path] = None):
        """Exports the Acentra Operations Command Center to standalone HTML."""
        target_path = output_path or HTML_OUTPUT_PATH
        content = self.generate_command_center_html(initial_perspective="bottlenecks")
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  [OK] Exported Operations Command Center Graph to: {target_path}")



# Singleton accessor
_service_instance: Optional[OntologyGraphService] = None

def get_ontology_graph_service() -> OntologyGraphService:
    global _service_instance
    if _service_instance is None:
        _service_instance = OntologyGraphService()
    return _service_instance
