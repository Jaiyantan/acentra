"""
Agentic Security Layer & RBAC Middleware
Saveetha Medical College and Hospital (SMCH) Operations Engine
Implements the 6 specific agentic AI defenses required by Hack to Care Build Plan (Page 5).
"""

import re
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from app.database import execute_insert
from app.simulation.events_bus import event_bus

logger = logging.getLogger("smch.security")

# 1. Staff Roles and Permission Matrix (Table on Page 3-4 of Build Plan)
RBAC_MATRIX = {
    "Receptionist": {
        "read_domains": ["admission", "opd", "patient_demographics", "bed_status", "knowledge_base"],
        "write_domains": ["admission_forms", "opd_tokens", "patient_registrations"],
        "can_approve_irreversible": False,
        "max_risk_level": "LOW"
    },
    "Nurse": {
        "read_domains": ["patient_records", "lab_results", "radiology_reports", "nursing_charts", "bed_status", "knowledge_base"],
        "write_domains": ["progress_notes", "nursing_charts", "shift_handovers", "vitals_logs"],
        "can_approve_irreversible": False,
        "max_risk_level": "MEDIUM"
    },
    "Doctor": {
        "read_domains": ["all_clinical_records", "patient_records", "lab_results", "radiology_reports", "pharmacy", "knowledge_base"],
        "write_domains": ["clinical_orders", "prescriptions", "discharge_summaries", "progress_notes", "diagnostic_orders"],
        "can_approve_irreversible": True,
        "approved_actions": ["discharge_patient"],
        "max_risk_level": "HIGH"
    },
    "Specialist": {
        "read_domains": ["clinical_records_own_patients", "specialty_reports", "lab_results", "knowledge_base"],
        "write_domains": ["specialist_notes", "procedure_reports", "tumor_board_records"],
        "can_approve_irreversible": True,
        "approved_actions": ["authorize_surgical_entry", "cancel_surgery"],
        "max_risk_level": "HIGH"
    },
    "Pharmacist": {
        "read_domains": ["prescriptions", "drug_stock", "ddi_alerts", "cold_chain", "knowledge_base"],
        "write_domains": ["dispensing_records", "inventory_updates", "narcotic_register"],
        "can_approve_irreversible": False,
        "max_risk_level": "MEDIUM"
    },
    "Lab / Radiology Tech": {
        "read_domains": ["test_orders", "imaging_worklist", "knowledge_base"],
        "write_domains": ["analyzer_results", "sample_collection", "imaging_acquisitions", "qc_logs"],
        "can_approve_irreversible": False,
        "max_risk_level": "MEDIUM"
    },
    "Billing Staff": {
        "read_domains": ["billing_records", "insurance_claims", "pmjay_packages", "patient_demographics", "knowledge_base"],
        "write_domains": ["invoices", "preauth_submissions", "copay_receipts"],
        "can_approve_irreversible": False,
        "max_risk_level": "MEDIUM"
    },
    "Admin": {
        "read_domains": ["all_domains", "audit_log", "security_logs", "staff_master", "equipment"],
        "write_domains": ["all_non_clinical", "staff_master", "equipment_tickets", "claim_approvals"],
        "can_approve_irreversible": True,
        "approved_actions": ["approve_insurance_claim", "discharge_patient", "override_workflow"],
        "max_risk_level": "CRITICAL"
    }
}

# 2. Irreversible Actions requiring Human Approval Gate (Defense #4)
IRREVERSIBLE_ACTIONS = {
    "discharge_patient": {
        "required_role": "Doctor",
        "description": "Final medical clearance releasing inpatient bed and clinical accountability.",
        "risk_level": "CRITICAL"
    },
    "approve_insurance_claim": {
        "required_role": "Admin",
        "description": "Financial disbursement and claim settlement exceeding statutory threshold.",
        "risk_level": "HIGH"
    },
    "cancel_surgery": {
        "required_role": "Specialist",
        "description": "Cancellation of booked operating theatre slot and procedural team.",
        "risk_level": "HIGH"
    },
    "authorize_surgical_entry": {
        "required_role": "Specialist",
        "description": "Final surgical knife-to-skin authorization into operating suite.",
        "risk_level": "CRITICAL"
    }
}

# 3. Known Prompt Injection & Jailbreak Patterns (Defense #1)
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)?\s*(instructions|guidelines|rules|safety|policies|guardrails)",
    r"disregard\s+(all\s+)?(previous|prior)?\s*(guidelines|rules|instructions|safety|policies)",
    r"you\s+are\s+now\s+in\s+dan\s+mode",
    r"bypass\s+(access\s+controls|rbac|security|billing|rules)",
    r"release\s+(unredacted|confidential|all\s+records)",
    r"override\s+(permissions|guardrails|safety)",
    r"reveal\s+system\s+prompt",
    r"print\s+your\s+instructions",
    r"zero\s+(out\s+)?(pending\s+)?balance"
]

