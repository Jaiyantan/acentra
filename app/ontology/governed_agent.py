"""
SMCH Governed Action Layer — Surface 2
========================================
Operational AI agent traversing the live ontology graph to answer frontline
staff questions. Guardrails are code-based (no LLM). LLM only synthesizes
final answers from structured graph context.

Key design constraints:
- Never let LLM access raw patient data directly — assemble context in Python first
- Medical advice queries are refused before reaching LLM
- Escalation paths and SOP citations come from the typed graph, not LLM memory
- Irreversible actions are flagged for human approval, never auto-executed
"""

import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


# ─────────────────────────────────────────────────────────────────────────────
# GUARDRAIL RULES (code-based, zero LLM)
# ─────────────────────────────────────────────────────────────────────────────

MEDICAL_ADVICE_KEYWORDS = [
    "dose", "dosage", "mg", "ml", "insulin", "medication order", "prescribe",
    "administer", "inject", "drug", "antibiotic", "treat", "treatment plan",
    "diagnosis", "clinical decision", "what medicine", "which drug",
]

IRREVERSIBLE_KEYWORDS = [
    "delete bill", "cancel admission", "reverse discharge", "write off",
    "write-off", "permanently remove", "force discharge",
]

MEDICAL_ADVICE_RESPONSE = {
    "guardrail": "MEDICAL_ADVICE",
    "answer": (
        "I cannot provide clinical or medication advice. "
        "This query must be directed to the treating physician or Clinical Review team."
    ),
    "escalation": "Clinical Review — Ext. 1012",
    "rule": "R-001",
    "requires_human_approval": False,
    "policy_citations": ["POL-CLIN-001 — Clinical Decision Authority"],
}

IRREVERSIBLE_RESPONSE = {
    "guardrail": "IRREVERSIBLE_ACTION",
    "answer": (
        "This action requires explicit authorization from a supervisor. "
        "I have flagged it for human approval — it cannot be auto-executed."
    ),
    "escalation": "Operations Manager — Ext. 1001",
    "rule": "R-007",
    "requires_human_approval": True,
    "policy_citations": ["POL-OPS-007 — Irreversible Action Approval Gate"],
}


# ─────────────────────────────────────────────────────────────────────────────
# ESCALATION ROUTES — 5 named teams per feature checklist requirement 6
# ─────────────────────────────────────────────────────────────────────────────

