"""
Stateful Hospital Workflow Engine & Escalation Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
Implements JSON-configurable multi-step workflows, missing-field detection,
irreversible action gating, and 5-team human escalation routing.
"""

import os
import json
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from app.database import execute_insert, execute_query
from app.simulation.events_bus import event_bus
from app.engine.security_layer import security_layer, IRREVERSIBLE_ACTIONS

logger = logging.getLogger("smch.workflow_engine")

CONFIG_DIR = Path(__file__).resolve().parent.parent / "workflows" / "configs"
KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"

class WorkflowEngine:
    def __init__(self):
        self.workflow_configs: Dict[str, Dict[str, Any]] = {}
        self.field_definitions: Dict[str, Any] = {}
        self.routing_rules: Dict[str, Any] = {}
        self.load_configs()

    def load_configs(self):
        """Loads all JSON workflow configs and field definitions."""
        self.workflow_configs.clear()
        if CONFIG_DIR.exists():
            for f in CONFIG_DIR.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        cfg = json.load(fp)
                        wf_id = cfg.get("workflow_id")
                        if wf_id:
                            self.workflow_configs[wf_id] = cfg
                            self.workflow_configs[f.stem] = cfg
                except Exception as e:
                    logger.error(f"Failed to load workflow config {f}: {e}")

        # Load field definitions
        fdef_path = KB_DIR / "field_definitions.json"
        if fdef_path.exists():
            try:
                with open(fdef_path, "r", encoding="utf-8") as fp:
                    self.field_definitions = json.load(fp).get("fields", {})
            except Exception as e:
                logger.error(f"Failed to load field definitions: {e}")

        # Load routing rules
        rr_path = KB_DIR / "routing_rules.json"
        if rr_path.exists():
            try:
                with open(rr_path, "r", encoding="utf-8") as fp:
                    self.routing_rules = json.load(fp)
            except Exception as e:
                logger.error(f"Failed to load routing rules: {e}")

        logger.info(f"Loaded {len(self.workflow_configs)} JSON workflow configurations.")

    def get_all_workflows(self) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for v in self.workflow_configs.values():
            wid = v.get("workflow_id")
            if wid not in seen:
                seen.add(wid)
                unique.append(v)
        return unique

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        if not workflow_id:
            return None
        if workflow_id in self.workflow_configs:
            return self.workflow_configs[workflow_id]
        for k, v in self.workflow_configs.items():
            if k.lower() == workflow_id.lower() or workflow_id.lower() in k.lower():
                return v
        return None

    # -------------------------------------------------------------
    # WORKFLOW INITIATION & STEPWISE ADVANCEMENT
    # -------------------------------------------------------------
    def initiate_workflow(
        self,
        workflow_id: str,
        initiator_role: str,
        uhid: str,
        initial_fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Initiates a multi-step workflow.
        Checks RBAC permissions, validates missing fields, and enforces state tracking.
        """
        config = self.get_workflow(workflow_id)
        if not config:
            return {"status": "ERROR", "message": f"Workflow '{workflow_id}' not found."}

        # 1. RBAC Validation
        allowed_roles = config.get("allowed_roles", [])
        if initiator_role not in allowed_roles and initiator_role != "Admin":
            security_layer.log_audit_event(
                user_role=initiator_role,
                event_type="RBAC_DENIED",
                user_input=f"Attempted to initiate {config['name']}",
                tool_called="initiate_workflow",
                rbac_status="DENIED",
                security_alert_flag=True,
                details={"workflow_id": workflow_id, "allowed_roles": allowed_roles}
            )
            return {
                "status": "DENIED",
                "message": f"Role '{initiator_role}' is not authorized to initiate workflow '{config['name']}'. Allowed roles: {allowed_roles}."
            }

        instance_id = f"WFI-{datetime.now().strftime('%m%d%H%M')}-{uuid.uuid4().hex[:4].upper()}"
        steps = config.get("steps", [])
        if not steps:
            return {"status": "ERROR", "message": "Workflow has no defined steps."}

        first_step = steps[0]
        step_id = first_step["step_id"]
        required_fields = first_step.get("required_fields", [])

        # 2. Missing-Field Detector (Core Bullet 3 requirement)
        missing_fields = []
        collected_fields = dict(initial_fields)

        for req in required_fields:
            if req not in collected_fields or collected_fields[req] is None or collected_fields[req] == "":
                missing_fields.append(req)

        # Build informative clarifying prompt for missing fields
        clarification_prompts = []
        for mf in missing_fields:
            fdef = self.field_definitions.get(mf, {})
            prompt_text = fdef.get("prompt_when_missing", f"Please provide '{mf}' before proceeding.")
            clarification_prompts.append(prompt_text)

        initial_status = "BLOCKED" if missing_fields else "IN_PROGRESS"

        # Record in database
        execute_insert(
            """INSERT INTO active_workflow_instances 
               (instance_id, workflow_id, workflow_name, initiator_role, uhid, status, current_step_id, collected_fields_json, missing_fields_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            (
                instance_id, workflow_id, config["name"], initiator_role, uhid,
                initial_status, step_id, json.dumps(collected_fields), json.dumps(missing_fields)
            )
        )

        # Audit log
        security_layer.log_audit_event(
            user_role=initiator_role,
            event_type="WORKFLOW_INITIATED",
            user_input=f"Initiated {config['name']} for UHID {uhid}",
            intent_classified="WORKFLOW_INITIATE",
            tool_called=first_step.get("action_tool"),
            confidence_score=1.0,
            rbac_status="AUTHORIZED",
            details={"instance_id": instance_id, "step_id": step_id, "missing_fields": missing_fields}
        )

        response = {
            "instance_id": instance_id,
            "workflow_id": workflow_id,
            "workflow_name": config["name"],
            "current_step": {
                "step_id": step_id,
                "step_name": first_step["step_name"],
                "action_tool": first_step.get("action_tool")
            },
            "status": initial_status,
            "collected_fields": collected_fields,
            "missing_fields": missing_fields,
            "is_blocked_by_missing_fields": len(missing_fields) > 0,
            "clarification_prompts": clarification_prompts,
            "system_instruction": "Please provide missing fields before proceeding. The assistant cannot make unsupported assumptions." if missing_fields else "Step 1 fields verified. Ready to execute."
        }

        return response

    def advance_workflow(
        self,
        instance_id: str,
        user_role: str,
        supplied_fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Advances an active workflow instance with new supplied fields.
        Validates missing fields, executes safe tools, and gates irreversible actions.
        """
        rows = execute_query(
            "SELECT * FROM active_workflow_instances WHERE instance_id = ?",
            (instance_id,)
        )
        if not rows:
            return {"status": "ERROR", "message": f"Workflow instance '{instance_id}' not found."}

        inst = rows[0]
        config = self.get_workflow(inst["workflow_id"])
        if not config:
            return {"status": "ERROR", "message": "Workflow config not found."}

        collected = json.loads(inst["collected_fields_json"])
        collected.update(supplied_fields)

        steps = config.get("steps", [])
        current_step_id = inst["current_step_id"]

        # Locate current step index
        step_idx = 0
        for i, s in enumerate(steps):
            if s["step_id"] == current_step_id:
                step_idx = i
                break

        current_step = steps[step_idx]
        required_fields = current_step.get("required_fields", [])

        # Check for missing fields in current step
        missing_fields = [rf for rf in required_fields if rf not in collected or collected[rf] in (None, "")]

        if missing_fields:
            execute_insert(
                "UPDATE active_workflow_instances SET collected_fields_json = ?, missing_fields_json = ?, status = 'BLOCKED', updated_at = CURRENT_TIMESTAMP WHERE instance_id = ?;",
                (json.dumps(collected), json.dumps(missing_fields), instance_id)
            )
            prompts = [self.field_definitions.get(mf, {}).get("prompt_when_missing", f"Please provide '{mf}'.") for mf in missing_fields]
            return {
                "instance_id": instance_id,
                "status": "BLOCKED",
                "current_step_id": current_step_id,
                "missing_fields": missing_fields,
                "clarification_prompts": prompts,
                "message": "Required fields are still missing. The system cannot make unsupported assumptions."
            }

        # Current step is complete! Check if tool is irreversible
        action_tool = current_step.get("action_tool")
        is_step_irreversible = current_step.get("irreversible", False)

        if is_step_irreversible:
            # Gated on Human Approval!
            approval_id = f"APPR-{datetime.now().strftime('%m%d%H%M')}-{uuid.uuid4().hex[:4].upper()}"
            required_role = config.get("approval_role", "Doctor")

            execute_insert(
                """INSERT INTO human_approval_queue 
                   (approval_id, workflow_instance_id, action_name, patient_uhid, requested_by_role, required_approver_role, action_payload_json, status, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?);""",
                (
                    approval_id, instance_id, action_tool, inst["uhid"], user_role, required_role,
                    json.dumps(collected), f"Irreversible action gate: Requires human confirmation from {required_role}."
                )
            )

            execute_insert(
                "UPDATE active_workflow_instances SET status = 'PENDING_APPROVAL', updated_at = CURRENT_TIMESTAMP WHERE instance_id = ?;",
                (instance_id,)
            )

            security_layer.log_audit_event(
                user_role=user_role,
                event_type="IRREVERSIBLE_ACTION_GATED",
                user_input=f"Triggered irreversible action '{action_tool}' in {config['name']}",
                tool_called=action_tool,
                irreversible_gated=True,
                rbac_status="GATED",
                details={"approval_id": approval_id, "required_role": required_role}
            )

            return {
                "instance_id": instance_id,
                "status": "PENDING_APPROVAL",
                "approval_id": approval_id,
                "action_tool": action_tool,
                "required_approver_role": required_role,
                "message": f"Action '{action_tool}' is tagged as irreversible and cannot be executed automatically. Human approval request #{approval_id} dispatched to {required_role} queue."
            }

        # Advance to next step or complete workflow
        if step_idx + 1 < len(steps):
            next_step = steps[step_idx + 1]
            execute_insert(
                "UPDATE active_workflow_instances SET current_step_id = ?, collected_fields_json = ?, missing_fields_json = '[]', status = 'IN_PROGRESS', updated_at = CURRENT_TIMESTAMP WHERE instance_id = ?;",
                (next_step["step_id"], json.dumps(collected), instance_id)
            )
            return {
                "instance_id": instance_id,
                "status": "IN_PROGRESS",
                "completed_step": current_step["step_name"],
                "current_step": {
                    "step_id": next_step["step_id"],
                    "step_name": next_step["step_name"],
                    "required_fields": next_step.get("required_fields", [])
                },
                "collected_fields": collected
            }
        else:
            # Workflow Completed!
            execute_insert(
                "UPDATE active_workflow_instances SET status = 'COMPLETE', missing_fields_json = '[]', updated_at = CURRENT_TIMESTAMP WHERE instance_id = ?;",
                (instance_id,)
            )
            # Advance Patient Journey state if target transition defined
            transition = config.get("target_journey_transition")
            if transition:
                self.transition_patient_journey(inst["uhid"], transition)

            return {
                "instance_id": instance_id,
                "status": "COMPLETE",
                "workflow_name": config["name"],
                "target_journey_transition": transition,
                "collected_fields": collected,
                "message": f"Workflow '{config['name']}' successfully completed."
            }

    # -------------------------------------------------------------
    # 10-STATE PATIENT JOURNEY TRANSITION ENGINE
    # -------------------------------------------------------------
    def transition_patient_journey(self, uhid: str, transition_str: str) -> Dict[str, Any]:
        """
        Advances patient lifecycle across the 10 states:
        REGISTERED -> TRIAGED -> ADMITTED -> UNDER_TREATMENT -> INVESTIGATION ->
        SURGERY -> RECOVERY -> DISCHARGE_PENDING -> DISCHARGED -> FOLLOW_UP
        """
        parts = transition_str.split("->")
        target_state = parts[-1].strip() if parts else transition_str.strip()

        now_iso = datetime.now().isoformat()
        execute_insert(
            """INSERT INTO patient_journeys (uhid, patient_name, current_state, last_transition_time, history_json)
               VALUES (?, 'Patient', ?, ?, ?)
               ON CONFLICT(uhid) DO UPDATE SET current_state = ?, last_transition_time = ?;""",
            (uhid, target_state, now_iso, json.dumps([{"state": target_state, "time": now_iso}]), target_state, now_iso)
        )
        return {"uhid": uhid, "new_state": target_state, "timestamp": now_iso}

    # -------------------------------------------------------------
    # 5-TEAM ESCALATION ROUTER (Core Bullet 4 requirement)
    # -------------------------------------------------------------
    def route_escalation(
        self,
        trigger_type: Optional[str] = None,
        ticket_id: Optional[str] = None,
        raw_query: Optional[str] = None,
        caller_role: Optional[str] = None,
        confidence_score: float = 0.5,
        summary: Optional[str] = None,
        trigger_reason: Optional[str] = None,
        uhid: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Routes requests across the 5 human teams:
        1. Account Management (account-specific cases)
        2. Clinical Review (medical advice, clinical territory)
        3. Compliance & Senior Ops (sensitive PII, MLC records, bypasses)
        4. Central Triage (unclear, ambiguous)
        5. Subject Matter Specialist Desk (low-confidence, conflicting rules)
        """
        team_map = {
            "Account-specific": ("account_management", "Account Management & Payer Liaison Team", "URGENT"),
            "Clinical": ("clinical_review", "Clinical Governance & Medical Review Board", "EMERGENCY"),
            "Sensitive": ("compliance_senior_ops", "Compliance, Legal & Senior Operations Team", "URGENT"),
            "Unclear": ("general_triage", "Central Operations Triage Desk", "ROUTINE"),
            "Low-confidence": ("subject_matter_team", "Departmental Subject-Matter Specialist Desk", "ROUTINE")
        }

        # Resolve aliases
        final_trigger = trigger_type
        if not final_trigger:
            reason_str = str(trigger_reason).lower()
            if "clinical" in reason_str or "medication" in reason_str or "dose" in reason_str:
                final_trigger = "Clinical"
            elif "account" in reason_str or "claim" in reason_str or "insurance" in reason_str:
                final_trigger = "Account-specific"
            elif "sensitive" in reason_str or "override" in reason_str:
                final_trigger = "Sensitive"
            elif "uncertain" in reason_str or "low-confidence" in reason_str:
                final_trigger = "Low-confidence"
            else:
                final_trigger = "Unclear"

        final_query = raw_query or (context.get("query") if isinstance(context, dict) else "") or trigger_reason or ""
        final_role = caller_role or (context.get("role") if isinstance(context, dict) else "Staff")
        final_ticket = ticket_id or uhid or f"TCK-{uuid.uuid4().hex[:5].upper()}"

        matched = team_map.get(final_trigger, ("general_triage", "Central Operations Triage Desk", "ROUTINE"))
        team_id, team_name, urgency = matched

        escalation_id = f"ESC-{datetime.now().strftime('%m%d%H%M')}-{uuid.uuid4().hex[:4].upper()}"
        ticket_id = final_ticket
        now_iso = datetime.now().isoformat()
        summary = summary or trigger_reason or f"Escalated {final_trigger} inquiry: {final_query[:100]}"

        # Formulate structured Escalation Brief
        brief_text = (
            f"=== STRUCTURED ESCALATION BRIEF ===\n"
            f"Ticket: {ticket_id} | Escalation ID: {escalation_id}\n"
            f"Trigger Type: {final_trigger}\n"
            f"Target Team: {team_name} (Queue ID: {team_id})\n"
            f"Urgency Level: {urgency}\n"
            f"Originator Role: {final_role} | System Confidence: {int(confidence_score * 100)}%\n"
            f"Patient / Inquiry Context: {final_query}\n"
            f"System Rationale: Request crossed explicit operational boundary for automated resolution.\n"
            f"Human Action Required: Review context, contact stakeholder, and resolve ticket in accordance with SLA.\n"
        )

        execute_insert(
            """INSERT INTO escalations_log 
               (escalation_id, ticket_id, timestamp, trigger_type, target_team_id, target_team_name, urgency_level, summary, brief_text, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_REVIEW');""",
            (escalation_id, ticket_id, now_iso, final_trigger, team_id, team_name, urgency, summary, brief_text)
        )

        # Log security audit
        security_layer.log_audit_event(
            user_role=final_role,
            event_type="ESCALATION_DISPATCHED",
            user_input=final_query,
            intent_classified=f"ESCALATE_{final_trigger.upper()}",
            confidence_score=confidence_score,
            rbac_status="ESCALATED",
            security_alert_flag=(final_trigger in ["Clinical", "Sensitive"]),
            details={"escalation_id": escalation_id, "team": team_name, "urgency": urgency}
        )

        return {
            "escalation_id": escalation_id,
            "ticket_id": ticket_id,
            "trigger_type": final_trigger,
            "target_team_id": team_id,
            "target_team_name": team_name,
            "target_team": team_name,
            "urgency_level": urgency,
            "urgency": urgency,
            "brief_text": brief_text,
            "status": "PENDING_REVIEW"
        }

# Singleton workflow engine instance
workflow_engine = WorkflowEngine()
