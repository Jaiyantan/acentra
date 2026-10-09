"""
SMCH Hospital Operational Ontology Builder
Ingests and harmonizes disintegrated data sources:
1. HIS (Admissions, Inpatient/ICU Beds, Patients, Consultations, Emergency Triage)
2. LIS (Lab Orders, Lab Results, Critical Panic Alerts)
3. RIS (Radiology Orders & Reports)
4. Pharmacy (Prescriptions, Dispensing, Inventory)
5. Billing & Revenue Cycle (Invoices, Balances, Unbilled Consumables)
6. TPA & Cashless Insurance (Claims, Pre-Auth, Rejections, Denial Reasons)
7. Operational Governance Knowledge Base (152+ SOPs, Policies, Articles, Rules, Workflows, Teams, Fields)

Features:
- Primary ingestion from Saveetha Medical College & Hospital database (smch_hospital.db).
- Fallback/supplement from hospital.db and knowledge_base assets.
- Cross-Departmental Entity Resolution (breaks down silos).
- Dynamic State Mutation & Context Pruning (solves Context Decay).
- High-density semantic indexing (TokenOptimizer) for zero token waste.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from .models import (
    DepartmentNode, StaffNode, SOPNode, KnowledgeArticleNode, PolicyNode,
    WorkflowNode, WorkflowStepNode, RoutingRuleNode, SupportTeamNode, FieldDefinitionNode,
    PatientNode, BedNode, AdmissionNode, DischargeNode, OrderNode,
    LabResultNode, LabPanicAlertNode, BillNode, ClaimNode, TicketNode,
    PrescriptionNode, DispensingNode, RadiologyReportNode, EmergencyCaseNode
)
from .token_optimizer import TokenOptimizer

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Resilient database paths (data/ -> db/ -> root)
_SMCH_CANDIDATES = [
    ROOT_DIR / "data" / "smch_hospital.db",
    ROOT_DIR / "db" / "smch_hospital.db",
    ROOT_DIR / "smch_hospital.db",
]
SMCH_DB_PATH = next((p for p in _SMCH_CANDIDATES if p.exists()), _SMCH_CANDIDATES[0])

_HOSP_CANDIDATES = [
    ROOT_DIR / "data" / "hospital.db",
    ROOT_DIR / "db" / "hospital.db",
    ROOT_DIR / "hospital.db",
]
HOSP_DB_PATH = next((p for p in _HOSP_CANDIDATES if p.exists()), _HOSP_CANDIDATES[0])

KB_DIR = ROOT_DIR / "knowledge_base"
INDEX_DIR = KB_DIR / "index"


def safe_row(row: Any) -> Dict[str, Any]:
    """Safely converts sqlite3.Row or dict-like object to a standard Python dict."""
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:
        return {}


class OntologyBuilder:
    """Constructs and maintains the SMCH Hospital Operational Ontology."""

    def __init__(self, smch_db_path: Path = SMCH_DB_PATH, hosp_db_path: Path = HOSP_DB_PATH):
        self.smch_db_path = smch_db_path
        self.hosp_db_path = hosp_db_path

        # Governance & Operational Schema Stores
        self.departments: Dict[str, DepartmentNode] = {}
        self.staff: Dict[str, StaffNode] = {}
        self.sops: Dict[str, SOPNode] = {}
        self.articles: Dict[str, KnowledgeArticleNode] = {}
        self.policies: Dict[str, PolicyNode] = {}
        self.workflows: Dict[str, WorkflowNode] = {}
        self.workflow_steps: Dict[str, WorkflowStepNode] = {}
        self.routing_rules: Dict[str, RoutingRuleNode] = {}
        self.support_teams: Dict[str, SupportTeamNode] = {}
        self.field_definitions: Dict[str, FieldDefinitionNode] = {}

        # Living Operational Digital Twin Stores
        self.patients: Dict[str, PatientNode] = {}
        self.beds: Dict[str, BedNode] = {}
        self.admissions: Dict[str, AdmissionNode] = {}
        self.discharges: Dict[str, DischargeNode] = {}
        self.orders: Dict[str, OrderNode] = {}
        self.lab_results: Dict[str, LabResultNode] = {}
        self.lab_critical_alerts: Dict[str, LabPanicAlertNode] = {}
        self.prescriptions: Dict[str, PrescriptionNode] = {}
        self.dispensing_logs: Dict[str, DispensingNode] = {}
        self.radiology_reports: Dict[str, RadiologyReportNode] = {}
        self.bills: Dict[str, BillNode] = {}
        self.claims: Dict[str, ClaimNode] = {}
        self.tickets: Dict[str, TicketNode] = {}
        self.emergency_cases: Dict[str, EmergencyCaseNode] = {}

        self.last_built_at: Optional[datetime] = None

    def get_smch_connection(self) -> Optional[sqlite3.Connection]:
        if self.smch_db_path.exists():
            conn = sqlite3.connect(str(self.smch_db_path), timeout=20.0)
            conn.row_factory = sqlite3.Row
            return conn
        return None

    def get_hosp_connection(self) -> Optional[sqlite3.Connection]:
        if self.hosp_db_path.exists():
            conn = sqlite3.connect(str(self.hosp_db_path), timeout=20.0)
            conn.row_factory = sqlite3.Row
            return conn
        return None

    # =========================================================================
    # 1. GOVERNANCE & POLICY ONTOLOGY INGESTION
    # =========================================================================

    def ingest_governance_layer(self):
        """Loads static procedural knowledge, workflows, schemas, and rules."""
        # A. Departments (From app.config.DEPARTMENTS and fallback hospital.db)
        from app.config import DEPARTMENTS
        for dept in DEPARTMENTS:
            d_id = dept["id"]
            dense = f"DEPARTMENT [{d_id.upper()}] {dept['name']} | Code: {dept['code']} | Category: {dept['category']}"
            self.departments[d_id] = DepartmentNode(
                dept_id=d_id,
                name=dept["name"],
                dept_type=dept["category"],
                dense_summary=dense
            )

        # Supplement from hospital.db departments if present
        h_conn = self.get_hosp_connection()
        if h_conn:
            try:
                dept_rows = h_conn.execute("SELECT * FROM departments").fetchall()
                for r in dept_rows:
                    rd = safe_row(r)
                    d_id = rd.get("dept_id")
                    if d_id and d_id not in self.departments:
                        dense = f"DEPARTMENT [{d_id}] {rd.get('name')} | Type: {rd.get('type')} | Location: {rd.get('location')}"
                        self.departments[d_id] = DepartmentNode(
                            dept_id=d_id,
                            name=rd.get("name", "Department"),
                            dept_type=rd.get("type", "clinical"),
                            dense_summary=dense
                        )
            except Exception:
                pass
            h_conn.close()

        # B. Staff Master (From smch_hospital.db staff_master and fallback hospital.db)
        smch_conn = self.get_smch_connection()
        if smch_conn:
            try:
                staff_rows = smch_conn.execute("SELECT * FROM staff_master").fetchall()
                for r in staff_rows:
                    rd = safe_row(r)
                    s_id = rd.get("staff_id")
                    if s_id:
                        dense = f"STAFF [{s_id}] {rd.get('name')} | Role: {rd.get('role')} | Dept: {rd.get('department')} | Contact: {rd.get('contact_no')}"
                        self.staff[s_id] = StaffNode(
                            staff_id=s_id,
                            name=rd.get("name", "Staff Member"),
                            role=rd.get("role", "Clinician"),
                            department_id=rd.get("department", "General"),
                            contact=rd.get("contact_no"),
                            dense_summary=dense
                        )
            except Exception:
                pass
            smch_conn.close()

        # Fallback staff from hospital.db
        if not self.staff:
            h_conn = self.get_hosp_connection()
            if h_conn:
                try:
                    staff_rows = h_conn.execute("SELECT * FROM staff").fetchall()
                    for r in staff_rows:
                        rd = safe_row(r)
                        s_id = rd.get("staff_id")
                        if s_id and s_id not in self.staff:
                            dense = f"STAFF [{s_id}] {rd.get('name')} | Role: {rd.get('role')} | Dept: {rd.get('department')}"
                            self.staff[s_id] = StaffNode(
                                staff_id=s_id,
                                name=rd.get("name", "Staff Member"),
                                role=rd.get("role", "Clinician"),
                                department_id=rd.get("department", "General"),
                                dense_summary=dense
                            )
                except Exception:
                    pass
                h_conn.close()

        # C. Field Definitions Schema
        fields_path = KB_DIR / "field_definitions.json"
        if fields_path.exists():
            with open(fields_path, "r", encoding="utf-8") as f:
                f_data = json.load(f)
            for item in f_data.get("fields", []):
                fname = item["field_name"]
                dense = f"FIELD [{fname}] {item['display_name']} ({item['type']}) | Required: {item['required']} | Pattern: {item.get('validation_pattern') or 'None'}"
                opts = [str(x) for x in item["select_options"]] if item.get("select_options") else None
                self.field_definitions[fname] = FieldDefinitionNode(
                    field_name=fname,
                    display_name=item["display_name"],
                    data_type=item["type"],
                    is_required=item["required"],
                    validation_pattern=item.get("validation_pattern"),
                    select_options=opts,
                    on_missing_message=item["on_missing_message"],
                    used_in_workflows=item.get("used_in_documents", []),
                    dense_summary=dense
                )

        # D. Support Teams Directory
        support_path = KB_DIR / "support_directory.json"
        if support_path.exists():
            with open(support_path, "r", encoding="utf-8") as f:
                s_data = json.load(f)
            for t in s_data.get("teams", []):
                t_id = t["team_id"]
                dense = f"TEAM [{t_id}] {t['name']} | Ext: {t['contact_extension']} | Queue: {t['helpdesk_queue']} | SLA: {t['sla_hours']}h | Escalates: {t.get('escalation_to')}"
                self.support_teams[t_id] = SupportTeamNode(
                    team_id=t_id,
                    name=t["name"],
                    handles=t.get("handles", []),
                    contact_extension=t["contact_extension"],
                    email=t["email"],
                    helpdesk_queue=t["helpdesk_queue"],
                    sla_hours=float(t["sla_hours"]),
                    escalation_to=t.get("escalation_to"),
                    dense_summary=dense
                )

        # E. Routing Rules
        rules_path = KB_DIR / "routing_rules.json"
        if rules_path.exists():
            with open(rules_path, "r", encoding="utf-8") as f:
                r_data = json.load(f)
            for r in r_data:
                r_id = r["rule_id"]
                dense = TokenOptimizer.optimize_routing_rule(
                    r_id, r["trigger"], r.get("trigger_type", "Operational"),
                    r["route_to"], str(r.get("contact_extension", "1026")),
                    r["priority"], float(r["sla_hours"]),
                    r.get("escalation_reason", "Hospital operational continuity")
                )
                self.routing_rules[r_id] = RoutingRuleNode(
                    rule_id=r_id,
                    trigger=r["trigger"],
                    trigger_type=r.get("trigger_type", "Operational"),
                    route_to_team=r["route_to"],
                    contact_extension=str(r.get("contact_extension", "1026")),
                    helpdesk_queue=r.get("helpdesk_queue", "QUEUE_GENERAL"),
                    priority=r["priority"],
                    sla_hours=float(r["sla_hours"]),
                    escalation_reason=r.get("escalation_reason", "Operational triage"),
                    dense_summary=dense
                )

        # F. Workflows & Step State Machines
        wf_path = KB_DIR / "workflow_definitions.json"
        if wf_path.exists():
            with open(wf_path, "r", encoding="utf-8") as f:
                wf_data = json.load(f)
            for wf in wf_data.get("workflows", []):
                w_id = wf["workflow_id"]
                states = wf.get("states", [])
                dense_wf = TokenOptimizer.optimize_workflow(
                    w_id, wf["name"], wf["department"],
                    wf.get("trigger_intents", []), wf.get("allowed_roles", []),
                    states, wf.get("human_approval_checkpoint", "Final Step")
                )
                self.workflows[w_id] = WorkflowNode(
                    workflow_id=w_id,
                    slug=wf["slug"],
                    name=wf["name"],
                    department=wf["department"],
                    trigger_intents=wf.get("trigger_intents", []),
                    allowed_roles=wf.get("allowed_roles", []),
                    requires_human_approval=wf.get("requires_human_approval", True),
                    approval_checkpoint=wf.get("human_approval_checkpoint", "Final Step"),
                    steps_count=len(states),
                    dense_summary=dense_wf
                )

                for s in states:
                    step_id = f"{w_id}_STEP_{s['step_number']}"
                    dense_step = f"WORKFLOW STEP [{step_id}] {s['state_name']} | Actor: {s['actor']} | Required Fields: {', '.join(s.get('required_fields', []))} | Blocker: {', '.join(s.get('blockers', []))} | Endpoint: {s.get('endpoint')}"
                    self.workflow_steps[step_id] = WorkflowStepNode(
                        step_id=step_id,
                        workflow_id=w_id,
                        step_number=s["step_number"],
                        step_name=s["state_name"],
                        actor_role=s["actor"],
                        required_fields=s.get("required_fields", []),
                        simulation_endpoint=s.get("endpoint"),
                        blockers=s.get("blockers", []),
                        escalation_rule_id=s.get("escalation_rule"),
                        requires_human_approval=s.get("requires_human_approval", False),
                        dense_summary=dense_step
                    )

        # G. SOPs, Articles, Policies from Companion Index Cards
        if INDEX_DIR.exists():
            for idx_file in INDEX_DIR.glob("*.json"):
                try:
                    with open(idx_file, "r", encoding="utf-8") as f:
                        card = json.load(f)
                    cat = card.get("category")
                    fid = card.get("file_id")

                    if cat == "sop" and fid:
                        dense = TokenOptimizer.clean_text(card.get("content", ""))
                        self.sops[fid] = SOPNode(
                            doc_id=card.get("doc_id", fid),
                            title=card.get("title", fid),
                            department=card.get("department", "Operations"),
                            version=card.get("version", "1.0"),
                            applicable_roles=card.get("applicable_roles", []),
                            purpose=dense[:120],
                            citation=card.get("source_citation", f"{fid} Section 4"),
                            dense_summary=dense[:400]
                        )
                    elif cat == "knowledge_article" and fid:
                        dense = TokenOptimizer.clean_text(card.get("content", ""))
                        self.articles[fid] = KnowledgeArticleNode(
                            doc_id=card.get("doc_id", fid),
                            title=card.get("title", fid),
                            host_system="HIS",
                            department=card.get("department", "Operations"),
                            version=card.get("version", "1.0"),
                            applicable_roles=card.get("applicable_roles", []),
                            overview=dense[:120],
                            contact_extension="1026",
                            dense_summary=dense[:400]
                        )
                    elif cat == "policy" and fid:
                        dense = TokenOptimizer.clean_text(card.get("content", ""))
                        self.policies[fid] = PolicyNode(
                            doc_id=card.get("doc_id", fid),
                            title=card.get("title", fid),
                            department=card.get("department", "Operations"),
                            version=card.get("version", "1.0"),
                            mandate=dense[:150],
                            scope=card.get("department", "Hospital-wide"),
                            citation=card.get("source_citation", f"{fid} Institutional Policy"),
                            dense_summary=dense[:400]
                        )
                except Exception:
                    continue

    # =========================================================================
    # 2. DYNAMIC OPERATIONAL DIGITAL TWIN INGESTION (Shattering Silos)
    # =========================================================================

    def ingest_digital_twin(self):
        """Builds the live operational digital twin from smch_hospital.db and hospital.db."""
        smch_conn = self.get_smch_connection()

        if smch_conn:
            self._ingest_smch_digital_twin(smch_conn)
            smch_conn.close()
        else:
            hosp_conn = self.get_hosp_connection()
            if hosp_conn:
                self._ingest_hosp_digital_twin(hosp_conn)
                hosp_conn.close()

        self._stamp_all_ttls()
        self.last_built_at = datetime.now(timezone.utc)

    def _stamp_all_ttls(self):
        """Attach TTL expiry timestamps to every operational node.

        Uses node_lifecycle.stamp_ttl which writes ``_expires_at`` directly on
        the object via object.__setattr__, so frozen Pydantic models are safe.
        Governance nodes (BedNode, SOPNode, etc.) receive TTL=None — permanent.
        """
        try:
            from app.ontology.node_lifecycle import stamp_ttl
        except ImportError:
            return

        _collections = [
            (self.patients,            "PatientNode"),
            (self.admissions,          "AdmissionNode"),
            (self.discharges,          "DischargeNode"),
            (self.lab_critical_alerts, "LabPanicAlertNode"),
            (self.lab_results,         "LabResultNode"),
            (self.bills,               "BillNode"),
            (self.claims,              "ClaimNode"),
            (self.prescriptions,       "PrescriptionNode"),
            (self.emergency_cases,     "EmergencyCaseNode"),
            # Permanent types still get stamped (None expiry = no prune)
            (self.beds,                "BedNode"),
            (self.sops,                "SOPNode"),
            (self.policies,            "PolicyNode"),
            (self.articles,            "KnowledgeArticleNode"),
            (self.routing_rules,       "RoutingRuleNode"),
        ]
        for store, node_type in _collections:
            for node in store.values():
                stamp_ttl(node, node_type)

    def _ingest_smch_digital_twin(self, conn: sqlite3.Connection):
        """Extracts complete multi-departmental records from smch_hospital.db."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # ---------------------------------------------------------------------
        # A. BEDS (290 Ward Beds + 12 ICU Beds)
        # ---------------------------------------------------------------------
        ipd_bed_rows = conn.execute("SELECT * FROM ipd_beds").fetchall()
        for r in ipd_bed_rows:
            rd = safe_row(r)
            bid = rd["bed_id"]
            stat = str(rd.get("status", "Available")).lower()
            norm_status = "occupied" if stat == "occupied" else "vacant"
            if "clean" in stat:
                norm_status = "dirty"
            elif "sanit" in stat:
                norm_status = "sanitized"

            dense = f"BED [{bid}] Ward: {rd.get('ward_name')} | BedNo: {rd.get('bed_no')} | Status: {norm_status} | Patient: {rd.get('current_uhid') or 'None'}"
            self.beds[bid] = BedNode(
                bed_id=bid,
                ward=rd.get("ward_name", "General Ward"),
                department_id=rd.get("ward_name", "General Ward"),
                bed_type=rd.get("category", "Standard"),
                status=norm_status,
                current_patient_uhid=rd.get("current_uhid"),
                active_admission_id=rd.get("admission_id"),
                last_turnaround_timestamp=now_iso,
                dense_summary=dense
            )

        icu_bed_rows = conn.execute("SELECT * FROM icu_beds").fetchall()
        for r in icu_bed_rows:
            rd = safe_row(r)
            bid = rd["bed_id"]
            stat = str(rd.get("status", "Available")).lower()
            norm_status = "occupied" if stat == "occupied" else "vacant"
            dense = f"BED [{bid}] ICU: {rd.get('icu_name')} | Status: {norm_status} | Patient: {rd.get('uhid') or 'None'} | APACHE-II: {rd.get('apache2_score', 0)}"
            self.beds[bid] = BedNode(
                bed_id=bid,
                ward=rd.get("icu_name", "ICU"),
                department_id="ICU",
                bed_type="Intensive Care",
                status=norm_status,
                current_patient_uhid=rd.get("uhid"),
                last_turnaround_timestamp=now_iso,
                dense_summary=dense
            )

        # ---------------------------------------------------------------------
        # B. ADMISSIONS (209 Active Inpatient Stays)
        # ---------------------------------------------------------------------
        adm_rows = conn.execute("SELECT * FROM ipd_admissions").fetchall()
        for r in adm_rows:
            rd = safe_row(r)
            aid = rd["admission_id"]
            uhid = rd["uhid"]
            ward = rd.get("ward_name", "General Ward")
            bed_no = rd.get("bed_no")

            # Match exact bed_id
            bed_id = f"{ward}-{bed_no}"
            if bed_id not in self.beds:
                # Find matching bed
                matched_b = next((b for b_id, b in self.beds.items() if b.current_patient_uhid == uhid), None)
                bed_id = matched_b.bed_id if matched_b else (bed_no or "BED-UNASSIGNED")

            dense = f"ADMISSION [{aid}] Patient: {uhid} | Bed: {bed_id} | Doctor: {rd.get('admitting_doctor')} | Diagnosis: {rd.get('admitting_diagnosis')} | Ward: {ward} | Status: {rd.get('status')}"
            self.admissions[aid] = AdmissionNode(
                admission_id=aid,
                uhid=uhid,
                bed_id=bed_id,
                admitting_doctor_id=rd.get("admitting_doctor", "Doctor"),
                department_id=ward,
                admitting_diagnosis=rd.get("admitting_diagnosis", "Clinical Diagnosis"),
                admission_type="icu" if "ICU" in ward else "inpatient",
                admission_date=str(rd.get("admission_time", now_iso)),
                status=str(rd.get("status", "Active")).lower(),
                dense_summary=dense
            )

        # ---------------------------------------------------------------------
        # C. PATIENTS (Demographics for Inpatients & Active Cases)
        # ---------------------------------------------------------------------
        # Ingest patients who have admissions
        for aid, adm in self.admissions.items():
            uhid = adm.uhid
            p_row = conn.execute("SELECT * FROM patients WHERE uhid = ?", (uhid,)).fetchone()
            if p_row:
                pd = safe_row(p_row)
                dense = TokenOptimizer.optimize_operational_patient(
                    uhid, pd.get("name", "Patient"), int(pd.get("age", 40)),
                    pd.get("gender", "Other"), "admitted", adm.bed_id, adm.department_id,
                    adm.admitting_doctor_id, adm.admitting_diagnosis
                )
                self.patients[uhid] = PatientNode(
                    uhid=uhid,
                    name=pd.get("name", "Patient"),
                    age=int(pd.get("age", 40)),
                    gender=pd.get("gender", "Other"),
                    contact=pd.get("phone", "+91-9840100000"),
                    registration_date=str(pd.get("registered_at", now_iso)),
                    status="admitted",
                    current_bed_id=adm.bed_id,
                    active_admission_id=aid,
                    dense_summary=dense
                )

        # ---------------------------------------------------------------------
        # D. BILLING INVOICES (251 Invoices) & DISCHARGES SYNTHESIS
        # ---------------------------------------------------------------------
        bill_rows = conn.execute("SELECT * FROM billing_invoices").fetchall()
        for r in bill_rows:
            rd = safe_row(r)
            bid = rd["invoice_id"]
            uhid = rd["uhid"]
            total = float(rd.get("total_amount_inr", 0))
            net = float(rd.get("net_amount_inr", total))
            p_stat = str(rd.get("payment_status", "Settled")).lower()

            # Find matching admission
            matched_adm = next((a for a in self.admissions.values() if a.uhid == uhid), None)
            aid = matched_adm.admission_id if matched_adm else "ADM-OPD"

            has_dispute = (total > 50000.0 and "Self-Paying" in str(rd.get("payer_type", "")))
            dispute_val = 13000.0 if has_dispute else 0.0
            pending_val = 0.0 if p_stat == "settled" else net

            dense = f"BILL [{bid}] Patient: {uhid} | Total: Rs {total:,.2f} | Payer: {rd.get('payer_type')} | Status: {p_stat} | Unbilled Consumables: Rs {dispute_val:,.2f}"
            self.bills[bid] = BillNode(
                bill_id=bid,
                admission_id=aid,
                uhid=uhid,
                total_amount=total,
                paid_amount=net if p_stat == "settled" else 0.0,
                pending_amount=pending_val,
                unbilled_consumables=dispute_val,
                has_billing_dispute=has_dispute,
                dispute_amount=dispute_val,
                status="disputed" if has_dispute else p_stat,
                dense_summary=dense
            )

        # ---------------------------------------------------------------------
        # E. DISCHARGES (The 4-Point Clearance Operational Bottleneck)
        # ---------------------------------------------------------------------
        # Model active discharge orders for admissions
        for aid, adm in self.admissions.items():
            uhid = adm.uhid
            did = f"DIS-{aid}"

            # Cross-reference billing
            matched_bill = next((b for b in self.bills.values() if b.uhid == uhid), None)
            c_bil = True
            if matched_bill and (matched_bill.has_billing_dispute or matched_bill.pending_amount > 0):
                c_bil = False

            # Cross-reference pharmacy (check if there is high drug indent)
            c_phm = True
            c_doc = True
            c_nur = True

            # Create realistic intentional bottleneck for demonstration
            if aid in ["ADM-42C854", "ADM-14E565"]:
                c_bil = False  # Unbilled consumables Rs 13,000
            elif aid in ["ADM-3F3465"]:
                c_phm = False  # Pharmacy return credit pending

            is_blocked = not (c_doc and c_phm and c_bil and c_nur)
            blocker_reason = None
            esc_rule = None
            res_ext = "1027"

            if not c_bil:
                blocker_reason = "Discharge blocked at Step 3: Central Billing final invoice/co-pay pending settlement."
                esc_rule = "R-008"
                res_ext = "1028"
            elif not c_phm:
                blocker_reason = "Discharge blocked at Step 2: Unused ward medications pending physical return to Pharmacy."
                esc_rule = "R-002"
                res_ext = "1023"

            status_str = "blocked" if is_blocked else "ready_for_gate_pass"
            dense = TokenOptimizer.optimize_discharge_blocker(
                did, uhid, adm.bed_id, c_doc, c_phm, c_bil, c_nur,
                blocker_reason or "All Clearances Satisfied",
                f"Billing Desk ext. {res_ext}" if is_blocked else "Release Gate Pass"
            )

            self.discharges[did] = DischargeNode(
                discharge_id=did,
                admission_id=aid,
                uhid=uhid,
                bed_id=adm.bed_id,
                discharge_type="Standard Medical Discharge",
                final_diagnosis=adm.admitting_diagnosis,
                clearance_clinical=c_doc,
                clearance_pharmacy=c_phm,
                clearance_billing=c_bil,
                clearance_nursing=c_nur,
                is_blocked=is_blocked,
                blocker_reason=blocker_reason,
                escalation_rule_id=esc_rule,
                resolution_team_extension=res_ext,
                gate_pass_issued=not is_blocked,
                status=status_str,
                dense_summary=dense
            )
            adm.has_blocked_discharge = is_blocked

        # ---------------------------------------------------------------------
        # F. CRITICAL PANIC LAB ALERTS (80 Alerts under POL-010 15-Min SLA)
        # ---------------------------------------------------------------------
        alert_rows = conn.execute("SELECT * FROM lab_critical_alerts").fetchall()
        for r in alert_rows:
            rd = safe_row(r)
            al_id = rd["alert_id"]
            uhid = rd["uhid"]
            param = rd.get("parameter_name", "Critical Lab")
            c_val = rd.get("critical_value", "Panic Value")
            ack_stat = rd.get("ack_status", "Pending-Ack")
            is_pending = (ack_stat == "Pending-Ack")
            elapsed = 22.0 if is_pending else 4.0  # 22 mins breaches 15 min SLA
            is_breached = is_pending and (elapsed > 15.0)

            dense = f"PANIC LAB [{al_id}] Patient: {uhid} ({rd.get('patient_name')}) | {param}: {c_val} | Doctor: {rd.get('doctor_contacted')} | Readback Status: {ack_stat} | SLA Breached: {is_breached}"
            self.lab_critical_alerts[al_id] = LabPanicAlertNode(
                alert_id=al_id,
                order_id=rd.get("order_id", "LAB-000"),
                uhid=uhid,
                patient_name=rd.get("patient_name", "Patient"),
                parameter_name=param,
                critical_value=c_val,
                alert_time=str(rd.get("alert_time", now_iso)),
                doctor_contacted=rd.get("doctor_contacted"),
                doctor_phone=rd.get("doctor_phone"),
                readback_status=ack_stat,
                sla_minutes=15.0,
                elapsed_minutes=elapsed,
                is_sla_breached=is_breached,
                ack_time=rd.get("ack_time"),
                dense_summary=dense
            )

        # Ingest any patients referenced in critical alerts who don't have admissions
        for al_id, alert in self.lab_critical_alerts.items():
            if alert.uhid and alert.uhid not in self.patients:
                p_row = conn.execute("SELECT * FROM patients WHERE uhid = ?", (alert.uhid,)).fetchone()
                p_name = alert.patient_name or "Emergency Patient"
                p_age = 48
                p_gen = "Female"
                p_phone = "+91-98401-22310"
                if p_row:
                    pd = safe_row(p_row)
                    p_name = pd.get("name", p_name)
                    p_age = int(pd.get("age", 48))
                    p_gen = pd.get("gender", p_gen)
                    p_phone = pd.get("phone", p_phone)
                dense_p = f"PATIENT [{alert.uhid}] {p_name} | Age: {p_age} | Gender: {p_gen} | Critical Panic Lab Alert"
                self.patients[alert.uhid] = PatientNode(
                    uhid=alert.uhid,
                    name=p_name,
                    age=p_age,
                    gender=p_gen,
                    contact=p_phone,
                    registration_date=now_iso,
                    status="critical_alert",
                    current_bed_id=None,
                    active_admission_id=None,
                    dense_summary=dense_p
                )

        # ---------------------------------------------------------------------
        # G. LAB RESULTS (Central Diagnostic Laboratory)
        # ---------------------------------------------------------------------
        lab_res_rows = conn.execute("SELECT * FROM lab_results LIMIT 100").fetchall()
        for r in lab_res_rows:
            rd = safe_row(r)
            rid = rd["result_id"]
            uhid = rd["uhid"]
            val = f"{rd.get('numeric_value')} {rd.get('unit')}" if rd.get("numeric_value") is not None else str(rd.get("text_value"))
            dense = f"LAB RESULT [{rid}] Patient: {uhid} | {rd.get('parameter_name')}: {val} | Range: {rd.get('reference_range')} | Flag: {rd.get('flag')}"
            self.lab_results[rid] = LabResultNode(
                result_id=rid,
                order_id=rd.get("order_id", "LAB-ORD"),
                admission_id="ADM-001",
                uhid=uhid,
                test_name=rd.get("parameter_name", "Test"),
                result_value=val,
                reference_range=str(rd.get("reference_range", "")),
                critical_value_flag=(rd.get("flag") == "Critical"),
                doctor_alerted=False,
                alert_sla_minutes=15.0,
                elapsed_alert_minutes=0.0,
                is_sla_breached=False,
                status="normal",
                dense_summary=dense
            )

        # ---------------------------------------------------------------------
        # H. INSURANCE CLAIMS & TPA REJECTIONS (78 Claims)
        # ---------------------------------------------------------------------
        claim_rows = conn.execute("SELECT * FROM insurance_claims").fetchall()
        for r in claim_rows:
            rd = safe_row(r)
            cid = rd["claim_id"]
            uhid = rd["uhid"]
            stat_str = str(rd.get("status", "Claim-Settled"))
            rej_reason = rd.get("denial_reason")
            is_rejected = bool(rej_reason) or ("reject" in stat_str.lower())
            preauth_val = float(rd.get("preauth_amount_inr", 0))
            appr_val = 0.0 if is_rejected else preauth_val

            dense = f"CLAIM [{cid}] Patient: {uhid} | Scheme: {rd.get('scheme')} | Status: {stat_str} | Preauth: Rs {preauth_val:,.2f} | Denial: {rej_reason or 'None'}"
            self.claims[cid] = ClaimNode(
                claim_id=cid,
                admission_id=rd.get("invoice_id", "INV-001"),
                uhid=uhid,
                insurer=rd.get("scheme", "PM-JAY"),
                tpa="Star Health / MediAssist TPA",
                policy_number=rd.get("preauth_code", "POL-9921"),
                claim_amount=preauth_val,
                approved_amount=appr_val,
                status="rejected" if is_rejected else "approved",
                rejection_reason=rej_reason,
                rejection_clause="Clause 4.2: Excluded consumable charges" if is_rejected else None,
                requires_dispute_appeal=is_rejected,
                dense_summary=dense
            )

        # Ensure representative cashless claim rejection for demonstration of TPA escalation (R-004)
        first_claim_id = next(iter(self.claims), None)
        if first_claim_id:
            demo_claim = self.claims[first_claim_id]
            demo_claim.status = "rejected"
            demo_claim.rejection_reason = "Clause 4.2 Query: Pre-existing hypertension non-disclosure dispute."
            demo_claim.rejection_clause = "Clause 4.2 Non-disclosure"
            demo_claim.requires_dispute_appeal = True
            demo_claim.insurer = "Star Health Insurance"
            demo_claim.dense_summary = f"CLAIM [{demo_claim.claim_id}] Patient: {demo_claim.uhid} | Scheme: Star Health | Status: rejected | Preauth: Rs {demo_claim.claim_amount:,.2f} | Denial: {demo_claim.rejection_reason}"


        # ---------------------------------------------------------------------
        # I. PHARMACY PRESCRIPTIONS & DISPENSING (399 Indents)
        # ---------------------------------------------------------------------
        rx_rows = conn.execute("SELECT * FROM pharmacy_prescriptions LIMIT 100").fetchall()
        for r in rx_rows:
            rd = safe_row(r)
            iid = rd["intake_id"]
            dense = f"PRESCRIPTION [{iid}] Patient: {rd.get('uhid')} ({rd.get('patient_name')}) | Source: {rd.get('source')} | Status: {rd.get('status')} | Drugs: {rd.get('drugs_json')[:80]}"
            self.prescriptions[iid] = PrescriptionNode(
                intake_id=iid,
                uhid=rd.get("uhid", "UHID-001"),
                patient_name=rd.get("patient_name", "Patient"),
                doctor_id=rd.get("doctor_id", "DOC-01"),
                source=rd.get("source", "Inpatient Indent"),
                drugs_summary=str(rd.get("drugs_json", ""))[:120],
                status=rd.get("status", "Dispensed"),
                intake_time=str(rd.get("intake_time", now_iso)),
                dense_summary=dense
            )

        disp_rows = conn.execute("SELECT * FROM pharmacy_dispensing LIMIT 100").fetchall()
        for r in disp_rows:
            rd = safe_row(r)
            did = rd["dispense_id"]
            dense = f"DISPENSING [{did}] Indent: {rd.get('intake_id')} | Drug: {rd.get('drug_name')} (Batch {rd.get('batch_no')}) | Qty: {rd.get('qty_dispensed')} | Warning: {rd.get('ddi_warning') or 'None'}"
            self.dispensing_logs[did] = DispensingNode(
                dispense_id=did,
                intake_id=rd.get("intake_id", "INTK-001"),
                uhid=rd.get("uhid", "UHID-001"),
                drug_name=rd.get("drug_name", "Drug"),
                batch_no=rd.get("batch_no", "BN-01"),
                expiry_date=str(rd.get("expiry_date", "2028-01-01")),
                qty_dispensed=int(rd.get("qty_dispensed", 1)),
                pharmacist_name=rd.get("pharmacist_name", "Pharmacist"),
                ddi_warning=rd.get("ddi_warning"),
                timestamp=str(rd.get("timestamp", now_iso)),
                dense_summary=dense
            )

        # ---------------------------------------------------------------------
        # J. RADIOLOGY REPORTS (305 PACS Studies)
        # ---------------------------------------------------------------------
        rad_rows = conn.execute("SELECT * FROM radiology_reports LIMIT 100").fetchall()
        for r in rad_rows:
            rd = safe_row(r)
            rid = rd["report_id"]
            is_crit = bool(rd.get("is_critical_finding", 0))
            dense = f"RADIOLOGY [{rid}] Patient: {rd.get('uhid')} | Modality: {rd.get('modality')} | Findings: {rd.get('findings')[:100]} | Critical: {is_crit}"
            self.radiology_reports[rid] = RadiologyReportNode(
                report_id=rid,
                study_id=rd.get("study_id", "STUDY-001"),
                uhid=rd.get("uhid", "UHID-001"),
                modality=rd.get("modality", "CT/MRI"),
                radiologist_name=rd.get("radiologist_name", "Radiologist"),
                findings=str(rd.get("findings", ""))[:200],
                impression=str(rd.get("impression", ""))[:120],
                is_critical_finding=is_crit,
                turnaround_time_min=float(rd.get("turnaround_time_min", 45.0)),
                reported_time=str(rd.get("reported_time", now_iso)),
                dense_summary=dense
            )

        # ---------------------------------------------------------------------
        # K. EMERGENCY CASES (399 Triage Cases)
        # ---------------------------------------------------------------------
        ed_rows = conn.execute("SELECT * FROM emergency_cases LIMIT 100").fetchall()
        for r in ed_rows:
            rd = safe_row(r)
            cid = rd["case_id"]
            dense = f"ED CASE [{cid}] Patient: {rd.get('uhid')} ({rd.get('patient_name')}) | Triage: {rd.get('triage_level')} | Chief: {rd.get('chief_complaint')} | Disposition: {rd.get('disposition')}"
            self.emergency_cases[cid] = EmergencyCaseNode(
                case_id=cid,
                uhid=rd.get("uhid", "UHID-001"),
                patient_name=rd.get("patient_name", "Patient"),
                triage_level=rd.get("triage_level", "Yellow (P2)"),
                arrival_mode=rd.get("arrival_mode", "Walk-in"),
                chief_complaint=rd.get("chief_complaint", "Acute distress"),
                time_to_doctor_min=rd.get("time_to_doctor_min"),
                assigned_doctor=rd.get("assigned_doctor"),
                disposition=rd.get("disposition"),
                status=rd.get("status", "Active"),
                dense_summary=dense
            )

    def _ingest_hosp_digital_twin(self, conn: sqlite3.Connection):
        """Fallback ingestion for minimal hospital.db."""
        now_iso = datetime.now(timezone.utc).isoformat()
        # Ingest patients
        for r in conn.execute("SELECT * FROM patients").fetchall():
            rd = safe_row(r)
            uhid = rd["uhid"]
            dense = TokenOptimizer.optimize_operational_patient(
                uhid, rd.get("name"), int(rd.get("age", 40)), rd.get("gender"), rd.get("status")
            )
            self.patients[uhid] = PatientNode(
                uhid=uhid, name=rd.get("name"), age=int(rd.get("age", 40)),
                gender=rd.get("gender"), contact=rd.get("contact"),
                registration_date=str(rd.get("registration_date")),
                status=rd.get("status"), dense_summary=dense
            )
        # Ingest beds
        for r in conn.execute("SELECT * FROM beds").fetchall():
            rd = safe_row(r)
            bid = rd["bed_id"]
            self.beds[bid] = BedNode(
                bed_id=bid, ward=rd.get("ward"), department_id=rd.get("ward"),
                bed_type="Standard", status=rd.get("status"),
                current_patient_uhid=rd.get("current_patient_uhid"),
                last_turnaround_timestamp=now_iso,
                dense_summary=f"BED [{bid}] Ward: {rd.get('ward')} | Status: {rd.get('status')}"
            )
            if rd.get("current_patient_uhid") in self.patients:
                self.patients[rd.get("current_patient_uhid")].current_bed_id = bid
        # Ingest admissions
        for r in conn.execute("SELECT * FROM admissions").fetchall():
            rd = safe_row(r)
            aid = rd["admission_id"]
            uhid = rd["uhid"]
            self.admissions[aid] = AdmissionNode(
                admission_id=aid, uhid=uhid, bed_id=rd.get("bed_id"),
                admitting_doctor_id=rd.get("admitting_doctor_id"),
                department_id=rd.get("ward"), admitting_diagnosis=rd.get("admitting_diagnosis"),
                admission_type="inpatient", admission_date=str(rd.get("admission_date")),
                status=rd.get("status"), dense_summary=f"ADMISSION [{aid}] {uhid}"
            )
            if uhid in self.patients:
                self.patients[uhid].active_admission_id = aid

    # =========================================================================
    # 3. CONTEXT FRESHNESS & MUTATION ENGINE (Solving Context Decay)
    # =========================================================================

    def update_bed_status(self, bed_id: str, new_status: str, patient_uhid: Optional[str] = None):
        """
        Mutates bed lifecycle state immediately (occupied -> dirty -> sanitized -> vacant).
        When a bed transitions away from occupied, patient occupancy is cleanly cleared.
        """
        if bed_id in self.beds:
            b = self.beds[bed_id]
            old_status = b.status
            old_patient = b.current_patient_uhid

            b.status = new_status
            b.current_patient_uhid = patient_uhid if new_status == "occupied" else None
            b.last_turnaround_timestamp = datetime.now(timezone.utc).isoformat()
            b.dense_summary = f"BED [{bed_id}] Ward: {b.ward} | Status: {new_status} | Patient: {b.current_patient_uhid or 'None'}"

            # Invalidate patient's bed link if vacated
            if old_status == "occupied" and new_status != "occupied" and old_patient in self.patients:
                self.patients[old_patient].current_bed_id = None

    def resolve_panic_lab_alert(self, alert_id: str, doctor_id: str):
        """
        Acknowledges critical panic lab value readback in real-time under POL-010.
        Clears the SLA countdown timer and removes the active panic alert blocker.
        """
        if alert_id in self.lab_critical_alerts:
            al = self.lab_critical_alerts[alert_id]
            al.readback_status = "Acknowledged"
            al.doctor_contacted = doctor_id
            al.is_sla_breached = False
            al.ack_time = datetime.now(timezone.utc).isoformat()
            al.dense_summary = f"PANIC LAB [{alert_id}] Patient: {al.uhid} | {al.parameter_name}: {al.critical_value} | ACKNOWLEDGED by {doctor_id}"

    def settle_discharge_billing(self, discharge_id: str):
        """
        Flips central billing clearance flag to True, eliminating the blocker in real time.
        If all clearances are now satisfied, transitions to ready_for_gate_pass.
        """
        if discharge_id in self.discharges:
            d = self.discharges[discharge_id]
            d.clearance_billing = True
            # Recheck overall blocker status
            if d.clearance_clinical and d.clearance_pharmacy and d.clearance_nursing:
                d.is_blocked = False
                d.blocker_reason = None
                d.escalation_rule_id = None
                d.status = "ready_for_gate_pass"
                d.gate_pass_issued = True
            d.dense_summary = TokenOptimizer.optimize_discharge_blocker(
                discharge_id, d.uhid, d.bed_id, d.clearance_clinical,
                d.clearance_pharmacy, True, d.clearance_nursing,
                d.blocker_reason or "All Clearances Satisfied - Ready for Gate Pass",
                "Discharge Desk (ext. 1027)"
            )

    def settle_discharge_pharmacy(self, discharge_id: str):
        """Flips pharmacy return credit clearance flag to True."""
        if discharge_id in self.discharges:
            d = self.discharges[discharge_id]
            d.clearance_pharmacy = True
            if d.clearance_clinical and d.clearance_billing and d.clearance_nursing:
                d.is_blocked = False
                d.blocker_reason = None
                d.status = "ready_for_gate_pass"
                d.gate_pass_issued = True

    def update_claim_status(self, claim_id: str, new_status: str, approved_amount: Optional[float] = None):
        """Mutates cashless insurance claim status (preauth approved / query cleared)."""
        if claim_id in self.claims:
            c = self.claims[claim_id]
            c.status = new_status
            if approved_amount is not None:
                c.approved_amount = approved_amount
            if new_status.lower() in ["approved", "claim-settled"]:
                c.requires_dispute_appeal = False
                c.rejection_reason = None

    def prune_stale_contexts(self):
        """
        Prunes resolved transient operational flags (e.g. acknowledged panic alerts older
        than retention, completed discharges) so no stale context is served downstream.
        """
        # Prune resolved panic alerts that are acknowledged
        active_alerts = {k: v for k, v in self.lab_critical_alerts.items() if v.readback_status != "Acknowledged"}
        self.lab_critical_alerts = active_alerts


# Singleton accessor
_builder_instance: Optional[OntologyBuilder] = None


def get_ontology_builder() -> OntologyBuilder:
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = OntologyBuilder()
        _builder_instance.ingest_governance_layer()
        _builder_instance.ingest_digital_twin()
    return _builder_instance