class SecurityLayer:
    def __init__(self):
        self.injection_regex = [re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS]

    def check_prompt_injection(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Defense #1: Prompt Injection Detection.
        Strict separation of data plane and instruction plane.
        """
        if not text:
            return False, None
        for pattern in self.injection_regex:
            if pattern.search(text):
                match = pattern.pattern
                return True, f"Malicious instruction pattern detected: '{match}'"
        return False, None

    def validate_rbac(self, role: str, target_domain: str, is_write: bool = False) -> Tuple[bool, str]:
        """
        Defense #2: Tool Call Privilege Escalation Defense.
        Validates caller role against domain permissions before tool execution.
        """
        role_perms = RBAC_MATRIX.get(role)
        if not role_perms:
            return False, f"Unknown staff role '{role}'. Access denied."

        if role == "Admin":
            if is_write and "clinical" in target_domain.lower() and not "claim" in target_domain.lower():
                return False, "Admin role cannot write directly to clinical medical records. Requires licensed physician."
            return True, "Authorized"

        allowed_list = role_perms["write_domains"] if is_write else role_perms["read_domains"]
        if "all_clinical_records" in allowed_list or "all_domains" in allowed_list:
            return True, "Authorized"

        # Domain matching
        for allowed in allowed_list:
            if allowed in target_domain or target_domain in allowed:
                return True, "Authorized"

        mode_str = "write to" if is_write else "read from"
        return False, f"Role '{role}' is not authorized to {mode_str} domain '{target_domain}'."

    def check_irreversible_action(self, action_name: str, requested_by_role: str) -> Dict[str, Any]:
        """
        Defense #4: Irreversible Action Gating.
        Actions tagged irreversible cannot be executed autonomously by the agent.
        """
        if action_name in IRREVERSIBLE_ACTIONS:
            meta = IRREVERSIBLE_ACTIONS[action_name]
            required_role = meta["required_role"]
            is_authorized = requested_by_role == required_role or (requested_by_role == "Admin" and required_role != "Specialist")
            return {
                "is_irreversible": True,
                "action_name": action_name,
                "required_role": required_role,
                "is_caller_authorized_to_approve": is_authorized,
                "description": meta["description"],
                "gate_status": "GATED_ON_HUMAN_APPROVAL"
            }
        return {"is_irreversible": False, "gate_status": "ALLOWED_FOR_EXECUTION"}

    def log_audit_event(
        self,
        user_role: Optional[str] = None,
        event_type: Optional[str] = None,
        user_input: Optional[str] = None,
        intent_classified: Optional[str] = None,
        tool_called: Optional[str] = None,
        confidence_score: float = 1.0,
        rbac_status: Optional[str] = None,
        irreversible_gated: bool = False,
        security_alert_flag: bool = False,
        details: Optional[Any] = None,
        role: Optional[str] = None,
        action_or_tool: Optional[str] = None,
        status: Optional[str] = None,
        uhid: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Layer 4: Append-Only Audit Logging.
        Writes every event (message, intent, tool called, action, escalation) to SQLite.
        """
        final_role = user_role or role or "Staff"
        final_event = event_type or action_or_tool or "AUDIT_EVENT"
        final_tool = tool_called or action_or_tool or final_event
        final_status = rbac_status or status or "AUTHORIZED"
        final_input = user_input or (f"UHID: {uhid}" if uhid else None)

        details_dict = {}
        if isinstance(details, dict):
            details_dict = dict(details)
        elif isinstance(details, str):
            details_dict = {"info": details}
        if uhid:
            details_dict["uhid"] = uhid

        log_id = f"AUDIT-{datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        now_iso = datetime.now().isoformat()
        details_json = json.dumps(details_dict)

        try:
            execute_insert(
                """INSERT INTO security_audit_log 
                   (log_id, timestamp, user_role, event_type, user_input, intent_classified, 
                    tool_called, confidence_score, rbac_status, irreversible_gated, security_alert_flag, details_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                (
                    log_id, now_iso, final_role, final_event, final_input, intent_classified,
                    final_tool, confidence_score, final_status,
                    1 if irreversible_gated else 0,
                    1 if security_alert_flag else 0,
                    details_json
                )
            )
        except Exception as e:
            logger.error(f"Audit log write failed: {e}")

        # Broadcast if security alert
        if security_alert_flag:
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                loop.create_task(
                    event_bus.publish_event(
                        department="Security & Governance",
                        event_type="Security Threat Intercepted",
                        severity="CRITICAL",
                        summary=f"Security Alert [{final_role}]: {final_event} - {final_input[:80] if final_input else ''}",
                        details={"log_id": log_id, "rbac_status": final_status}
                    )
                )
            except Exception:
                pass

        return log_id

    def get_grounding_safety_anchor(self) -> str:
        """
        Defense #6: Context Window Manipulation Defense.
        Core safety constraints re-injected as a grounding anchor every 10 turns.
        """
        return (
            "[SYSTEM MANDATORY SAFETY ANCHOR]\n"
            "1. You are an Operational Assistant. You MUST NOT provide medical advice or recommend drug dosages.\n"
            "2. You MUST NOT execute irreversible operational actions (discharge, claim approvals) without human approval.\n"
            "3. You MUST NOT bypass RBAC access controls or expose confidential case sheets.\n"
            "4. You MUST ask for missing required fields instead of making unsupported assumptions.\n"
            "5. If uncertain or in clinical territory, ESCALATE to the appropriate human team with source citations."
        )

# Singleton security layer instance
security_layer = SecurityLayer()
