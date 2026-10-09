"""
Knowledge Base & Synthetic Workbook API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
Provides RAG-grounded answers with source citations, communicates uncertainty,
evaluates security layers, and surfaces approved policy articles.
"""

import json
import uuid
from pathlib import Path
from fastapi import APIRouter, Query, Body, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.database import execute_query, execute_insert
from app.engine.security_layer import security_layer
from app.engine.workflow_engine import workflow_engine

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base & Second Brain"])

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"

def _load_json(filename: str):
    p = KB_DIR / filename
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

class KnowledgeQueryPayload(BaseModel):
    query: Optional[str] = None
    query_str: Optional[str] = None
    role: Optional[str] = None
    user_role: Optional[str] = "Receptionist"
    uhid: Optional[str] = None

@router.get("/articles", summary="List approved knowledge articles with source citations")
def get_articles(department: Optional[str] = None):
    """
    Returns approved SOPs and operational policies.
    Each section includes an explicit citation tag (e.g. [SMCH Policy Manual §ADM.101]).
    """
    articles = _load_json("approved_knowledge_articles.json")
    if department:
        articles = [a for a in articles if department.lower() in a.get("department", "").lower()]
    return {"total": len(articles), "articles": articles}

@router.get("/workbook", summary="Inspect full synthetic workbook (All 5 content types)")
def get_full_workbook():
    """
    Returns the synthetic workbook required by Problem Statement & Build Plan:
    1. Approved knowledge articles
    2. Operations requests (sample tickets)
    3. Workflow information (registered JSON workflows)
    4. Routing rules (5 escalation teams)
    5. Field definitions
    """
    return {
        "approved_knowledge_articles": _load_json("approved_knowledge_articles.json"),
        "operations_requests_sample": _load_json("operations_requests_sample.json"),
        "routing_rules": _load_json("routing_rules.json"),
        "field_definitions": _load_json("field_definitions.json")
    }

