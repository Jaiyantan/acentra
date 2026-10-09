"""
Tests for Hospital Workflow Engine and Human Escalation Router.
Verifies stepwise execution, missing field prompting, and team routing.
"""

from app.engine.workflow_engine import WorkflowEngine


def test_workflow_configs_loading():
    """Verifies that all JSON workflow configurations are loaded properly."""
    engine = WorkflowEngine()
    workflows = engine.get_all_workflows()
    assert len(workflows) >= 5
    # Configs can be accessed either by internal ID or by stem
    assert "admission_workflow" in engine.workflow_configs
    assert "discharge_workflow" in engine.workflow_configs


def test_missing_field_detection_and_blocking():
    """
    Core Bullet 3 requirement:
    When a required field is absent, system must set status to BLOCKED and prompt
    for the missing field instead of making unsupported assumptions.
    """
    engine = WorkflowEngine()

    # Initiate admission without bed_type or insurance_status
    result = engine.initiate_workflow(
        workflow_id="admission_workflow",
        initiator_role="Receptionist",
        uhid="UHID-000001",
        initial_fields={"admitting_doctor": "Dr. Anbarasan"}
    )

    assert result["status"] == "BLOCKED"
    assert len(result["missing_fields"]) > 0
    assert len(result["clarification_prompts"]) > 0


def test_workflow_rbac_denial():
    """Unauthorized role cannot initiate restricted workflows."""
    engine = WorkflowEngine()

    # Pharmacist attempting to initiate surgery clearance
    result = engine.initiate_workflow(
        workflow_id="surgery_clearance",
        initiator_role="Pharmacist",
        uhid="UHID-000001",
        initial_fields={}
    )

    assert result["status"] == "DENIED"
    assert "not authorized" in result["message"].lower()


def test_escalation_routing_triggers():
    """
    Verifies that clinical and sensitive escalations route to specific named teams.
    """
    engine = WorkflowEngine()

    # Route clinical query
    escalation = engine.route_escalation(
        trigger_type="Clinical",
        uhid="UHID-000001",
        summary="Doctor dosage recalculation requested for heparin infusion",
        caller_role="Nurse"
    )

    assert escalation["status"] == "PENDING_REVIEW"
    assert "clinical" in escalation["target_team_id"].lower()
    assert "Clinical" in escalation["target_team_name"]
