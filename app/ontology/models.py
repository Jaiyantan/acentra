"""
SMCH Hospital Operations Ontology Models (DataPoints)
Defines both:
1. Static Governance Objects (SOPs, Policies, Workflows, Rules, Teams, Fields)
2. Dynamic Operational Digital Twin Objects (Patients, Beds, Admissions, Discharges, Orders, Labs, Bills, Claims, Tickets)

Each DataPoint utilizes dense indexing fields (`dense_summary`) to eliminate token waste.
"""

from typing import Optional, List, Dict, Any
from pydantic import Field, SkipValidation
from cognee.infrastructure.engine.models.DataPoint import DataPoint


# =========================================================================
# 1. STATIC GOVERNANCE & POLICY ONTOLOGY OBJECTS
# =========================================================================

class DepartmentNode(DataPoint):
    """Hospital Department Entity (Clinical, Clinical Support, Administrative)."""
    dept_id: str
    name: str
    dept_type: str
    head_of_department: Optional[str] = None
    contact_extension: Optional[str] = None
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class StaffNode(DataPoint):
    """Staff Member Identity & Role Permissions."""
    staff_id: str
    name: str
    role: str
    department_id: str
    contact: Optional[str] = None
    email: Optional[str] = None
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class PolicyNode(DataPoint):
    """Institutional Compliance & Safety Policy (e.g., POL-010 Panic Labs)."""
    doc_id: str
    title: str
    department: str
    version: str
    mandate: str
    scope: str
    citation: str
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class SOPNode(DataPoint):
    """Standard Operating Procedure defining multi-step clinical/operational execution."""
    doc_id: str
    title: str
    department: str
    version: str
    applicable_roles: List[str] = []
    purpose: str
    step_sequence: List[str] = []
    blockers: List[str] = []
    escalations: List[str] = []
    citation: str
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class KnowledgeArticleNode(DataPoint):
    """System How-To Guide for HIS, LIS, RIS, Billing, and TPA Portals."""
    doc_id: str
    title: str
    host_system: str
    department: str
    version: str
    applicable_roles: List[str] = []
    overview: str
    procedures: List[str] = []
    common_errors: List[str] = []
    contact_extension: str
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class FieldDefinitionNode(DataPoint):
    """Canonical Healthcare Operations Field Schema with Validation Regex."""
    field_name: str
    display_name: str
    data_type: str
    is_required: bool
    validation_pattern: Optional[str] = None
    select_options: Optional[List[str]] = None
    on_missing_message: str
    used_in_workflows: List[str] = []
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class RoutingRuleNode(DataPoint):
    """Escalation Routing Rule connecting triggers to responsible human teams."""
    rule_id: str
    trigger: str
    trigger_type: str
    route_to_team: str
    contact_extension: str
    helpdesk_queue: str
    priority: str
    sla_hours: float
    escalation_reason: str
    sample_queries: List[str] = []
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class SupportTeamNode(DataPoint):
    """Internal Support Department Directory."""
    team_id: str
    name: str
    handles: List[str] = []
    contact_extension: str
    email: str
    helpdesk_queue: str
    sla_hours: float
    escalation_to: Optional[str] = None
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class WorkflowStepNode(DataPoint):
    """Granular Step State within an Operational Workflow."""
    step_id: str
    workflow_id: str
    step_number: int
    step_name: str
    actor_role: str
    required_fields: List[str] = []
    simulation_endpoint: Optional[str] = None
    blockers: List[str] = []
    escalation_rule_id: Optional[str] = None
    requires_human_approval: bool = False
    human_approver_role: Optional[str] = None
    next_step_id: Optional[str] = None
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class WorkflowNode(DataPoint):
    """End-to-End Operational State Machine (WF-001 to WF-008)."""
    workflow_id: str
    slug: str
    name: str
    department: str
    trigger_intents: List[str] = []
    allowed_roles: List[str] = []
    requires_human_approval: bool = True
    approval_checkpoint: str
    steps_count: int = 0
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


# =========================================================================
# 2. DYNAMIC OPERATIONAL DIGITAL TWIN OBJECTS (Solving Context Fragmentation)
# =========================================================================

