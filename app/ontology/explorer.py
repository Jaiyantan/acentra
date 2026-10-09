"""
SMCH Ontology Explorer
Provides two execution surfaces on top of the single ground-truth graph:
1. Surface 1: Situational Awareness & Interpretability (Command Center Dashboard Queries)
2. Surface 2: Governed Agent Workflow Interface (Guided Execution, Missing Fields, Guardrails)
"""

import re
from typing import Dict, List, Any, Optional
from .builder import get_ontology_builder, OntologyBuilder


class OntologyExplorer:
    """Exposes high-level situational awareness and governed agent traversal methods."""

    def __init__(self, builder: Optional[OntologyBuilder] = None):
        self.builder = builder or get_ontology_builder()

    # =========================================================================
    # SURFACE 1: SITUATIONAL AWARENESS & INTERPRETABILITY (COMMAND CENTER)
    # =========================================================================

    def get_cross_departmental_bottlenecks(self) -> Dict[str, Any]:
        """
        Shatters departmental silos by surfacing active operational bottlenecks
        spanning Nursing, Pharmacy, Billing, Laboratory, and Insurance TPA.
        """
        blocked_discharges = []
        for did, d in self.builder.discharges.items():
            if d.is_blocked:
                blocked_discharges.append({
                    "discharge_id": did,
                    "uhid": d.uhid,
                    "bed_id": d.bed_id,
                    "blocker_reason": d.blocker_reason,
                    "clearances": {
                        "clinical": d.clearance_clinical,
                        "pharmacy": d.clearance_pharmacy,
                        "billing": d.clearance_billing,
                        "nursing": d.clearance_nursing
                    },
                    "escalation_rule": d.escalation_rule_id,
                    "resolution_team_extension": d.resolution_team_extension,
                    "governing_sop": "SOP-DIS-001 Section 4"
                })

        panic_labs = []
        for aid, alert in self.builder.lab_critical_alerts.items():
            if alert.readback_status != "Acknowledged":
                panic_labs.append({
                    "result_id": alert.alert_id,
                    "order_id": alert.order_id,
                    "admission_id": "ADM-001",
                    "uhid": alert.uhid,
                    "test_name": alert.parameter_name,
                    "result_value": alert.critical_value,
                    "reference_range": "Critical Alert Threshold",
                    "elapsed_minutes": alert.elapsed_minutes,
                    "sla_minutes": alert.sla_minutes,
                    "is_breached": alert.is_sla_breached,
                    "governing_policy": "POL-010 Critical Panic Reporting (15-min SLA)",
                    "escalation_team": f"Clinical Review ({alert.doctor_contacted or 'ext. 1012'} / Rule R-009)"
                })
        for rid, lab in self.builder.lab_results.items():
            if lab.critical_value_flag and not lab.doctor_alerted:
                panic_labs.append({
                    "result_id": rid,
                    "order_id": lab.order_id,
                    "admission_id": lab.admission_id,
                    "uhid": lab.uhid,
                    "test_name": lab.test_name,
                    "result_value": lab.result_value,
                    "reference_range": lab.reference_range,
                    "elapsed_minutes": lab.elapsed_alert_minutes,
                    "sla_minutes": lab.alert_sla_minutes,
                    "is_breached": lab.is_sla_breached,
                    "governing_policy": "POL-010 Critical Panic Reporting",
                    "escalation_team": "Clinical Review (ext. 1012 / Rule R-009)"
                })

        rejected_claims = []
        for cid, c in self.builder.claims.items():
            if c.status == "rejected":
                rejected_claims.append({
                    "claim_id": cid,
                    "admission_id": c.admission_id,
                    "uhid": c.uhid,
                    "insurer": c.insurer,
                    "tpa": c.tpa,
                    "claim_amount": c.claim_amount,
                    "rejection_reason": c.rejection_reason,
                    "clause": c.rejection_clause,
                    "appeal_route": "Insurance and TPA (ext. 1029 / Rule R-004)"
                })

        # Bed capacity summary
        total_beds = len(self.builder.beds)
        occupied_beds = sum(1 for b in self.builder.beds.values() if b.status == "occupied")
        vacant_beds = sum(1 for b in self.builder.beds.values() if b.status == "vacant")
        dirty_beds = sum(1 for b in self.builder.beds.values() if b.status == "dirty")
        icu_total = sum(1 for b in self.builder.beds.values() if b.ward == "ICU")
        icu_occupied = sum(1 for b in self.builder.beds.values() if b.ward == "ICU" and b.status == "occupied")

        open_tickets = [
            {
                "ticket_id": t.ticket_id,
                "category": t.category,
                "severity": t.severity,
                "description": t.description,
                "department": t.department_id,
                "assigned_team": t.assigned_team
            }
            for t in self.builder.tickets.values() if t.status == "open"
        ]

        return {
            "timestamp": self.builder.last_built_at.isoformat() if self.builder.last_built_at else None,
            "blocked_discharges": blocked_discharges,
            "critical_panic_labs": panic_labs,
            "rejected_insurance_claims": rejected_claims,
            "open_incident_tickets": open_tickets,
            "bed_capacity": {
                "total_beds": total_beds,
                "occupied_beds": occupied_beds,
                "vacant_beds": vacant_beds,
                "dirty_beds": dirty_beds,
                "occupancy_rate_percent": round((occupied_beds / total_beds) * 100, 1) if total_beds else 0,
                "icu_occupancy_percent": round((icu_occupied / icu_total) * 100, 1) if icu_total else 0
            }
        }

    # =========================================================================
    # SURFACE 2: GOVERNED AGENT WORKFLOW & SAFETY INTERFACE
    # =========================================================================

    def check_safety_guardrails(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Responsible AI Guardrail:
        Strictly blocks medical advice, diagnosis, and drug dosage calculations.
        Routes immediately to human Clinical Review (TEAM-012).
        """
        q = query.lower()

        # Clinical Diagnosis / Medical Advice
        if any(term in q for term in ["what antibiotic", "prescribe", "diagnosis for this patient", "intubate", "should i give", "dose of", "dosage"]):
            return {
                "blocked": True,
                "boundary_type": "MEDICAL_ADVICE_REFUSAL",
                "reason": "AI assistant strictly forbidden from prescribing medications, calculating dosages, or giving clinical advice.",
                "triggered_rule": "R-001 / R-002",
                "escalate_to": {
                    "team": "Clinical Review",
                    "extension": "1012",
                    "sla_hours": 1.0,
                    "action": "Paged treating consultant and CMO on-call."
                },
                "response_message": (
                    "⚠️ Medical Advice Boundary: As an operations assistant, I cannot provide medical diagnoses, "
                    "treatment advice, or medication dosages. This request has been escalated to "
                    "Clinical Review (ext. 1012 / Rule R-001) for immediate physician review."
                )
            }

        # Narcotic Drugs
        if any(term in q for term in ["morphine", "fentanyl", "pethidine", "narcotic", "schedule x"]):
            return {
                "blocked": True,
                "boundary_type": "SCHEDULE_X_NARCOTIC_RESTRICTION",
                "reason": "Narcotic drug requisition requires physical dual-witness registration.",
                "triggered_rule": "R-014",
                "escalate_to": {
                    "team": "Clinical Review & Central Pharmacy",
                    "extension": "1012 / 1023",
                    "sla_hours": 0.5,
                    "action": "Dual-nurse bedside witnessing and vault log required."
                },
                "response_message": (
                    "🔒 Schedule X Narcotic Restriction: In accordance with SOP-PHM-002 and Rule R-014, "
                    "narcotics require physical senior consultant requisition and dual-nurse bedside witnessing. "
                    "Contact Central Pharmacy (ext. 1023) or Clinical Review (ext. 1012)."
                )
            }

        return None

    def validate_workflow_inputs(self, workflow_id: str, step_number: int,
                                 provided_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates input parameters against graph field schemas and identifies missing fields.
        """
        step_id = f"{workflow_id}_STEP_{step_number}"
        step_node = self.builder.workflow_steps.get(step_id)

        if not step_node:
            return {
                "valid": False,
                "error": f"Workflow step {step_id} not found in ontology."
            }

        missing_fields = []
        validation_errors = []

        for f_name in step_node.required_fields:
            # Handle comma separated in some schemas
            for actual_f in [x.strip() for x in f_name.split(",")]:
                if not actual_f:
                    continue
                val = provided_inputs.get(actual_f)
                field_def = self.builder.field_definitions.get(actual_f)

                if val is None or val == "":
                    missing_fields.append({
                        "field_name": actual_f,
                        "display_name": field_def.display_name if field_def else actual_f,
                        "prompt": field_def.on_missing_message if field_def else f"Please provide {actual_f}."
                    })
                elif field_def and field_def.validation_pattern:
                    if not re.match(field_def.validation_pattern, str(val)):
                        validation_errors.append({
                            "field_name": actual_f,
                            "invalid_value": val,
                            "pattern": field_def.validation_pattern,
                            "error": f"Invalid format for {field_def.display_name}. Expected pattern: {field_def.validation_pattern}"
                        })

        is_valid = (len(missing_fields) == 0 and len(validation_errors) == 0)

        return {
            "valid": is_valid,
            "step_id": step_id,
            "step_name": step_node.step_name,
            "actor_role": step_node.actor_role,
            "simulation_endpoint": step_node.simulation_endpoint,
            "requires_human_approval": step_node.requires_human_approval,
            "missing_fields": missing_fields,
            "validation_errors": validation_errors,
            "blockers": step_node.blockers,
            "escalation_rule_id": step_node.escalation_rule_id
        }

    def query_cross_department_context(self, uhid: str) -> Dict[str, Any]:
        """
        Solves the Context Fragmentation Problem for a specific patient.
        Aggregates Bed, Admission, Orders, Lab Results, Billing, Claims, and Discharges in one unified view.
        """
        patient = self.builder.patients.get(uhid)
        if not patient:
            return {"error": f"UHID {uhid} not found in hospital ontology."}

        # Find active admission
        adm = None
        for a in self.builder.admissions.values():
            if a.uhid == uhid and a.status == "active":
                adm = a
                break

        # Find bed
        bed = self.builder.beds.get(patient.current_bed_id) if patient.current_bed_id else None

        # Find bills
        bills = [b for b in self.builder.bills.values() if b.uhid == uhid]

        # Find claims
        claims = [c for c in self.builder.claims.values() if c.uhid == uhid]

        # Find orders & labs
        orders = [o for o in self.builder.orders.values() if o.uhid == uhid]
        labs = [l for l in self.builder.lab_results.values() if l.uhid == uhid]

        # Find discharge record
        discharge = None
        for d in self.builder.discharges.values():
            if d.uhid == uhid:
                discharge = d
                break

        return {
            "patient": {
                "uhid": patient.uhid,
                "name": patient.name,
                "age": patient.age,
                "gender": patient.gender,
                "status": patient.status
            },
            "location": {
                "bed_id": bed.bed_id if bed else None,
                "ward": bed.ward if bed else None,
                "department": bed.department_id if bed else None,
                "bed_status": bed.status if bed else None
            },
            "admission": {
                "admission_id": adm.admission_id if adm else None,
                "diagnosis": adm.admitting_diagnosis if adm else None,
                "admitting_doctor": adm.admitting_doctor_id if adm else None,
                "admission_date": adm.admission_date if adm else None
            },
            "discharge_status": {
                "discharge_id": discharge.discharge_id if discharge else None,
                "is_blocked": discharge.is_blocked if discharge else False,
                "blocker_reason": discharge.blocker_reason if discharge else None,
                "clearance_clinical": discharge.clearance_clinical if discharge else None,
                "clearance_pharmacy": discharge.clearance_pharmacy if discharge else None,
                "clearance_billing": discharge.clearance_billing if discharge else None,
                "clearance_nursing": discharge.clearance_nursing if discharge else None,
                "gate_pass_issued": discharge.gate_pass_issued if discharge else False
            },
            "billing_summary": [
                {
                    "bill_id": b.bill_id,
                    "total": b.total_amount,
                    "paid": b.paid_amount,
                    "pending": b.pending_amount,
                    "has_dispute": b.has_billing_dispute,
                    "unbilled_consumables": b.unbilled_consumables
                }
                for b in bills
            ],
            "insurance_claims": [
                {
                    "claim_id": c.claim_id,
                    "insurer": c.insurer,
                    "status": c.status,
                    "rejection_reason": c.rejection_reason
                }
                for c in claims
            ],
            "critical_labs": [
                {
                    "result_id": l.result_id,
                    "test_name": l.test_name,
                    "result_value": l.result_value,
                    "critical_flag": l.critical_value_flag,
                    "doctor_alerted": l.doctor_alerted
                }
                for l in labs if l.critical_value_flag
            ]
        }


# Singleton accessor
_explorer_instance: Optional[OntologyExplorer] = None

def get_ontology_explorer() -> OntologyExplorer:
    global _explorer_instance
    if _explorer_instance is None:
        _explorer_instance = OntologyExplorer()
    return _explorer_instance
