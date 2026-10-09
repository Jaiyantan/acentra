"""Generate 15 individual routing rule JSON index files for better semantic search."""
import json
from pathlib import Path

INDEX_DIR = Path(__file__).resolve().parent / "index"
INDEX_DIR.mkdir(exist_ok=True)

ROUTING_RULES = [
    ("R-001", "Clinical question detected", "Intent", "Medical advice or diagnosis asked", "Clinical Review", "1012", "QUEUE_CLINICAL", "urgent", 1.0, "Non-clinicians and AI systems cannot prescribe medical advice. Any clinical question or diagnosis must be routed to Clinical Review.", "What antibiotic should I prescribe?", "Does this patient need intubation?"),
    ("R-002", "Medication dosage asked", "Intent", "Dosage calculation inquiry", "Clinical Review", "1012", "QUEUE_CLINICAL", "urgent", 1.0, "Severe risk of drug toxicity if answered by non-clinician. Dosing must be verified by licensed pharmacist or physician.", "What is the pediatric dose of amikacin?", "How many units of insulin should I give?"),
    ("R-003", "Diagnosis question asked", "Intent", "Interpretation of clinical symptoms", "Clinical Review", "1012", "QUEUE_CLINICAL", "urgent", 1.0, "Diagnostic responsibility lies exclusively with licensed physician. AI cannot interpret ECG or assign diagnoses.", "Can you confirm if this ECG shows STEMI?", "What is the diagnosis for this patient?"),
    ("R-004", "Insurance claim rejected", "Data State", "Cashless claim status updated to rejected", "Insurance and TPA", "1029", "QUEUE_INSURANCE", "high", 2.0, "Requires urgent dispute filing, RFI appeal, or financial counseling. Contact Insurance TPA Desk ext. 1029.", "Claim CLM-002 rejected citing clause 4.2", "Why did Star Health deny cashless approval?"),
    ("R-005", "Pre-auth pending over 48 hours", "Time Threshold", "Pre-auth unacknowledged after 48h", "Insurance and TPA", "1029", "QUEUE_INSURANCE", "high", 2.0, "Unreasonable insurer delay threatening planned admission. Escalate to Senior Insurance Officer.", "Preauth for UHID-000002 has had no response for 2 days", "Status still submitted after 50 hours"),
    ("R-006", "Bill disputed by patient", "Intent", "Attender disputes itemized charges", "Billing", "1028", "QUEUE_BILLING", "high", 2.0, "Financial grievance requiring itemized tariff audit. Route to Billing Manager ext. 1028. Pause gate pass.", "Patient attender refuses to pay extra consumables", "Why are we being charged for ICU support?"),
    ("R-007", "UHID not found in system", "Data State", "Query yields zero results across DB", "Front Office and Registration", "1026", "QUEUE_FRONTOFFICE", "normal", 4.0, "Demographic reconciliation needed. Possible duplicate Aadhaar or typo. Contact Front Office ext. 1026.", "Cannot find patient Senthil Kumar with UHID-999999", "Patient card says UHID-000088 but no records"),
    ("R-008", "Discharge blocked by billing", "Data State", "Discharge signed but billing clearance is FALSE", "Billing", "1028", "QUEUE_BILLING", "high", 2.0, "Causes inpatient bed blockage. Discharge gate pass cannot be issued until billing is cleared. Contact Billing ext. 1028.", "Discharge for Bed 07 blocked because bill is not generated", "Nursing cleared but stuck waiting for bill"),
    ("R-009", "Critical lab result unalerted", "Data State", "critical_value_flag TRUE but doctor_alerted FALSE", "Clinical Review", "1012", "QUEUE_CLINICAL", "urgent", 0.5, "Severe patient safety hazard. Mandatory verbal readback within 15 minutes of critical result. Contact Clinical Review ext. 1012.", "Potassium 6.8 mmol/L but doctor not alerted for 30m", "Platelets under 20000 with alert unexecuted"),
    ("R-010", "Bed unavailable in requested ward", "Data State", "No vacant beds matching admission", "Operations Management", "1032", "QUEUE_FACILITY", "high", 1.0, "Requires buffer override or inter-ward transfer by Operations Manager ext. 1032.", "Zero ICU beds available for emergency patient", "Need General Ward bed but all 15 occupied"),
    ("R-011", "IT system down reported", "Incident", "Workstation or HIS connectivity failure", "IT and HIS Support", "1033", "QUEUE_IT_SUPPORT", "urgent", 1.0, "Hospital operational continuity at risk. ICU terminals get priority 1 dispatch within 15 minutes. Call IT helpline ext. 1033.", "EMR workstation in ICU Bed 02 freezing", "Cannot access HIS admission portal from counter"),
    ("R-012", "MLC case registration needed", "Event", "Trauma, poisoning, or assault presentation", "Medical Records (MRD / HIM)", "1030", "QUEUE_MRD", "urgent", 1.0, "Statutory police intimation mandatory within 1 hour for medico-legal cases. Contact Medical Records ext. 1030.", "Road traffic accident victim in emergency bay", "Suspected domestic assault requires MLC"),
    ("R-013", "Patient complaint about staff", "Grievance", "Attender registers formal service complaint", "Quality and Patient Safety", "1032", "QUEUE_QUALITY", "high", 4.0, "Patient satisfaction and NABH compliance. Log in Quality Portal, dispatch to Quality Manager ext. 1032.", "Attender complained of delay in breakfast", "Complaint regarding rude behavior at counter"),
    ("R-014", "Narcotic drug query", "Drug Schedule", "Schedule X or controlled substance query", "Clinical Review", "1012", "QUEUE_CLINICAL", "urgent", 0.5, "Statutory narcotic register compliance and dual sign-off required. Schedule X requires consultant prescription and dual-nurse witnessing. Contact Clinical Review ext. 1012.", "Need emergency dose of Inj Morphine 10mg", "How do I request Fentanyl ampoule?"),
    ("R-015", "Low confidence score under 0.6", "System Logic", "Agent confidence score below 0.60 threshold", "Front Office and Registration", "1026", "QUEUE_FRONTOFFICE", "normal", 4.0, "Ambiguous query that agent cannot resolve with confidence. Route to human triage. Contact Front Office ext. 1026.", "I need that document about the thing from last month", "Can you process the green file for room five?"),
]

