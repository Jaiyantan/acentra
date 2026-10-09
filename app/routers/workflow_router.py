"""
Workflow Engine API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
Provides endpoints for JSON workflow execution, missing-field detection, instance tracking, and escalations.
"""

from fastapi import APIRouter, Query, Body, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.engine.workflow_engine import workflow_engine

router = APIRouter(prefix="/api/workflows", tags=["Workflow Automation Engine"])

class WorkflowInitiatePayload(BaseModel):
    workflow_id: str
    initiator_role: Optional[str] = "Receptionist"
    role: Optional[str] = None
    uhid: Optional[str] = "UHID-2026-0001"
    initial_fields: Optional[Dict[str, Any]] = None
    provided_fields: Optional[Dict[str, Any]] = None

class WorkflowAdvancePayload(BaseModel):
    instance_id: str
    user_role: Optional[str] = "Receptionist"
    role: Optional[str] = None
    supplied_fields: Optional[Dict[str, Any]] = None
    fields: Optional[Dict[str, Any]] = None

@router.get("/configs", summary="List all JSON workflow configurations")
def get_workflow_configs():
    """
    Returns all registered workflow definitions (Admission, Consultation, Lab Order,
    Medication Dispensing, Pre-Auth, Discharge, Surgery Clearance).
    """
    workflows = workflow_engine.get_all_workflows()
    return {"total": len(workflows), "workflows": workflows}

@router.get("/configs/{workflow_id}", summary="Get specific workflow configuration")
def get_workflow_by_id(workflow_id: str):
    """
    Returns step definitions, required fields, and irreversible action flags for a workflow.
    """
    wf = workflow_engine.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow configuration not found.")
    return wf

@router.post("/initiate", summary="Initiate a workflow with missing-field detection")
def initiate_workflow(payload: WorkflowInitiatePayload):
    """
    Initiates a workflow instance.
    - If mandatory fields are missing: marks status BLOCKED and prompts for missing information
      rather than making unsupported assumptions.
    - If fields are present: starts step execution.
    """
    role = payload.role or payload.initiator_role or "Receptionist"
    fields = payload.provided_fields or payload.initial_fields or {}
    uhid = payload.uhid or fields.get("uhid") or "UHID-2026-0001"
    result = workflow_engine.initiate_workflow(payload.workflow_id, role, uhid, fields)
    return result

@router.post("/advance", summary="Advance workflow step or supply missing fields")
def advance_workflow(payload: WorkflowAdvancePayload):
    """
    Advances an active workflow instance.
    - Gates irreversible actions (discharge, claim approvals) on human approval.
    - Advances patient lifecycle across the 10 Patient Journey States upon completion.
    """
    role = payload.role or payload.user_role or "Receptionist"
    fields = payload.supplied_fields or payload.fields or {}
    result = workflow_engine.advance_workflow(payload.instance_id, role, fields)
    return result

@router.get("/active", summary="List running workflow instances and missing field states")
def get_active_instances(status: Optional[str] = None, limit: int = 50):
    """
    Returns active workflow instances with step progression, collected fields, and missing fields.
    """
    query = "SELECT * FROM active_workflow_instances WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    rows = execute_query(query, tuple(params))
    return {"total": len(rows), "instances": rows}

@router.get("/escalations", summary="List 5-Team human escalations log")
def get_escalations(team: Optional[str] = None, limit: int = 50):
    """
    Returns structured escalation briefs dispatched to the 5 specialized human teams:
    1. Central Triage Desk
    2. Clinical Review Desk
    3. Compliance & Senior Operations
    4. Account Management
    5. Subject-Matter Specialist Desk
    """
    query = "SELECT * FROM escalations_log WHERE 1=1"
    params = []
    if team:
        query += " AND (target_team_id = ? OR target_team_name LIKE ?)"
        params.extend([team, f"%{team}%"])
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    rows = execute_query(query, tuple(params))
    normalized = []
    for r in rows:
        normalized.append({
            "id": r.get("escalation_id"),
            "escalation_id": r.get("escalation_id"),
            "target_team": r.get("target_team_name") or r.get("target_team_id"),
            "target_team_name": r.get("target_team_name"),
            "urgency": r.get("urgency_level") or "HIGH",
            "urgency_level": r.get("urgency_level"),
            "uhid": r.get("ticket_id") or "N/A",
            "ticket_id": r.get("ticket_id"),
            "trigger_reason": r.get("trigger_reason"),
            "brief_summary": r.get("structured_brief") or r.get("trigger_reason"),
            "structured_brief": r.get("structured_brief"),
            "escalated_at": r.get("timestamp"),
            "timestamp": r.get("timestamp")
        })
    return {"total": len(normalized), "escalations": normalized}