ESCALATION_ROUTES = {
    "MEDICAL_ADVICE": {
        "team": "Clinical Review Team",
        "extension": "Ext. 1012",
        "rule": "R-001",
        "policy": "POL-CLIN-001 — Clinical Decision Authority",
        "requires_human_approval": False,
    },
    "IRREVERSIBLE_ACTION": {
        "team": "Operations Manager",
        "extension": "Ext. 1001",
        "rule": "R-007",
        "policy": "POL-OPS-007 — Irreversible Action Approval Gate",
        "requires_human_approval": True,
    },
    "ACCOUNT_SPECIFIC": {
        "team": "Account Management Team",
        "extension": "Ext. 1020",
        "rule": "R-003",
        "policy": "POL-ACC-003 — Account-Specific Data Access",
        "requires_human_approval": False,
    },
    "SENSITIVE": {
        "team": "Compliance / Senior Ops",
        "extension": "Ext. 1030",
        "rule": "R-005",
        "policy": "POL-COMP-005 — Sensitive Data Handling",
        "requires_human_approval": False,
    },
    "UNCLEAR": {
        "team": "General Triage Team",
        "extension": "Ext. 1000",
        "rule": "R-009",
        "policy": "POL-OPS-009 — Unclear Request Handling",
        "requires_human_approval": False,
    },
    "LOW_CONFIDENCE": {
        "team": "Subject Matter Expert",
        "extension": "Ext. 1010",
        "rule": "R-010",
        "policy": "POL-OPS-010 — Low-Confidence Response Protocol",
        "requires_human_approval": False,
    },
    "PROMPT_INJECTION": {
        "team": "Security Operations",
        "extension": "Ext. 1099",
        "rule": "R-INJ-001",
        "policy": "POL-SEC-001 — Prompt Injection and Access Bypass Prevention",
        "requires_human_approval": True,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# HOSPITAL DIRECTORY — internal extension lookup
# ─────────────────────────────────────────────────────────────────────────────

HOSPITAL_CONTACTS = {
    "central billing":    {"ext": "1028", "name": "Central Billing"},
    "billing":            {"ext": "1028", "name": "Central Billing"},
    "pharmacy":           {"ext": "1023", "name": "Pharmacy"},
    "clinical":           {"ext": "1012", "name": "Clinical Review Team"},
    "clinical review":    {"ext": "1012", "name": "Clinical Review Team"},
    "nursing":            {"ext": "1031", "name": "Nursing Station"},
    "ward nurse":         {"ext": "1031", "name": "Nursing Station"},
    "operations":         {"ext": "1001", "name": "Operations Manager"},
    "operations manager": {"ext": "1001", "name": "Operations Manager"},
    "triage":             {"ext": "1000", "name": "General Triage"},
    "compliance":         {"ext": "1020", "name": "Compliance & Senior Operations"},
    "security":           {"ext": "1020", "name": "Security & Compliance"},
    "sme":                {"ext": "1025", "name": "Subject Matter Expert Queue"},
    "account management": {"ext": "1015", "name": "Account Management Team"},
    "radiology":          {"ext": "1040", "name": "Radiology"},
    "lab":                {"ext": "1035", "name": "Laboratory"},
    "laboratory":         {"ext": "1035", "name": "Laboratory"},
    "blood bank":         {"ext": "1036", "name": "Blood Bank"},
    "icu":                {"ext": "1045", "name": "ICU"},
    "emergency":          {"ext": "1050", "name": "Emergency"},
    "discharge":          {"ext": "1028", "name": "Central Billing (Discharge Settlement)"},
}

_CONTACT_SIGNALS = [
    "how do i contact", "how to contact", "extension for", "ext for",
    "contact number", "phone number for", "how can i reach",
    "who do i call for", "how do i reach", "what is the number for",
    "what extension", "dial for",
]

# ─────────────────────────────────────────────────────────────────────────────
# RBAC — Role-Based Access Control
# ─────────────────────────────────────────────────────────────────────────────

ROLES = {
    "ADMIN":         {"label": "Administrator",      "color": "#6366F1"},
    "DOCTOR":        {"label": "Doctor / Clinician",  "color": "#10B981"},
    "NURSE":         {"label": "Ward Nurse",          "color": "#3B82F6"},
    "BILLING_STAFF": {"label": "Billing Staff",       "color": "#F59E0B"},
}

ROLE_DENY = {
    "DOCTOR":        ["claim_amount", "tpa", "billing", "invoice", "payment", "revenue",
                      "financial", "insurance claim", "rejected claim"],
    "NURSE":         ["claim_amount", "tpa", "billing", "invoice", "payment", "revenue",
                      "financial", "insurance claim", "rejected claim",
                      "salary", "staff payment"],
    "BILLING_STAFF": ["lab result", "lab value", "critical value", "clinical diagnosis",
                      "medication", "prescription", "doctor note", "clinical detail"],
}

# Whitelist of graph sections each role may receive in assembled context
ROLE_VISIBLE_NODE_TYPES = {
    "ADMIN": None,  # None = unrestricted
    "DOCTOR": {
        "patients", "admissions", "discharges", "lab_critical_alerts",
        "lab_results", "prescriptions", "beds", "sops", "policies", "articles",
    },
    "NURSE": {
        "patients", "beds", "admissions", "discharges",
        "lab_critical_alerts", "sops", "articles",
    },
    "BILLING_STAFF": {
        "claims", "bills", "patients", "sops", "articles",
    },
}

# Regex patterns: lines matching ANY of these are stripped from graph context for that role
ROLE_STRIP_PATTERNS = {
    "DOCTOR": [
        r"Claim [A-Z0-9\-]+:.*",
        r"\bTPA\b.*:.*",
        r"Amount:.*[₹\d]",
        r"Bill [A-Z0-9\-]+:.*",
        r"claim_amount",
        r"revenue",
    ],
    "NURSE": [
        r"Claim [A-Z0-9\-]+:.*",
        r"\bTPA\b.*:.*",
        r"Amount:.*[₹\d]",
        r"Bill [A-Z0-9\-]+:.*",
        r"Parameter:.*=.*",
        r"Critical Value:.*",
    ],
    "BILLING_STAFF": [
        r"Diagnosis:.*",
        r"Parameter:.*=.*",
        r"Critical Value:.*",
        r"Readback:.*",
        r"SLA:.*elapsed.*",
        r"Doctor:.*Ext\.",
    ],
}


def filter_graph_context_by_role(context: str, role: str) -> str:
    """Strip lines from assembled graph context that the given role cannot see.

    Real data-level RBAC: the LLM never receives fields the role isn't allowed
    to see, regardless of how the query is phrased.
    """
    if not role or role == "ADMIN" or not context:
        return context
    patterns = ROLE_STRIP_PATTERNS.get(role, [])
    if not patterns:
        return context
    lines = context.split("\n")
    filtered = []
    for line in lines:
        blocked = any(re.search(p, line, re.IGNORECASE) for p in patterns)
        if not blocked:
            filtered.append(line)
    header = f"[RBAC: context filtered for role={role} — restricted fields redacted]\n"
    return header + "\n".join(filtered)


def check_rbac(query: str, role: str) -> Optional[Dict[str, Any]]:
    """Return a denial response if the role is not permitted to access the requested data."""
    if not role or role == "ADMIN":
        return None
    deny_terms = ROLE_DENY.get(role, [])
    q = query.lower()
    matched = next((t for t in deny_terms if t in q), None)
    if matched:
        try:
            from app.ontology.shared_state import audit as _audit
            _audit("RBAC_DENY", role, f"denied: {matched}", f"Query: {query[:80]}", role)
        except Exception:
            pass
        return {
            "query": query,
            "guardrail_triggered": "RBAC_DENY",
            "answer": (
                f"Your role ({ROLES.get(role, {}).get('label', role)}) does not have access to "
                f"'{matched}' information. This request has been logged."
            ),
            "confidence": {"level": "N/A", "reason": "Access denied by role-based policy."},
            "source_citations": [],
            "requires_human_approval": False,
            "workflow_step": None,
            "missing_fields": [],
            "escalation": "Compliance & Senior Operations — Ext. 1020",
            "escalation_reason": f"Role {role} attempted to access restricted data: {matched}",
            "graph_context_used": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    return None

# ─────────────────────────────────────────────────────────────────────────────
# PROMPT INJECTION DETECTION — requirement 9
# ─────────────────────────────────────────────────────────────────────────────

PROMPT_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "ignore your instructions",
    "disregard previous",
    "disregard all previous",
    "forget your instructions",
    "forget previous",
    "you are now",
    "act as if you are",
    "pretend you are",
    "pretend to be",
    "jailbreak",
    "bypass guardrails",
    "bypass restrictions",
    "override policy",
    "reveal your prompt",
    "show your system prompt",
    "what are your instructions",
    "repeat your instructions",
]

SENSITIVE_KEYWORDS = [
    "salary", "employee record", "staff file", "personal record",
    "resignation", "termination", "disciplinary",
    "investigation", "complaint against",
    "password", "credentials", "login",
    "financial record", "bank account",
]

ACCOUNT_KEYWORDS = [
    "my account", "my profile", "my details", "my record",
    "my bills", "my balance", "my claim", "my insurance",
    "change my", "update my", "reset my",
]

# ─────────────────────────────────────────────────────────────────────────────
# DISCHARGE WORKFLOW — requirements 4, 5
# ─────────────────────────────────────────────────────────────────────────────

DISCHARGE_WORKFLOW_STEPS = [
    {
        "step": 1,
        "name": "Clinical Clearance",
        "description": "Treating physician must sign off on clinical clearance.",
        "field": "clearance_clinical",
        "responsible_team": "Clinical Team",
        "extension": "Ext. 1012",
    },
    {
        "step": 2,
        "name": "Pharmacy Clearance",
        "description": "Pharmacy must confirm all medications returned or dispensed.",
        "field": "clearance_pharmacy",
        "responsible_team": "Pharmacy",
        "extension": "Ext. 1015",
    },
    {
        "step": 3,
        "name": "Billing Clearance",
        "description": "Billing must settle all outstanding dues.",
        "field": "clearance_billing",
        "responsible_team": "Billing Team",
        "extension": "Ext. 1020",
    },
    {
        "step": 4,
        "name": "Gate Pass Issue",
        "description": "Once all clearances obtained, gate pass is issued.",
        "field": "gate_pass_issued",
        "responsible_team": "Discharge Desk",
        "extension": "Ext. 1005",
    },
]

WORKFLOW_TRIGGERS = {
    "discharge": [
        "discharge process", "how to discharge", "discharge workflow",
        "steps to discharge", "discharge steps", "discharge procedure",
        "gate pass process", "how is discharge done",
    ],
    "admission": [
        "how to admit", "admission process", "admission workflow",
        "steps to admit", "admission steps", "admit patient",
    ],
}

WORKFLOW_REQUIRED_FIELDS = {
    "discharge": {
        "clearance_clinical": "Clinical sign-off from treating physician",
        "clearance_pharmacy": "Pharmacy clearance confirmation",
        "clearance_billing": "Billing clearance — all dues settled",
        "gate_pass_issued": "Gate pass printed and issued to patient",
    },
    "admission": {
        "uhid": "Patient UHID (or new patient registration)",
        "admitting_doctor_id": "Admitting doctor ID",
        "admitting_diagnosis": "Admitting diagnosis",
        "bed_id": "Assigned bed ID",
    },
}


def check_guardrails(query: str) -> Optional[Dict[str, Any]]:
    """Returns a guardrail response dict if triggered, else None (safe to proceed)."""
    q = query.lower()

    # 1. Prompt injection / access bypass — requirement 9
    if any(pattern in q for pattern in PROMPT_INJECTION_PATTERNS):
        route = ESCALATION_ROUTES["PROMPT_INJECTION"]
        return {
            "guardrail": "PROMPT_INJECTION",
            "answer": (
                "This request appears to contain an attempt to bypass system instructions or access controls. "
                "It has been flagged and logged. If this was accidental, please rephrase your question."
            ),
            "escalation": f"{route['team']} — {route['extension']}",
            "escalation_reason": "Pattern matched a known prompt injection or access bypass technique.",
            "rule": route["rule"],
            "requires_human_approval": route["requires_human_approval"],
            "policy_citations": [route["policy"]],
        }

    # 2. Medical advice — requirement 7
    if any(kw in q for kw in MEDICAL_ADVICE_KEYWORDS):
        route = ESCALATION_ROUTES["MEDICAL_ADVICE"]
        return {
            "guardrail": "MEDICAL_ADVICE",
            "answer": (
                "I cannot provide clinical or medication advice. "
                "This query must be directed to the treating physician or Clinical Review team."
            ),
            "escalation": f"{route['team']} — {route['extension']}",
            "escalation_reason": "Query contains clinical or medication keywords requiring physician oversight.",
            "rule": route["rule"],
            "requires_human_approval": route["requires_human_approval"],
            "policy_citations": [route["policy"]],
        }

    # 3. Irreversible actions — requirement 10
    if any(kw in q for kw in IRREVERSIBLE_KEYWORDS):
        route = ESCALATION_ROUTES["IRREVERSIBLE_ACTION"]
        return {
            "guardrail": "IRREVERSIBLE_ACTION",
            "answer": (
                "This action requires explicit authorization from a supervisor. "
                "I have flagged it for human approval — it cannot be auto-executed."
            ),
            "escalation": f"{route['team']} — {route['extension']}",
            "escalation_reason": "Request involves an irreversible operation that cannot be auto-executed per policy.",
            "rule": route["rule"],
            "requires_human_approval": route["requires_human_approval"],
            "policy_citations": [route["policy"]],
        }

    # 4. Sensitive personal / employee data — requirement 8
    if any(kw in q for kw in SENSITIVE_KEYWORDS):
        route = ESCALATION_ROUTES["SENSITIVE"]
        return {
            "guardrail": "SENSITIVE",
            "answer": (
                "This request touches sensitive employee or financial records. "
                "Please contact the Compliance team for assistance."
            ),
            "escalation": f"{route['team']} — {route['extension']}",
            "escalation_reason": "Query involves sensitive personal or financial data outside operational scope.",
            "rule": route["rule"],
            "requires_human_approval": route["requires_human_approval"],
            "policy_citations": [route["policy"]],
        }

    # 5. Account-specific requests — requirement 6
    if any(kw in q for kw in ACCOUNT_KEYWORDS):
        route = ESCALATION_ROUTES["ACCOUNT_SPECIFIC"]
        return {
            "guardrail": "ACCOUNT_SPECIFIC",
            "answer": (
                "Account-specific requests must be handled by the Account Management team. "
                "Please contact them directly for assistance with your account."
            ),
            "escalation": f"{route['team']} — {route['extension']}",
            "escalation_reason": "Request is account-specific and requires Account Management team handling.",
            "rule": route["rule"],
            "requires_human_approval": route["requires_human_approval"],
            "policy_citations": [route["policy"]],
        }

    return None


# ─────────────────────────────────────────────────────────────────────────────
# ENTITY EXTRACTION (code-based, regex)
# ─────────────────────────────────────────────────────────────────────────────

def extract_entities(query: str) -> Dict[str, List[str]]:
    """Extract typed entity IDs from natural language query."""
    uhids = re.findall(r'\bSMCH-\d{6}\b', query, re.IGNORECASE)
    bed_ids = re.findall(r'\b(?:Ward\w+-B\d+|BED-\w+|ICU-\w+)\b', query, re.IGNORECASE)
    alert_ids = re.findall(r'\bCRIT-ALRT-\w+\b', query, re.IGNORECASE)
    discharge_ids = re.findall(r'\bDIS-ADM-\w+\b', query, re.IGNORECASE)
    admission_ids = re.findall(r'\bADM-\w+\b', query, re.IGNORECASE)
    claim_ids = re.findall(r'\bCLM-\w+\b', query, re.IGNORECASE)
    bill_ids = re.findall(r'\bINV-\w+\b', query, re.IGNORECASE)
    return {
        "uhids": [u.upper() for u in uhids],
        "bed_ids": [b.upper() for b in bed_ids],
        "alert_ids": [a.upper() for a in alert_ids],
        "discharge_ids": [d.upper() for d in discharge_ids],
        "admission_ids": [a.upper() for a in admission_ids],
        "claim_ids": [c.upper() for c in claim_ids],
        "bill_ids": [b.upper() for b in bill_ids],
    }


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH CONTEXT ASSEMBLY (reads OntologyBuilder — live state)
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_bool(v: bool) -> str:
    return "Yes" if v else "No"


def _fmt_inr(v: float) -> str:
    return f"Rs {v:,.2f}"


def build_patient_context(uhid: str, builder) -> str:
    """Full 360° context for a patient from the live graph."""
    pat = builder.patients.get(uhid)
    if not pat:
        return f"Patient {uhid}: not found in operational graph."

    lines = [
        f"PATIENT: {pat.name}, {pat.age}y {pat.gender} | UHID: {uhid}",
        f"Status: {pat.status}",
    ]

    bed = builder.beds.get(pat.current_bed_id) if pat.current_bed_id else None
    if bed:
        lines.append(f"Bed: {bed.bed_id} ({bed.ward}) | Bed Status: {bed.status}")
    else:
        lines.append("Bed: Not currently admitted")

    adm = next((a for a in builder.admissions.values() if a.uhid == uhid), None)
    if adm:
        lines.append(f"Admission: {adm.admission_id} | Doctor: {adm.admitting_doctor_id} | Diagnosis: {adm.admitting_diagnosis}")

    dis = next((d for d in builder.discharges.values() if d.uhid == uhid), None)
    if dis:
        status_label = "BLOCKED" if dis.is_blocked else "CLEAR"
        lines.append(f"Discharge [{status_label}]: {dis.discharge_id}")
        lines.append(f"  Clinical: {_fmt_bool(dis.clearance_clinical)} | Pharmacy: {_fmt_bool(dis.clearance_pharmacy)} | Billing: {_fmt_bool(dis.clearance_billing)}")
        if dis.is_blocked:
            lines.append(f"  BLOCKER: {dis.blocker_reason}")
            lines.append(f"  Escalation: {dis.resolution_team_extension}")
        if dis.gate_pass_issued:
            lines.append("  Gate Pass: ISSUED")

    bills = [b for b in builder.bills.values() if b.uhid == uhid]
    for bill in bills[:2]:
        lines.append(f"Bill {bill.bill_id}: Total {_fmt_inr(bill.total_amount)} | Pending: {_fmt_inr(bill.pending_amount)} | Dispute: {_fmt_bool(bill.has_billing_dispute)}")
        if bill.unbilled_consumables > 0:
            lines.append(f"  Unbilled consumables: {_fmt_inr(bill.unbilled_consumables)}")

    alerts = [a for a in builder.lab_critical_alerts.values() if a.uhid == uhid]
    for alert in alerts[:2]:
        sla_status = "SLA BREACHED" if alert.is_sla_breached else f"{alert.elapsed_minutes:.0f}m elapsed"
        lines.append(f"Panic Alert {alert.alert_id}: {alert.parameter_name} = {alert.critical_value} | {sla_status} | Readback: {alert.readback_status}")

    claims = [c for c in builder.claims.values() if c.uhid == uhid]
    for claim in claims[:1]:
        lines.append(f"Claim {claim.claim_id}: {claim.tpa} | Status: {claim.status} | Amount: {_fmt_inr(claim.claim_amount)}")

    return "\n".join(lines)


def build_discharge_context(discharge_id: str, builder) -> str:
    dis = builder.discharges.get(discharge_id)
    if not dis:
        return f"Discharge {discharge_id}: not found."
    pat = builder.patients.get(dis.uhid)
    pat_name = pat.name if pat else dis.uhid
    lines = [
        f"DISCHARGE {discharge_id} — Patient: {pat_name} ({dis.uhid})",
        f"Status: {'BLOCKED' if dis.is_blocked else 'CLEAR'} | Gate Pass: {'Issued' if dis.gate_pass_issued else 'Pending'}",
        f"Clinical: {_fmt_bool(dis.clearance_clinical)} | Pharmacy: {_fmt_bool(dis.clearance_pharmacy)} | Billing: {_fmt_bool(dis.clearance_billing)}",
    ]
    if dis.is_blocked:
        lines.append(f"BLOCKER: {dis.blocker_reason}")
        lines.append(f"Escalation: {dis.resolution_team_extension}")
    return "\n".join(lines)


def build_alert_context(alert_id: str, builder) -> str:
    alert = builder.lab_critical_alerts.get(alert_id)
    if not alert:
        return f"Alert {alert_id}: not found."
    pat = builder.patients.get(alert.uhid)
    pat_name = pat.name if pat else alert.uhid
    lines = [
        f"PANIC ALERT {alert_id} — Patient: {pat_name} ({alert.uhid})",
        f"Test: {alert.parameter_name} = {alert.critical_value}",
        f"Doctor: {alert.doctor_contacted} | Readback: {alert.readback_status}",
        f"SLA: {alert.elapsed_minutes:.0f} min elapsed / {alert.sla_minutes:.0f} min limit | Breached: {_fmt_bool(alert.is_sla_breached)}",
        f"Policy: POL-010 — Critical Value 15-Minute Readback Mandate | Paging Rule: R-009",
    ]
    return "\n".join(lines)


def build_bed_context(bed_id: str, builder) -> str:
    bed = builder.beds.get(bed_id)
    if not bed:
        for k, v in builder.beds.items():
            if k.upper() == bed_id.upper():
                bed = v
                break
    if not bed:
        return f"Bed {bed_id}: not found."
    lines = [f"BED {bed.bed_id} — Ward: {bed.ward} | Status: {bed.status}"]
    if bed.current_patient_uhid:
        pat = builder.patients.get(bed.current_patient_uhid)
        if pat:
            lines.append(f"Occupied by: {pat.name} ({bed.current_patient_uhid})")
    return "\n".join(lines)


def _find_patients_by_name(query: str, builder) -> List[str]:
    """Find UHIDs by partial name match — requires at least 2 name words to match."""
    words = [w.lower() for w in query.split() if len(w) > 2]
    results = []
    for uhid, pat in builder.patients.items():
        pname = (pat.name or "").lower()
        if sum(1 for w in words if w in pname) >= min(2, len(words)):
            results.append(uhid)
    return results


def _extract_ward_from_query(query: str) -> Optional[str]:
    """Extract ward identifier from a natural language query."""
    # Strip punctuation that users type in place of spaces (#, @, -)
    q = re.sub(r'[#@*!]', ' ', query.lower()).strip()
    # Match "ward 3a", "ward3a", "ward a", "3a ward"
    m = re.search(r'ward\s*([a-z0-9]+)', q)
    if m:
        return f"ward {m.group(1)}"
    m = re.search(r'([a-z0-9]+)\s*ward', q)
    if m and len(m.group(1)) <= 4:
        return f"ward {m.group(1)}"
    # Dedicated units — use word boundary to avoid "ccu" matching inside "occupancy"
    for unit in ["icu", "ccu", "nicu", "picu", "emergency", "recovery"]:
        if re.search(r'\b' + unit + r'\b', q):
            return unit
    return None


def _extract_gender_filter(query: str) -> Optional[str]:
    q = query.lower()
    if "female" in q or "women" in q or "woman" in q or "lady" in q or "ladies" in q:
        return "female"
    if "male" in q or "men " in q or "man " in q:
        return "male"
    return None


def assemble_graph_context(entities: Dict[str, List[str]], query: str, builder) -> str:
    """Build structured fact context from the live graph based on extracted entities."""
    parts = []
    # Track which discharge IDs have already been rendered inside patient context
    shown_discharge_ids: set = set()

    for uhid in entities["uhids"][:3]:
        parts.append(build_patient_context(uhid, builder))
        # Mark discharge as shown so we don't duplicate it below
        dis = next((d for d in builder.discharges.values() if d.uhid == uhid), None)
        if dis:
            shown_discharge_ids.add(dis.discharge_id)

    for dis_id in entities["discharge_ids"][:3]:
        if dis_id not in shown_discharge_ids:
            parts.append(build_discharge_context(dis_id, builder))
            shown_discharge_ids.add(dis_id)

    for alert_id in entities["alert_ids"][:2]:
        parts.append(build_alert_context(alert_id, builder))

    # Skip bed context if we already showed the patient occupying that bed
    shown_uhids = set(entities["uhids"][:3])
    for bed_id in entities["bed_ids"][:2]:
        bed = builder.beds.get(bed_id) or next(
            (b for b in builder.beds.values() if b.bed_id.upper() == bed_id.upper()), None
        )
        if bed and bed.current_patient_uhid in shown_uhids:
            continue  # patient context already shown
        parts.append(build_bed_context(bed_id, builder))

    PROCEDURAL_SIGNALS = ["procedure", "protocol", "sop", "how to", "what steps", "steps to",
                          "steps for", "what is the sop", "what is the procedure", "what is the protocol"]
    is_explicit_procedural = any(sig in query.lower() for sig in PROCEDURAL_SIGNALS)

    if not parts and not is_explicit_procedural:
        q = query.lower()

        # ── 1. Name-based patient lookup ────────────────────────────────────
        # Detect capitalized proper names in the query (e.g. "Geetha Kuppuswamy")
        name_matches = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+', query)
        name_uhids: List[str] = []
        for name in name_matches[:2]:
            found = _find_patients_by_name(name, builder)
            name_uhids.extend(found[:2])
        if name_uhids:
            for uhid in name_uhids[:2]:
                parts.append(build_patient_context(uhid, builder))

        # ── 2. Ward-based lookup ────────────────────────────────────────────
        elif (ward := _extract_ward_from_query(query)) is not None:
            gender_filter = _extract_gender_filter(query)
            ward_patients = []
            ward_str = ward.lower()
            for bed in builder.beds.values():
                if ward_str not in bed.ward.lower():
                    continue
                if not bed.current_patient_uhid:
                    continue
                pat = builder.patients.get(bed.current_patient_uhid)
                if not pat:
                    continue
                if gender_filter and (pat.gender or "").lower() != gender_filter:
                    continue
                ward_patients.append((bed, pat))

            if ward_patients:
                gender_label = f" ({gender_filter})" if gender_filter else ""
                parts.append(f"PATIENTS IN {ward.upper()}{gender_label} ({len(ward_patients)} total):")
                for bed, pat in ward_patients:  # no artificial cap
                    dis = next((d for d in builder.discharges.values() if d.uhid == pat.uhid), None)
                    dis_flag = " [DISCHARGE BLOCKED]" if (dis and dis.is_blocked) else ""
                    parts.append(f"  {pat.uhid} — {pat.name}, {getattr(pat, 'age', '?')}y {pat.gender} | Bed: {bed.bed_id}{dis_flag}")
            else:
                parts.append(f"No patients found in {ward.upper()} matching your criteria.")

        # ── 3. Blocked discharge lookup ─────────────────────────────────────
        elif any(kw in q for kw in ["blocked discharge", "discharge blocked", "gate pass", "clearance",
                                    "not printing", "why blocked"]) or \
             (("discharge" in q or "blocked" in q) and any(kw in q for kw in ["how many", "list", "show", "count", "which", "pending"])):
            blocked = [d for d in builder.discharges.values() if d.is_blocked]
            if blocked:
                parts.append(f"BLOCKED DISCHARGES ({len(blocked)} total):")
                for d in blocked[:5]:
                    pat = builder.patients.get(d.uhid)
                    pname = pat.name if pat else d.uhid
                    parts.append(f"  {d.discharge_id} — {pname}: {d.blocker_reason}")
            else:
                parts.append("BLOCKED DISCHARGES: None currently blocked.")

        # ── 4. Panic / SLA alerts ────────────────────────────────────────────
        elif any(kw in q for kw in ["panic", "critical", "sla", "readback", "breached"]):
            breached = [a for a in builder.lab_critical_alerts.values() if a.is_sla_breached]
            if breached:
                parts.append(f"SLA-BREACHED PANIC ALERTS ({len(breached)} total):")
                for a in breached[:5]:
                    parts.append(f"  {a.alert_id}: {a.parameter_name} = {a.critical_value} | {a.elapsed_minutes:.0f}m elapsed | Doctor: {a.doctor_contacted}")
            else:
                parts.append("SLA ALERTS: No SLA breaches currently.")

        # ── 5. Bed census ────────────────────────────────────────────────────
        elif any(kw in q for kw in ["bed", "occupancy", "capacity", "vacant", "dirty", "turnaround", "available bed", "empty bed", "free bed"]):
            occupied = sum(1 for b in builder.beds.values() if b.status == "occupied")
            vacant = sum(1 for b in builder.beds.values() if b.status == "vacant")
            dirty = sum(1 for b in builder.beds.values() if b.status == "dirty")
            total = len(builder.beds)
            occ_pct = (100 * occupied // total) if total else 0
            parts.append(f"BED CENSUS: Total={total} | Occupied={occupied} | Vacant={vacant} | Dirty (pending turnaround)={dirty} | Occupancy={occ_pct}%")

        # ── 6. Revenue / billing ─────────────────────────────────────────────
        elif any(kw in q for kw in ["revenue", "billing", "claim", "denied", "tpa", "dispute", "unbilled"]):
            disputed = sum(1 for b in builder.bills.values() if b.has_billing_dispute)
            rejected_claims = [c for c in builder.claims.values() if c.status.lower() == "rejected"]
            total_unbilled = sum(b.unbilled_consumables for b in builder.bills.values())
            parts.append(f"REVENUE RISK: {disputed} billing disputes | {len(rejected_claims)} rejected claims | Unbilled consumables: Rs {total_unbilled:,.2f}")

        # ── 7. Generic patient census (last resort, count only) ─────────────
        elif any(kw in q for kw in ["how many patient", "total patient", "patient count", "census"]):
            total_admitted = sum(1 for p in builder.patients.values() if p.status == "admitted")
            parts.append(f"PATIENT CENSUS: {total_admitted} patients currently admitted across all wards.")

    return "\n\n".join(parts) if parts else ""


# ─────────────────────────────────────────────────────────────────────────────
# GOVERNANCE SEARCH
# ─────────────────────────────────────────────────────────────────────────────

def _is_template_content(text: str) -> bool:
    """Detect synthetic/template SOP content that has no real procedural value."""
    t = text.lower()
    return "execute phase" in t and "in full compliance with" in t


def _relevance_score(query_words: List[str], text: str) -> int:
    """Count how many query words (4+ chars) appear in text."""
    t = text.lower()
    return sum(1 for w in query_words if w in t)


async def search_governance(query: str) -> str:
    """Search governance KB for relevant SOPs, policies, articles, and routing rules.

    Three-layer search:
    1. Cognee semantic graph search (SUMMARIES + GRAPH_COMPLETION) — rich entity relationships.
    2. Operational vector store (fastembed direct) filtered to governance node types.
    3. In-memory OntologyBuilder scan — zero-dependency fallback.

    Returns empty string if nothing useful found.
    """
    query_words = [w for w in query.lower().split() if len(w) > 3]
    min_score = min(2, len(query_words)) if query_words else 1

    # ── Layer 1: Cognee semantic graph search ─────────────────────────────────
    cognee_snippets: List[str] = []
    try:
        try:
            from cognee.api.v1.search.types import SearchType as CogneeSearchType
        except ImportError:
            from cognee.modules.search.types import SearchType as CogneeSearchType
        import cognee
        # SUMMARIES gives paragraph chunks; GRAPH_COMPLETION gives entity traversal
        for search_mode in (CogneeSearchType.SUMMARIES, CogneeSearchType.GRAPH_COMPLETION):
            try:
                raw = await cognee.search(search_mode, query_text=query)
                if raw:
                    for r in raw[:3]:
                        text = ""
                        if isinstance(r, dict):
                            text = r.get("text", r.get("content", r.get("summary", ""))) or ""
                        elif hasattr(r, "text"):
                            text = str(r.text or "")
                        elif hasattr(r, "content"):
                            text = str(r.content or "")
                        text = text.strip()
                        if text and not _is_template_content(text) and len(text) > 30:
                            scored = _relevance_score(query_words, text)
                            if scored >= min_score:
                                cognee_snippets.append(text[:500])
                                break
            except Exception:
                pass
    except Exception:
        pass

    # ── Layer 2: Operational vector store (governance nodes) ──────────────────
    gov_hits: List[str] = []
    try:
        from app.ontology.vector_store import search_operational
        results = search_operational(query, top_k=12)
        gov_node_types = ("SOPNode", "PolicyNode", "KnowledgeArticleNode", "RoutingRuleNode")
        for r in results:
            if r.get("node_type") not in gov_node_types:
                continue
            ds = r.get("dense_summary", "") or ""
            if _is_template_content(ds):
                continue
            if _relevance_score(query_words, ds + " " + r.get("id", "")) >= min_score:
                gov_hits.append(f"  {r['id']}: {ds[:500]}")
                if len(gov_hits) >= 3:
                    break
    except Exception:
        pass

    # ── Layer 3: In-memory builder scan (SOPs + policies + routing rules) ─────
    builder_hits: List[str] = []
    try:
        from app.ontology.builder import get_ontology_builder
        builder = get_ontology_builder()
        stores = [
            ("SOP", builder.sops),
            ("Policy", builder.policies),
            ("Article", builder.articles),
            ("RoutingRule", builder.routing_rules),
        ]
        for label, store in stores:
            for node_id, node in store.items():
                ds = getattr(node, "dense_summary", "") or ""
                if _is_template_content(ds):
                    continue
                if _relevance_score(query_words, ds + " " + node_id) >= min_score:
                    builder_hits.append(f"  {label} {node_id}: {ds[:400]}")
                if len(builder_hits) >= 4:
                    break
            if len(builder_hits) >= 4:
                break
    except Exception:
        pass

    # ── Merge results ─────────────────────────────────────────────────────────
    all_snippets: List[str] = []
    # Cognee results are richest; operational vector store next; in-memory last
    if cognee_snippets:
        all_snippets.extend(cognee_snippets[:2])
    if gov_hits and len(all_snippets) < 3:
        all_snippets.extend(gov_hits[: 3 - len(all_snippets)])
    if builder_hits and len(all_snippets) < 3:
        all_snippets.extend(builder_hits[: 3 - len(all_snippets)])

    if all_snippets:
        return "RELEVANT GOVERNANCE:\n" + "\n".join(all_snippets)
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# CONFIDENCE, CITATIONS, WORKFLOW, MISSING FIELDS — requirements 2, 3, 4, 5
# ─────────────────────────────────────────────────────────────────────────────

def compute_confidence(graph_context: str, entities: Dict[str, List[str]], query: str) -> Dict[str, str]:
    """Return confidence level and reason based on data found in the graph."""
    if not graph_context:
        return {"level": "UNCERTAIN", "reason": "No matching data found in the operational graph for this query."}

    has_specific_entity = any(v for v in entities.values())
    if has_specific_entity and "not found" not in graph_context.lower():
        return {"level": "HIGH", "reason": "Direct match found in the live graph with specific entity IDs."}

    aggregate_signals = ("BED CENSUS", "BLOCKED DISCHARGES", "REVENUE RISK", "SLA-BREACHED", "PATIENTS IN", "PATIENT CENSUS")
    if any(sig in graph_context for sig in aggregate_signals):
        return {"level": "HIGH", "reason": "Live aggregate data retrieved from the operational graph."}

    if "RELEVANT GOVERNANCE" in graph_context:
        return {"level": "MEDIUM", "reason": "Governance documents found but no live patient data matches this query."}

    if graph_context.strip():
        return {"level": "MEDIUM", "reason": "Partial data found — answer may not be complete."}

    return {"level": "UNCERTAIN", "reason": "No matching data found in the operational graph for this query."}


def build_source_citations(entities: Dict[str, List[str]], graph_context: str, governance_context: str) -> List[Dict[str, str]]:
    """Build source citations from entities used and governance docs referenced."""
    citations: List[Dict[str, str]] = []

    for uhid in entities.get("uhids", []):
        citations.append({"type": "PatientNode", "id": uhid, "section": "Patient 360°"})
    for dis_id in entities.get("discharge_ids", []):
        citations.append({"type": "DischargeNode", "id": dis_id, "section": "Discharge Status"})
    for alert_id in entities.get("alert_ids", []):
        citations.append({"type": "LabCriticalAlertNode", "id": alert_id, "section": "Panic Alert"})
    for bed_id in entities.get("bed_ids", []):
        citations.append({"type": "BedNode", "id": bed_id, "section": "Bed Status"})
    for adm_id in entities.get("admission_ids", []):
        citations.append({"type": "AdmissionNode", "id": adm_id, "section": "Admission"})
    for claim_id in entities.get("claim_ids", []):
        citations.append({"type": "ClaimNode", "id": claim_id, "section": "Insurance Claim"})
    for bill_id in entities.get("bill_ids", []):
        citations.append({"type": "BillNode", "id": bill_id, "section": "Bill"})

    if "BED CENSUS" in graph_context:
        citations.append({"type": "LiveGraph", "id": "BedCensus", "section": "Bed occupancy aggregate"})
    if "BLOCKED DISCHARGES" in graph_context:
        citations.append({"type": "LiveGraph", "id": "BlockedDischarges", "section": "Discharge status aggregate"})
    if "REVENUE RISK" in graph_context:
        citations.append({"type": "LiveGraph", "id": "RevenueRisk", "section": "Revenue risk aggregate"})
    if "SLA-BREACHED" in graph_context:
        citations.append({"type": "LiveGraph", "id": "SLAAlerts", "section": "SLA breach aggregate"})
    if "PATIENTS IN" in graph_context:
        m = re.search(r'PATIENTS IN (.+?) \(', graph_context)
        ward_name = m.group(1) if m else "Ward"
        citations.append({"type": "LiveGraph", "id": f"Ward:{ward_name}", "section": "Ward patient list"})

    if governance_context:
        for line in governance_context.split("\n"):
            gm = re.match(r'\s*(SOP-\w+|POL-\w+)[:\s]', line)
            if gm:
                citations.append({"type": "GovernanceDoc", "id": gm.group(1), "section": line.strip()[:100]})

    return citations


def get_discharge_next_step(discharge_id: str, builder) -> Optional[Dict[str, Any]]:
    """Return the NEXT incomplete step in the discharge workflow for a discharge ID."""
    dis = builder.discharges.get(discharge_id)
    if not dis:
        return None

    step_values = {
        "clearance_clinical": getattr(dis, "clearance_clinical", False),
        "clearance_pharmacy": getattr(dis, "clearance_pharmacy", False),
        "clearance_billing": getattr(dis, "clearance_billing", False),
        "gate_pass_issued": getattr(dis, "gate_pass_issued", False),
    }

    for step_def in DISCHARGE_WORKFLOW_STEPS:
        if not step_values.get(step_def["field"], False):
            return {
                "step": step_def["step"],
                "total_steps": len(DISCHARGE_WORKFLOW_STEPS),
                "name": step_def["name"],
                "description": step_def["description"],
                "responsible_team": step_def["responsible_team"],
                "extension": step_def["extension"],
                "field": step_def["field"],
            }

    return {
        "step": len(DISCHARGE_WORKFLOW_STEPS),
        "total_steps": len(DISCHARGE_WORKFLOW_STEPS),
        "name": "Complete",
        "description": "All discharge steps completed. Gate pass has been issued.",
        "responsible_team": "Discharge Desk",
        "extension": "Ext. 1005",
        "field": "gate_pass_issued",
    }


def detect_missing_fields(query: str, entities: Dict[str, List[str]]) -> Optional[Dict[str, Any]]:
    """Detect workflow action triggers with missing required fields and return prompts."""
    q = query.lower()
    for workflow_type, triggers in WORKFLOW_TRIGGERS.items():
        if any(trigger in q for trigger in triggers):
            missing = {}
            if workflow_type == "discharge":
                if not entities.get("uhids") and not entities.get("discharge_ids"):
                    missing["uhid"] = "Which patient or discharge ID should this workflow be started for? (e.g. SMCH-123456 or DIS-ADM-xxx)"
            elif workflow_type == "admission":
                if not entities.get("uhids"):
                    missing["uhid"] = "Please provide the patient UHID or name."
                if "doctor" not in q:
                    missing["admitting_doctor_id"] = "Which doctor is admitting the patient?"
                if "diagnosis" not in q and " for " not in q:
                    missing["admitting_diagnosis"] = "What is the admitting diagnosis?"

            if missing:
                return {
                    "workflow_type": workflow_type,
                    "missing_fields": missing,
                    "prompt": "Before I can guide you through this workflow, I need a few more details:",
                }
    return None


# ─────────────────────────────────────────────────────────────────────────────
# LLM SYNTHESIS
# ─────────────────────────────────────────────────────────────────────────────

def _nlg_format(query: str, graph_context: str, governance_context: str) -> str:
    """
    Convert structured graph context into natural conversational prose.
    Used when the LLM is unavailable — produces human-readable responses without hallucination.
    """
    if not graph_context and not governance_context:
        return "I don't have that information. Please check with your supervisor or refer to the relevant SOP."

    parts: List[str] = []

    # ── Bed census ─────────────────────────────────────────────────────────────
    if "BED CENSUS:" in graph_context:
        m = re.search(r'Total=(\d+).*?Occupied=(\d+).*?Vacant=(\d+).*?Dirty[^=]+=(\d+).*?Occupancy=(\d+)%', graph_context)
        if m:
            total, occupied, vacant, dirty, pct = m.groups()
            line = (f"Current bed occupancy is {pct}% — {occupied} of {total} beds are occupied, "
                    f"with {vacant} beds available for new admissions")
            if int(dirty) > 0:
                line += f" and {dirty} bed(s) pending housekeeping turnaround"
            parts.append(line + ".")

    # ── Ward patient list ───────────────────────────────────────────────────────
    elif graph_context.startswith("PATIENTS IN") or graph_context.startswith("No patients"):
        lines = [l for l in graph_context.split("\n") if l.strip()]
        hm = re.match(r'PATIENTS IN (.+?) \((\d+) total\)', lines[0])
        if hm:
            ward_name, count = hm.group(1), int(hm.group(2))
            patient_lines = [l.strip() for l in lines[1:] if "SMCH-" in l and "—" in l]
            blocked = [l for l in patient_lines if "DISCHARGE BLOCKED" in l]
            clear = [l for l in patient_lines if "DISCHARGE BLOCKED" not in l and "more" not in l]

            parts.append(f"There are {count} patient(s) in {ward_name}.")
            if blocked:
                parts.append(f"\n{len(blocked)} discharge(s) are currently BLOCKED:")
                for l in blocked:
                    # "SMCH-xxx — Name, age gender | Bed: id [DISCHARGE BLOCKED]"
                    clean = l.replace("[DISCHARGE BLOCKED]", "").strip()
                    parts.append(f"  • {clean} — discharge blocked")
            if clear:
                parts.append(f"\n{len(clear)} patient(s) with all clearances:")
                for l in clear:  # no artificial cap — show all
                    parts.append(f"  • {l}")
        else:
            parts.append(graph_context)

    # ── Patient 360° view ───────────────────────────────────────────────────────
    elif "PATIENT:" in graph_context and "UHID:" in graph_context:
        blocks = re.split(r'\n(?=PATIENT:)', graph_context)
        for block in blocks[:3]:
            if not block.strip():
                continue
            blines = block.strip().split("\n")
            pm = re.match(r'PATIENT:\s*(.+?),\s*(\d+)y\s*(\w+)\s*\|\s*UHID:\s*(SMCH-\w+)', blines[0])
            if not pm:
                parts.append(block)
                continue
            name, age, gender, uhid = pm.groups()
            summary: List[str] = [f"{name} ({uhid}) — {age}y {gender}"]
            for line in blines[1:]:
                line = line.strip()
                if line.startswith("Bed:"):
                    summary.append(f"  Location: {line[4:].strip()}")
                elif line.startswith("Admission:"):
                    summary.append(f"  {line}")
                elif "Discharge [BLOCKED]" in line:
                    summary.append(f"  Discharge status: BLOCKED")
                elif "Discharge [CLEAR]" in line:
                    summary.append(f"  Discharge status: Clear")
                elif "BLOCKER:" in line:
                    summary.append(f"  Block reason: {line.replace('BLOCKER:', '').strip()}")
                elif "Escalation:" in line:
                    ext = line.replace("Escalation:", "").strip()
                    summary.append(f"  Action needed: Contact Ext. {ext} to unblock")
                elif line.startswith("Clinical:"):
                    summary.append(f"  Clearances — {line}")
                elif line.startswith("Bill "):
                    summary.append(f"  Billing: {line}")
                elif "Panic Alert" in line:
                    summary.append(f"  LAB ALERT: {line}")
                elif "Gate Pass: ISSUED" in line:
                    summary.append(f"  Gate pass has been issued")
                elif "Claim " in line:
                    summary.append(f"  Insurance: {line}")
            parts.append("\n".join(summary))

    # ── Discharge context ──────────────────────────────────────────────────────
    elif "DISCHARGE DIS-ADM" in graph_context and "PATIENT:" not in graph_context:
        blocks = re.split(r'\n(?=DISCHARGE DIS-ADM)', graph_context)
        for block in blocks[:3]:
            if not block.strip():
                continue
            blines = block.strip().split("\n")
            dm = re.match(r'DISCHARGE (DIS-ADM-\w+) — Patient: (.+?) \((.+?)\)', blines[0])
            if dm:
                dis_id, patient, uhid = dm.groups()
                summary = [f"Discharge for {patient} ({uhid}) — {dis_id}"]
                for line in blines[1:]:
                    line = line.strip()
                    if "BLOCKED" in line:
                        summary.append(f"  Status: BLOCKED — gate pass not yet issued")
                    elif "BLOCKER:" in line:
                        summary.append(f"  Reason: {line.replace('BLOCKER:', '').strip()}")
                    elif "Escalation:" in line:
                        ext = line.replace("Escalation:", "").strip()
                        summary.append(f"  Resolve by calling Ext. {ext}")
                    elif line.startswith("Clinical:"):
                        summary.append(f"  Clearances — {line}")
                parts.append("\n".join(summary))

    # ── Blocked discharge list ─────────────────────────────────────────────────
    elif "BLOCKED DISCHARGES" in graph_context:
        cm = re.search(r'BLOCKED DISCHARGES \((\d+) total\)', graph_context)
        count = cm.group(1) if cm else "?"
        if "None currently" in graph_context:
            parts.append("All discharges are currently clear. No patients are blocked from leaving.")
        else:
            parts.append(f"There are {count} blocked discharge(s) right now:")
            for line in graph_context.split("\n"):
                m = re.match(r'\s*(DIS-ADM-\w+) — (.+?):\s*(.+)', line.strip())
                if m:
                    dis_id, patient, reason = m.groups()
                    parts.append(f"  • {patient} ({dis_id}): {reason}")

    # ── SLA alerts ─────────────────────────────────────────────────────────────
    elif "SLA-BREACHED" in graph_context or "SLA ALERTS" in graph_context:
        if "No SLA breaches" in graph_context:
            parts.append("No panic lab alerts have breached the 15-minute readback SLA right now.")
        else:
            cm = re.search(r'SLA-BREACHED PANIC ALERTS \((\d+) total\)', graph_context)
            count = cm.group(1) if cm else "?"
            parts.append(f"{count} panic lab alert(s) have breached the 15-minute readback SLA:")
            for line in graph_context.split("\n"):
                if "CRIT-ALRT" in line or ("elapsed" in line.lower() and "|" in line):
                    parts.append(f"  • {line.strip()}")

    # ── Revenue / billing ──────────────────────────────────────────────────────
    elif "REVENUE RISK:" in graph_context:
        m = re.search(r'(\d+) billing disputes.*?(\d+) rejected claims.*?Rs ([\d,.]+)', graph_context)
        if m:
            disputes, rejected, unbilled = m.groups()
            parts.append(
                f"Revenue risk summary: {disputes} billing dispute(s), "
                f"{rejected} rejected insurance claim(s), "
                f"and Rs {unbilled} in unbilled consumables."
            )

    # ── Patient census ──────────────────────────────────────────────────────────
    elif "PATIENT CENSUS:" in graph_context:
        parts.append(graph_context.replace("PATIENT CENSUS:", "").strip())

    # ── Fallback: just return the raw context rather than silence ──────────────
    else:
        parts.append(graph_context)

    # Governance
    if governance_context and governance_context.strip():
        policy_lines = [l.strip() for l in governance_context.split("\n") if l.strip() and l.strip() != "RELEVANT GOVERNANCE:"]
        if policy_lines:
            parts.append("\nRelevant policy reference: " + policy_lines[0])

    return "\n".join(p for p in parts if p.strip()) or "I don't have that information. Please consult your supervisor."


SYSTEM_PROMPT = """You are the SMCH Operations Assistant for Saveetha Medical College & Hospital.
You answer questions from nurses, billing clerks, and operations staff using ONLY the live hospital graph data provided.

RULES:
1. Base every answer strictly on the LIVE GRAPH DATA provided. Never guess or invent data.
2. If the data is insufficient, say exactly: "I don't have that information in the system."
3. When listing patients or items, show ALL of them from the graph data — do not truncate.
4. For blocked discharges, always state the blocker reason and the escalation extension.
5. When giving procedural guidance, cite the SOP or Policy ID.
6. Never provide clinical, medication, or dosage advice — route to Clinical Review Ext. 1012.
7. Write in plain conversational language. The user is a nurse, billing clerk, or ward administrator.
8. For patient lists, format as a numbered or bulleted list with UHID, name, bed, and any key flags."""


async def synthesize_response(query: str, graph_context: str, governance_context: str, history_context: str = "") -> str:
    """Call LLM (Groq/Ollama) to synthesize a natural language answer from graph context."""
    import os
    import logging
    _log = logging.getLogger("smch.agent")

    combined_context = graph_context
    if governance_context:
        combined_context += f"\n\n{governance_context}"

    history_section = f"\n{history_context}\n" if history_context else ""

    user_message = f"""QUESTION: {query}
{history_section}
LIVE GRAPH DATA:
{combined_context}

Answer based strictly on the graph data above. If the question refers to items from the conversation history, use those items."""

    try:
        import litellm
        model = os.getenv("LLM_MODEL", "groq/llama-3.1-8b-instant")
        api_key = os.getenv("LLM_API_KEY")
        api_base = os.getenv("LLM_ENDPOINT") or None  # None = let litellm use the provider's default endpoint

        call_kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": 400,
            "temperature": 0.1,
        }
        if api_key:
            call_kwargs["api_key"] = api_key
        if api_base:
            call_kwargs["api_base"] = api_base

        response = await litellm.acompletion(**call_kwargs)
        return response.choices[0].message.content.strip()
    except Exception as e:
        _log.warning("LLM synthesis failed [%s: %s] — falling back to NLG formatter", type(e).__name__, e)
        return _nlg_format(query, graph_context, governance_context)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AGENT PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

# Follow-up signals — pronouns and references that indicate the query is about something
# already mentioned in the conversation.
FOLLOWUP_SIGNALS = ["these", "them", "they", "this", "those", "it ", "why ", "what about",
                    "who is", "who are", "tell me more", "explain", "elaborate", "which one",
                    "the same", "above", "mentioned", "listed", "that patient", "that discharge"]


async def answer_query(query: str, builder, conversation_history: Optional[List[Dict[str, str]]] = None, role: str = "ADMIN") -> Dict[str, Any]:
    """
    Full governed agent pipeline:
    guardrail → RBAC → missing fields → entity extraction (+ history) → graph context
    → governance → confidence → citations → workflow step → LLM → response
    """
    # 0. Hospital directory lookup — "how do I contact X?"
    q_lower_strip = query.lower().strip()
    if any(sig in q_lower_strip for sig in _CONTACT_SIGNALS):
        # Match longest key first so "central billing" beats "billing"
        for dept_key in sorted(HOSPITAL_CONTACTS, key=len, reverse=True):
            if dept_key in q_lower_strip:
                info = HOSPITAL_CONTACTS[dept_key]
                return {
                    "query": query,
                    "guardrail_triggered": None,
                    "answer": f"To reach {info['name']}, dial internal extension **{info['ext']}**.",
                    "confidence": {"level": "HIGH", "reason": "Contact retrieved from hospital internal directory."},
                    "source_citations": [{"id": f"EXT-{info['ext']}", "type": "HospitalDirectory", "snippet": info["name"]}],
                    "requires_human_approval": False,
                    "workflow_step": None,
                    "missing_fields": [],
                    "graph_context_used": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

    # 0b. RBAC check — role-based data access control
    rbac_deny = check_rbac(query, role)
    if rbac_deny:
        return rbac_deny

    # 1. Code-based guardrails — no LLM involved
    guardrail_hit = check_guardrails(query)
    if guardrail_hit:
        if guardrail_hit.get("requires_human_approval"):
            try:
                from app.ontology.shared_state import add_approval, audit as _audit
                aid = add_approval(
                    query, guardrail_hit["guardrail"],
                    guardrail_hit.get("escalation", "—"),
                    guardrail_hit.get("escalation_reason", "—"),
                    query,
                )
                _audit("GUARDRAIL", guardrail_hit["guardrail"], "approval_queued",
                       f"APR-ID: {aid} | Query: {query[:60]}", role)
            except Exception:
                pass
        return {
            "query": query,
            "guardrail_triggered": guardrail_hit["guardrail"],
            "answer": guardrail_hit["answer"],
            "escalation": guardrail_hit.get("escalation"),
            "escalation_reason": guardrail_hit.get("escalation_reason"),
            "policy_citations": guardrail_hit.get("policy_citations", []),
            "requires_human_approval": guardrail_hit.get("requires_human_approval", False),
            "graph_context_used": False,
            "confidence": {"level": "UNCERTAIN", "reason": "Request blocked by guardrail."},
            "source_citations": [],
            "workflow_step": None,
            "missing_fields": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    entities = extract_entities(query)
    has_entities = any(v for v in entities.values())

    # 2. Follow-up resolution from conversation history
    if not has_entities and conversation_history:
        q_lower = query.lower()
        is_followup = any(sig in q_lower for sig in FOLLOWUP_SIGNALS)
        if is_followup:
            history_text = " ".join(msg.get("content", "") for msg in conversation_history[-6:])
            history_entities = extract_entities(history_text)
            for k, v in history_entities.items():
                if v:
                    entities[k] = v

    # 3. Missing field detection — prompt before proceeding
    missing_field_result = detect_missing_fields(query, entities)
    if missing_field_result:
        missing = missing_field_result["missing_fields"]
        prompt_lines = [missing_field_result["prompt"]]
        for _, field_prompt in missing.items():
            prompt_lines.append(f"  • {field_prompt}")
        return {
            "query": query,
            "guardrail_triggered": None,
            "answer": "\n".join(prompt_lines),
            "graph_context_used": False,
            "confidence": {"level": "UNCERTAIN", "reason": "Required fields missing — cannot proceed with workflow."},
            "source_citations": [],
            "workflow_step": None,
            "missing_fields": missing_field_result,
            "requires_human_approval": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # 4. Assemble live graph context then apply role-level data filter
    graph_context = assemble_graph_context(entities, query, builder)
    graph_context = filter_graph_context_by_role(graph_context, role)

    # 5. Build conversation history string for LLM
    history_context = ""
    if conversation_history:
        turns = []
        for msg in conversation_history[-4:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            turns.append(f"{role}: {msg.get('content', '')[:300]}")
        if turns:
            history_context = "RECENT CONVERSATION:\n" + "\n".join(turns)

    # 6. Governance search
    governance_context = await search_governance(query)

    # 7. Confidence scoring — requirement 3
    confidence = compute_confidence(graph_context, entities, query)

    # 8. Source citations — requirement 2
    source_citations = build_source_citations(entities, graph_context, governance_context)

    # 9. Stepwise workflow guidance — requirement 4
    workflow_step = None
    q_lower = query.lower()
    if any(trigger in q_lower for trigger in WORKFLOW_TRIGGERS.get("discharge", [])):
        dis_ids = entities.get("discharge_ids", [])
        if dis_ids:
            workflow_step = get_discharge_next_step(dis_ids[0], builder)
        # Fall back to step 1 if no specific discharge found or not in builder
        if workflow_step is None:
            s = DISCHARGE_WORKFLOW_STEPS[0]
            workflow_step = {
                "step": s["step"],
                "total_steps": len(DISCHARGE_WORKFLOW_STEPS),
                "name": s["name"],
                "description": s["description"],
                "responsible_team": s["responsible_team"],
                "extension": s["extension"],
                "field": s["field"],
            }

    # 10. Unclear routing when no data found at all — requirement 6
    if confidence["level"] == "UNCERTAIN" and not graph_context and not governance_context:
        route = ESCALATION_ROUTES["UNCLEAR"]
        return {
            "query": query,
            "guardrail_triggered": "UNCLEAR",
            "answer": (
                "I'm not sure I have the right information to answer this reliably. "
                f"Please contact {route['team']} at {route['extension']} for assistance."
            ),
            "escalation": f"{route['team']} — {route['extension']}",
            "escalation_reason": "No relevant data found in the operational graph for this query.",
            "policy_citations": [route["policy"]],
            "requires_human_approval": False,
            "graph_context_used": False,
            "confidence": confidence,
            "source_citations": [],
            "workflow_step": workflow_step,
            "missing_fields": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # 11. LLM synthesis
    answer = await synthesize_response(query, graph_context, governance_context, history_context)

    entities_found = {k: v for k, v in entities.items() if v}

    # 12. Audit log — record every answered query
    try:
        from app.ontology.shared_state import audit as _audit
        _audit(
            "QUERY", query[:60], "answered",
            f"confidence={confidence.get('level', '?')} | entities={list(entities_found.keys())}",
            role,
        )
    except Exception:
        pass

    return {
        "query": query,
        "guardrail_triggered": None,
        "answer": answer,
        "graph_context_used": bool(graph_context),
        "entities_found": entities_found,
        "graph_context_preview": graph_context[:500] if graph_context else "",
        "requires_human_approval": False,
        "confidence": confidence,
        "source_citations": source_citations,
        "workflow_step": workflow_step,
        "missing_fields": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
