"""
Security, Governance & Human-in-the-Loop API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
Provides endpoints for the Human Approval Queue (irreversible actions),
Escalation Router (5 human teams), and Append-Only Security Audit Log.
"""

from fastapi import APIRouter, Query, Body, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.engine.security_layer import security_layer, IRREVERSIBLE_ACTIONS
from app.engine.workflow_engine import workflow_engine

router = APIRouter(prefix="/api/security", tags=["Security, Governance & Approvals"])

class ApprovalDecisionPayload(BaseModel):
    decision: str = Field(..., description="Approved or Rejected")
    reviewer_role: Optional[str] = None
    approver_role: Optional[str] = None
    approver_name: Optional[str] = "Staff Member"
    notes: Optional[str] = None

@router.get("/audit-log", summary="Append-only security and operational audit trail")
def get_security_audit_log(
    user_role: Optional[str] = None,
    only_alerts: bool = False,
    limit: int = 50
):
    """
    Returns immutable audit logs tracking user messages, classified intents,
    tools called, RBAC status, irreversible gating, and security alerts.
    """
    query = "SELECT * FROM security_audit_log WHERE 1=1"
    params = []
    if user_role:
        query += " AND user_role = ?"
        params.append(user_role)
    if only_alerts:
        query += " AND security_alert_flag = 1"
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    rows = execute_query(query, tuple(params))

    # Normalize fields for frontend compatibility
    normalized = []
    for r in rows:
        normalized.append({
            "id": r.get("log_id"),
            "log_id": r.get("log_id"),
            "timestamp": r.get("timestamp"),
            "role": r.get("user_role"),
            "user_role": r.get("user_role"),
            "event_type": r.get("event_type"),
            "action_or_tool": r.get("tool_called") or r.get("event_type"),
            "uhid": r.get("user_input") if "UHID" in str(r.get("user_input", "")) else "GLOBAL",
            "status": r.get("rbac_status"),
            "rbac_status": r.get("rbac_status"),
            "confidence_score": r.get("confidence_score") or 0.95,
            "details": r.get("details_json") or r.get("user_input") or ""
        })

    return {"total": len(normalized), "audit_logs": normalized}

@router.get("/approvals", summary="Human Approval Queue for irreversible operational actions")
def get_human_approval_queue(status: Optional[str] = None):
    """
    Returns pending irreversible actions (discharge_patient, approve_insurance_claim, cancel_surgery)
    that cannot be executed autonomously by the AI agent without explicit human confirmation.
    """
    query = "SELECT * FROM human_approval_queue WHERE 1=1"
    params = []
    if status:
        query += " AND (status = ? OR status = ?)"
        params.extend([status, f"{status}_APPROVAL"])
    query += " ORDER BY approval_id DESC"
    rows = execute_query(query, tuple(params))

    normalized = []
    for r in rows:
        normalized.append({
            "id": r.get("approval_id"),
            "approval_id": r.get("approval_id"),
            "action_name": r.get("action_name"),
            "uhid": r.get("patient_uhid"),
            "patient_uhid": r.get("patient_uhid"),
            "requested_by": r.get("requested_by_role"),
            "requested_by_role": r.get("requested_by_role"),
            "required_role": r.get("required_approver_role"),
            "required_approver_role": r.get("required_approver_role"),
            "payload": r.get("action_payload_json"),
            "action_payload_json": r.get("action_payload_json"),
            "status": "PENDING" if "PENDING" in str(r.get("status", "")).upper() else r.get("status"),
            "raw_status": r.get("status"),
            "decision_by": r.get("decision_by"),
            "decision_timestamp": r.get("decision_timestamp"),
            "requested_at": r.get("decision_timestamp") or "2026-10-08 09:30:00",
            "notes": r.get("notes")
        })

    return {"total": len(normalized), "approvals": normalized, "approval_queue": normalized}