created = 0
for (rule_id, trigger, trigger_type, condition, team, ext, queue, priority, sla, rationale, q1, q2) in ROUTING_RULES:
    file_id = "routing_rule_" + rule_id.lower().replace("-", "_")
    content = "\n".join([
        f"ROUTING RULE: {rule_id} -- {trigger}",
        f"TRIGGER TYPE: {trigger_type}",
        f"CONDITION: {condition}",
        f"ROUTE TO: {team} (Extension {ext})",
        f"QUEUE: {queue}",
        f"PRIORITY: {priority.upper()}",
        f"SLA: {sla} hour(s)",
        f"ESCALATION RATIONALE: {rationale}",
        f"EXAMPLE QUERY 1: {q1}",
        f"EXAMPLE QUERY 2: {q2}",
    ])
    obj = {
        "file_id": file_id,
        "title": f"Escalation Routing Rule {rule_id}: {trigger}",
        "file_path": "routing_matrix/Escalation_Routing_Matrix.xlsx",
        "file_type": "routing_rule",
        "category": "routing_rule",
        "department": team,
        "applicable_roles": ["all_staff"],
        "version": "1.0",
        "content": content,
        "tags": ["routing", "escalation", rule_id.lower(), trigger_type.lower(), queue.lower(), "smch"],
        "source_citation": f"SMCH Escalation Routing Matrix -- {rule_id} ({trigger}) v1.0",
    }
    out_path = INDEX_DIR / f"{file_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    created += 1

print(f"Created {created} routing rule index files in {INDEX_DIR}")