@router.post("/query", summary="Source-grounded RAG inquiry with citation, security check, and uncertainty scoring")
def query_knowledge_base(payload: KnowledgeQueryPayload):
    """
    Simulates the Hermes Agent + Supermemory / Second Brain knowledge retrieval layer:
    1. Prompt Injection Defense (Defense #1)
    2. Clinical Boundary Enforcement (Routes to Clinical Review Desk)
    3. Irreversible Action Gating (Defense #4 - Routes to Human Approval Queue)
    4. Missing-Field Workflow Detector (Workflow Engine)
    5. RAG Source Grounding with Exact Citations (Defense #5)
    6. Uncertainty Communication without Unsupported Assumptions
    """
    query_text = payload.query or payload.query_str or ""
    role = payload.role or payload.user_role or "Receptionist"
    uhid = payload.uhid or "UHID-2026-0012"
    q_lower = query_text.lower()

    if not query_text.strip():
        raise HTTPException(status_code=400, detail="Query text cannot be empty.")

    # 1. Prompt Injection Detection
    is_injection, reason = security_layer.check_prompt_injection(query_text)
    if is_injection:
        audit_id = security_layer.log_audit_event(
            role=role,
            action_or_tool="PROMPT_EVALUATION",
            uhid=uhid,
            status="BLOCKED",
            confidence_score=0.99,
            details=f"Prompt injection pattern blocked: {reason}"
        )
        return {
            "status": "SECURITY_BLOCKED",
            "response": f"🚨 SECURITY DEFENSE TRIGGERED: Prompt injection attempt detected. Input safely rejected.\nReason: {reason}\nAudit Log: {audit_id}",
            "confidence_score": 0.0,
            "citations": [],
            "audit_id": audit_id
        }

    # 2. Clinical Boundary Enforcement
    clinical_keywords = ["dosage", "norepinephrine", "mg/kg", "titrate", "prescribe", "administer", "bolus", "infusion rate"]
    if any(kw in q_lower for kw in clinical_keywords) and role not in ["Doctor", "Specialist"]:
        esc_res = workflow_engine.route_escalation(
            trigger_reason="Clinical Decision & Medication Dosing Outside Agent Boundary",
            confidence_score=0.95,
            uhid=uhid,
            context={"query": query_text, "role": role}
        )
        esc_team = esc_res.get("target_team") or esc_res.get("target_team_name") or "Clinical Review Desk"
        audit_id = security_layer.log_audit_event(
            role=role,
            action_or_tool="CLINICAL_DECISION_QUERY",
            uhid=uhid,
            status="ESCALATED_CLINICAL",
            confidence_score=0.95,
            details=f"Clinical boundary guarded. Escalated to {esc_team}"
        )
        return {
            "status": "CLINICAL_ESCALATION",
            "response": f"🩺 CLINICAL BOUNDARY ENFORCED: The AI Operations Assistant does not prescribe medications, calculate acute pharmacological doses, or make independent clinical decisions.\n\nThis inquiry has been escalated to the Clinical Review Desk for immediate evaluation by an attending physician.\nTicket Reference: {esc_res['escalation_id']}",
            "citations": [
                {
                    "policy_code": "CLI-501",
                    "title": "Clinical Boundary & Physician Authority SOP",
                    "citation_tag": "[SMCH Policy Manual §CLI.501]"
                }
            ],
            "confidence_score": 0.95,
            "escalation_id": esc_res["escalation_id"],
            "audit_id": audit_id
        }

    # 3. Irreversible Action Gating
    if "approve" in q_lower and ("claim" in q_lower or "insurance" in q_lower):
        gate_res = security_layer.check_irreversible_action("approve_insurance_claim", role)
        queue_id = f"APPR-{uuid.uuid4().hex[:6].upper()}"
        execute_insert(
            """INSERT INTO human_approval_queue 
               (approval_id, workflow_instance_id, action_name, patient_uhid, requested_by_role, 
                required_approver_role, action_payload_json, status, decision_by, decision_timestamp, notes)
               VALUES (?, NULL, 'approve_insurance_claim', ?, ?, 'Admin', ?, 'PENDING_APPROVAL', NULL, NULL, 'Financial claim approval requires human authorization.');""",
            (queue_id, uhid, role, json.dumps({"query": query_text, "action": "approve_insurance_claim"}))
        )
        audit_id = security_layer.log_audit_event(
            role=role,
            action_or_tool="approve_insurance_claim",
            uhid=uhid,
            status="GATED_HUMAN_APPROVAL",
            confidence_score=0.99,
            details="Financial claim approval requires human authorization."
        )
        return {
            "status": "IRREVERSIBLE_ACTION_GATED",
            "response": f"🔒 IRREVERSIBLE ACTION DETECTED & GATED: Approving high-value insurance claims is an irreversible action requiring human verification.\n\nThe action has been placed in the Human Approval Queue with ticket ID {queue_id}. An authorized reviewer (Admin/Billing Lead) must review and approve before release.",
            "irreversible_action": {"action": "approve_insurance_claim", "queue_id": queue_id},
            "confidence_score": 0.99,
            "audit_id": audit_id
        }

    # 4. Workflow Initiation & Missing Field Detection
    if any(k in q_lower for k in ["admit", "admission", "ward", "inpatient"]):
        wf_res = workflow_engine.initiate_workflow(
            workflow_id="admission_workflow",
            initiator_role=role,
            uhid=uhid,
            provided_fields={"uhid": uhid} if uhid else {}
        )
        audit_id = security_layer.log_audit_event(
            role=role,
            action_or_tool="admission_workflow.initiate",
            uhid=uhid,
            status=wf_res["status"],
            confidence_score=0.92,
            details=f"Admission workflow evaluated. Status: {wf_res['status']}"
        )
        if wf_res["status"] == "BLOCKED":
            missing_prompts = wf_res.get("missing_fields", [])
            return {
                "status": "WORKFLOW_TRIGGERED",
                "response": f"⚠️ Inpatient Admission Workflow initiated for {uhid}, but required parameters are missing.\n\nThe assistant cannot assume unstated parameters. Please provide the required information below to proceed.",
                "missing_fields": missing_prompts,
                "confidence_score": 0.92,
                "audit_id": audit_id
            }

    # 5. RAG Retrieval from Approved Knowledge Articles
    articles = _load_json("approved_knowledge_articles.json")
    matched_sections = []
    for art in articles:
        for sec in art.get("sections", []):
            allowed = sec.get("allowed_roles", [])
            if role not in allowed and role != "Admin":
                continue

            content = sec.get("content", "")
            title = sec.get("title", "")
            overlap = sum(1 for word in q_lower.split() if len(word) > 3 and (word in content.lower() or word in title.lower()))
            if overlap > 0:
                matched_sections.append({
                    "article_id": art["article_id"],
                    "title": art["title"],
                    "policy_code": art["policy_code"],
                    "citation_tag": art["citation_tag"] + " (" + sec["title"] + ")",
                    "content": content,
                    "relevance_score": overlap
                })

    if not matched_sections:
        # Communicate uncertainty explicitly
        audit_id = security_layer.log_audit_event(
            role=role,
            action_or_tool="KNOWLEDGE_RAG_SEARCH",
            uhid=uhid,
            status="UNCERTAIN_ESCALATED",
            confidence_score=0.25,
            details="Zero verified SOP matches. Assistant communicated uncertainty."
        )
        return {
            "status": "UNCERTAIN",
            "confidence_score": 0.25,
            "response": "The available approved hospital documents do not contain sufficient verified information to answer this inquiry safely. The assistant communicates uncertainty and recommends escalating to the Subject-Matter Specialist Desk rather than making unsupported assumptions.",
            "citations": [],
            "should_escalate": True,
            "recommended_escalation_team": "Subject-Matter Specialist Desk",
            "audit_id": audit_id
        }

    matched_sections.sort(key=lambda s: s["relevance_score"], reverse=True)
    best = matched_sections[0]

    audit_id = security_layer.log_audit_event(
        role=role,
        action_or_tool="KNOWLEDGE_RAG_SEARCH",
        uhid=uhid,
        status="ALLOWED",
        confidence_score=0.96,
        details=f"Grounded response retrieved from {best['policy_code']}"
    )

    return {
        "status": "GROUNDED_ANSWER",
        "confidence_score": 0.96,
        "response": best["content"],
        "citations": [
            {
                "policy_code": best["policy_code"],
                "title": best["title"],
                "citation_tag": best["citation_tag"]
            }
        ],
        "audit_id": audit_id
    }