@router.post("/approvals/{approval_id}/decide", summary="Human decision on irreversible action")
@router.post("/approvals/{approval_id}/action", summary="Human decision on irreversible action (alias)")
def act_on_human_approval(approval_id: str, payload: ApprovalDecisionPayload):
    """
    Human-in-the-Loop approval gate execution:
    Validates approver role against required authority and marks action executed or rejected.
    """
    rows = execute_query("SELECT * FROM human_approval_queue WHERE approval_id = ?", (approval_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Approval request not found.")
    appr = rows[0]

    decision = payload.decision.upper()
    role = payload.reviewer_role or payload.approver_role or "Doctor"
    name = payload.approver_name or "Hospital Staff"

    required_role = appr["required_approver_role"]
    if role != required_role and role != "Admin":
        security_layer.log_audit_event(
            role=role,
            action_or_tool=appr["action_name"],
            uhid=appr["patient_uhid"],
            status="BLOCKED_UNAUTHORIZED_APPROVAL",
            confidence_score=0.99,
            details=f"Unauthorized approval attempt. Role '{role}' attempted to approve '{appr['action_name']}' requiring '{required_role}'."
        )
        raise HTTPException(
            status_code=403,
            detail=f"Role '{role}' is not authorized to approve this action. Requires '{required_role}' or Admin."
        )

    execute_insert(
        """UPDATE human_approval_queue 
           SET status = ?, decision_by = ?, decision_timestamp = CURRENT_TIMESTAMP, notes = ?
           WHERE approval_id = ?;""",
        (decision, f"{name} ({role})", payload.notes or "", approval_id)
    )

    # If linked to a workflow instance, update instance status
    wfi_id = appr.get("workflow_instance_id")
    if wfi_id:
        new_status = "COMPLETE" if decision == "APPROVED" else "REJECTED_BY_HUMAN"
        execute_insert(
            "UPDATE active_workflow_instances SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE instance_id = ?;",
            (new_status, wfi_id)
        )

    security_layer.log_audit_event(
        role=role,
        action_or_tool=appr["action_name"],
        uhid=appr["patient_uhid"],
        status=f"HUMAN_{decision}",
        confidence_score=1.0,
        details=f"Action '{appr['action_name']}' {decision} by {name} ({role})"
    )

    return {
        "status": "SUCCESS",
        "approval_id": approval_id,
        "decision": decision,
        "approver": f"{name} ({role})",
        "message": f"Action '{appr['action_name']}' has been {decision}."
    }

@router.get("/escalations", summary="Escalations log routed across the 5 human teams")
def get_escalations(
    target_team: Optional[str] = None,
    trigger_type: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Returns escalated requests categorized by the 5 distinct teams:
    1. Account Management
    2. Clinical Review
    3. Compliance & Senior Ops
    4. Central Triage
    5. Subject Matter Specialist Desk
    """
    query = "SELECT * FROM escalations_log WHERE 1=1"
    params = []
    if target_team:
        query += " AND (target_team_id = ? OR target_team_name LIKE ?)"
        params.extend([target_team, f"%{target_team}%"])
    if trigger_type:
        query += " AND trigger_type = ?"
        params.append(trigger_type)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY timestamp DESC LIMIT 50"
    rows = execute_query(query, tuple(params))

    normalized = []
    for r in rows:
        normalized.append({
            "id": r.get("escalation_id"),
            "escalation_id": r.get("escalation_id"),
            "target_team": r.get("target_team_name") or r.get("target_team_id"),
            "urgency": r.get("urgency_level") or "HIGH",
            "uhid": r.get("ticket_id") or "N/A",
            "trigger_reason": r.get("trigger_reason") or r.get("trigger_type"),
            "brief_summary": r.get("structured_brief") or r.get("trigger_reason"),
            "escalated_at": r.get("timestamp") or "2026-10-08 09:30:00"
        })

    return {"total": len(normalized), "escalations": normalized}