class PatientNode(DataPoint):
    """Live Inpatient/Outpatient Demographic Record in Digital Twin."""
    uhid: str
    name: str
    age: int
    gender: str
    contact: str
    registration_date: str
    status: str  # registered, admitted, discharged
    current_bed_id: Optional[str] = None
    active_admission_id: Optional[str] = None
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class BedNode(DataPoint):
    """Real-time Ward & ICU Bed Status & Turnaround Lifecycle."""
    bed_id: str
    ward: str
    department_id: str
    bed_type: str
    status: str  # vacant, occupied, dirty, maintenance
    current_patient_uhid: Optional[str] = None
    active_admission_id: Optional[str] = None
    last_turnaround_timestamp: Optional[str] = None
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class AdmissionNode(DataPoint):
    """Active Hospital Inpatient Stay."""
    admission_id: str
    uhid: str
    bed_id: str
    admitting_doctor_id: str
    department_id: str
    admitting_diagnosis: str
    admission_type: str
    admission_date: str
    discharge_date: Optional[str] = None
    status: str  # active, discharged, transfer_pending
    has_blocked_discharge: bool = False
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class DischargeNode(DataPoint):
    """Four-Point Inpatient Discharge Tracking Object."""
    discharge_id: str
    admission_id: str
    uhid: str
    bed_id: str
    discharge_type: str
    final_diagnosis: str
    clearance_clinical: bool = True
    clearance_pharmacy: bool = True
    clearance_billing: bool = True
    clearance_nursing: bool = True
    is_blocked: bool = False
    blocker_reason: Optional[str] = None
    escalation_rule_id: Optional[str] = None
    resolution_team_extension: Optional[str] = None
    gate_pass_issued: bool = False
    status: str  # pending_clearance, blocked, ready_for_gate_pass, completed
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class OrderNode(DataPoint):
    """Diagnostic Investigation Requisition (LIS / RIS)."""
    order_id: str
    admission_id: str
    uhid: str
    order_type: str
    test_name: str
    priority: str  # routine, urgent, stat
    ordering_doctor_id: str
    order_date: str
    status: str  # ordered, collected, processing, completed
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class LabResultNode(DataPoint):
    """Laboratory Result with Critical Panic Value Readback Monitoring."""
    result_id: str
    order_id: str
    admission_id: str
    uhid: str
    test_name: str
    result_value: str
    reference_range: str
    critical_value_flag: bool = False
    doctor_alerted: bool = False
    alert_sla_minutes: float = 15.0
    elapsed_alert_minutes: float = 0.0
    is_sla_breached: bool = False
    readback_doctor_id: Optional[str] = None
    status: str  # pending_readback, acknowledged, normal
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class BillNode(DataPoint):
    """Real-Time Inpatient Bill Account."""
    bill_id: str
    admission_id: str
    uhid: str
    total_amount: float
    paid_amount: float
    pending_amount: float
    unbilled_consumables: float = 0.0
    has_billing_dispute: bool = False
    dispute_amount: float = 0.0
    status: str  # draft, interim, final_settled, disputed
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class ClaimNode(DataPoint):
    """Cashless Insurance Claim and TPA Pre-Authorization Status."""
    claim_id: str
    admission_id: str
    uhid: str
    insurer: str
    tpa: str
    policy_number: str
    claim_amount: float
    approved_amount: float
    status: str  # preauth_submitted, approved, query_raised, rejected
    rejection_reason: Optional[str] = None
    rejection_clause: Optional[str] = None
    requires_dispute_appeal: bool = False
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class TicketNode(DataPoint):
    """Operational Support and IT Ticket."""
    ticket_id: str
    category: str
    severity: str  # low, medium, high, critical
    description: str
    reporter_staff_id: str
    department_id: str
    assigned_team: str
    status: str  # open, in_progress, resolved
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class LabPanicAlertNode(DataPoint):
    """Critical Panic Lab Value requiring mandatory verbal readback under POL-010."""
    alert_id: str
    order_id: str
    uhid: str
    patient_name: str
    parameter_name: str
    critical_value: str
    alert_time: str
    doctor_contacted: Optional[str] = None
    doctor_phone: Optional[str] = None
    readback_status: str  # Pending-Ack, Acknowledged, Escalated, Expired
    sla_minutes: float = 15.0
    elapsed_minutes: float = 0.0
    is_sla_breached: bool = False
    ack_time: Optional[str] = None
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class PrescriptionNode(DataPoint):
    """Pharmacy Medication Indent / Inpatient Prescription."""
    intake_id: str
    uhid: str
    patient_name: str
    doctor_id: str
    source: str
    drugs_summary: str
    status: str  # Pending, Dispensed, Returned
    intake_time: str
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class DispensingNode(DataPoint):
    """Pharmacy Medication Dispensing & Batch Verification Log."""
    dispense_id: str
    intake_id: str
    uhid: str
    drug_name: str
    batch_no: str
    expiry_date: str
    qty_dispensed: int
    pharmacist_name: str
    ddi_warning: Optional[str] = None
    timestamp: str
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class RadiologyReportNode(DataPoint):
    """Radiology & PACS Imaging Diagnostic Study & Critical Findings."""
    report_id: str
    study_id: str
    uhid: str
    modality: str
    radiologist_name: str
    findings: str
    impression: str
    is_critical_finding: bool = False
    turnaround_time_min: float = 0.0
    reported_time: str
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}


class EmergencyCaseNode(DataPoint):
    """Emergency Department Patient Triage & Acute Disposition."""
    case_id: str
    uhid: str
    patient_name: str
    triage_level: str  # Red (P1), Yellow (P2), Green (P3)
    arrival_mode: str
    chief_complaint: str
    time_to_doctor_min: Optional[int] = None
    assigned_doctor: Optional[str] = None
    disposition: Optional[str] = None
    status: str  # Active, Admitted, Discharged, Transferred
    dense_summary: str
    metadata: dict = {"index_fields": ["dense_summary"]}

