"""
SMCH Operations Command Center — Palantir-style Hospital Operations Platform
=============================================================================
Full command center: monitor + execute every admin workflow from one dashboard.

Routes:
  GET  /dashboard                          → HTML command center
  GET  /api/v1/dashboard/live              → live JSON data
  POST /api/v1/ops/discharge/{id}/advance  → mark next discharge step complete
  POST /api/v1/ops/alert/{id}/acknowledge  → acknowledge lab critical alert
  POST /api/v1/ops/bed/{id}/mark-clean     → mark dirty bed available
  POST /api/v1/ops/bed/{id}/assign         → assign patient to bed
  POST /api/v1/ops/claim/{id}/update-status → update claim status
"""

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from collections import defaultdict

router = APIRouter(tags=["Dashboard"])


# ─────────────────────────────────────────────────────────────────────────────
# DATA BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_live_data(builder) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)

    # BED CENSUS
    beds = list(builder.beds.values())
    total_beds = len(beds)
    occupied_beds = sum(1 for b in beds if b.status == "occupied")
    vacant_beds   = sum(1 for b in beds if b.status == "vacant")
    dirty_beds    = sum(1 for b in beds if b.status == "dirty")

    ward_map = defaultdict(lambda: {"total": 0, "occupied": 0, "vacant": 0, "dirty": 0})
    for b in beds:
        w = b.ward or "Unknown"
        ward_map[w]["total"] += 1
        if b.status in ("occupied", "vacant", "dirty"):
            ward_map[w][b.status] += 1

    by_ward = []
    for ward_name, counts in sorted(ward_map.items()):
        occ = counts["occupied"]
        tot = counts["total"]
        by_ward.append({
            "ward": ward_name,
            "total": tot,
            "occupied": occ,
            "vacant": counts["vacant"],
            "dirty": counts["dirty"],
            "occupancy_pct": round(100 * occ / tot, 1) if tot > 0 else 0,
        })

    # Individual bed rows for Bed Operations section
    bed_rows = []
    for bed in beds:
        pat = builder.patients.get(bed.current_patient_uhid) if bed.current_patient_uhid else None
        bed_rows.append({
            "bed_id": bed.bed_id,
            "ward": bed.ward or "—",
            "status": bed.status,
            "patient_uhid": bed.current_patient_uhid or "",
            "patient_name": pat.name if pat else "",
        })

    bed_census = {
        "total": total_beds,
        "occupied": occupied_beds,
        "vacant": vacant_beds,
        "dirty": dirty_beds,
        "occupancy_pct": round(100 * occupied_beds / total_beds, 1) if total_beds > 0 else 0,
        "by_ward": by_ward[:15],
        "bed_rows": bed_rows,
    }

    # DISCHARGE PIPELINE
    discharges = list(builder.discharges.values())
    blocked_dis = [d for d in discharges if d.is_blocked]

    discharge_rows = []
    for d in discharges:
        pat = builder.patients.get(d.uhid)
        bed = builder.beds.get(pat.current_bed_id) if pat and getattr(pat, "current_bed_id", None) else None
        discharge_rows.append({
            "discharge_id": d.discharge_id,
            "uhid": d.uhid,
            "patient_name": pat.name if pat else d.uhid,
            "bed_id": bed.bed_id if bed else "—",
            "ward": bed.ward if bed else "—",
            "clinical":  getattr(d, "clearance_clinical",  False),
            "pharmacy":  getattr(d, "clearance_pharmacy",  False),
            "billing":   getattr(d, "clearance_billing",   False),
            "nursing":   getattr(d, "clearance_nursing",   False),
            "is_blocked": d.is_blocked,
            "blocker_reason": getattr(d, "blocker_reason", "") or "",
            "gate_pass": getattr(d, "gate_pass_issued", False),
            "escalation": getattr(d, "resolution_team_extension", "") or "",
        })

    discharge_pipeline = {
        "total": len(discharges),
        "blocked": len(blocked_dis),
        "cleared": len([d for d in discharges if not d.is_blocked]),
        "gate_pass_issued": sum(1 for d in discharges if getattr(d, "gate_pass_issued", False)),
        "rows": discharge_rows,
    }

    # LAB CRITICAL ALERTS (correct field names)
    alerts = list(builder.lab_critical_alerts.values())
    breached = [a for a in alerts if getattr(a, "is_sla_breached", False)]
    pending_ack = [a for a in alerts if getattr(a, "readback_status", "") != "Acknowledged"]

    alert_rows = []
    for a in sorted(alerts, key=lambda x: getattr(x, "elapsed_minutes", 0), reverse=True):
        pat = builder.patients.get(getattr(a, "uhid", ""))
        elapsed = getattr(a, "elapsed_minutes", 0)
        sla     = getattr(a, "sla_minutes", 15)
        alert_rows.append({
            "alert_id":       getattr(a, "alert_id", ""),
            "uhid":           getattr(a, "uhid", ""),
            "patient_name":   pat.name if pat else getattr(a, "patient_name", getattr(a, "uhid", "")),
            "parameter":      getattr(a, "parameter_name", ""),
            "value":          getattr(a, "critical_value", ""),
            "elapsed_min":    round(elapsed, 1),
            "sla_limit_min":  sla,
            "sla_breached":   getattr(a, "is_sla_breached", False),
            "readback_status":getattr(a, "readback_status", ""),
            "doctor_contacted": getattr(a, "doctor_contacted", False),
            "doctor_phone":   getattr(a, "doctor_phone", ""),
        })

    panic_alerts = {
        "total":        len(alerts),
        "sla_breached": len(breached),
        "pending_ack":  len(pending_ack),
        "acknowledged": len(alerts) - len(pending_ack),
        "rows": alert_rows,
    }

    # REVENUE & CLAIMS (correct field names)
    bills  = list(builder.bills.values())
    claims = list(builder.claims.values())
    total_pending  = sum(getattr(b, "pending_amount", 0)   for b in bills)
    total_disputed = sum(getattr(b, "total_amount",   0)   for b in bills if getattr(b, "has_billing_dispute", False))
    total_unbilled = sum(getattr(b, "unbilled_consumables", 0) for b in bills)

    rejected_claims = [c for c in claims if (c.status or "").lower() in ("rejected", "denied")]
    rejected_amount = sum(c.claim_amount or 0 for c in rejected_claims)
    pending_claims  = [c for c in claims if (c.status or "").lower() == "pending"]
    at_risk_amount  = sum((c.claim_amount or 0) for c in rejected_claims + pending_claims)

    claim_rows = []
    for c in claims:
        pat = builder.patients.get(getattr(c, "uhid", ""))
        status_low = (c.status or "").lower()
        claim_rows.append({
            "claim_id":     c.claim_id,
            "uhid":         getattr(c, "uhid", ""),
            "patient_name": pat.name if pat else getattr(c, "uhid", ""),
            "tpa":          c.tpa or "—",
            "amount":       c.claim_amount or 0,
            "status":       c.status or "—",
            "is_rejected":  status_low in ("rejected", "denied"),
            "rejection_reason": getattr(c, "rejection_reason", "") or "",
            "insurer":      getattr(c, "insurer", "") or "",
        })

    # TPA breakdown
    tpa_amounts = defaultdict(float)
    status_counts = defaultdict(int)
    for c in claims:
        tpa_amounts[c.tpa or "Unknown"] += (c.claim_amount or 0)
        status_counts[c.status or "Unknown"] += 1

    revenue = {
        "total_pending":            total_pending,
        "total_disputed":           total_disputed,
        "total_unbilled":           total_unbilled,
        "total_at_risk":            at_risk_amount,
        "rejected_claims_count":    len(rejected_claims),
        "rejected_claims_amount":   rejected_amount,
        "pending_claims_count":     len(pending_claims),
        "claim_rows":               claim_rows,
        "tpa_labels":               list(tpa_amounts.keys()),
        "tpa_values":               list(tpa_amounts.values()),
        "status_labels":            list(status_counts.keys()),
        "status_values":            list(status_counts.values()),
    }

    # EMERGENCY
    ed_cases = list(builder.emergency_cases.values())
    p1 = sum(1 for e in ed_cases if getattr(e, "triage_priority", "") in ("P1", "1", "Critical"))
    p2 = sum(1 for e in ed_cases if getattr(e, "triage_priority", "") in ("P2", "2", "Urgent"))

    ed_rows = [{
        "case_id":        getattr(e, "case_id", ""),
        "uhid":           getattr(e, "uhid", ""),
        "chief_complaint":getattr(e, "chief_complaint", ""),
        "triage":         getattr(e, "triage_priority", ""),
        "status":         getattr(e, "status", ""),
    } for e in ed_cases[:20]]

    emergency = {"total": len(ed_cases), "p1_critical": p1, "p2_urgent": p2, "rows": ed_rows}

    # PATIENTS
    patients = builder.patients
    patient_rows = []
    for uhid, p in list(patients.items())[:300]:
        bed = builder.beds.get(p.current_bed_id) if getattr(p, "current_bed_id", None) else None
        adm = builder.admissions.get(p.active_admission_id) if getattr(p, "active_admission_id", None) else None
        patient_rows.append({
            "uhid":           uhid,
            "name":           p.name or uhid,
            "status":         p.status or "active",
            "gender":         getattr(p, "gender", ""),
            "age":            getattr(p, "age", ""),
            "ward":           bed.ward if bed else "—",
            "bed_id":         p.current_bed_id or "—",
            "admission_date": str(getattr(adm, "admission_date", "") or ""),
            "diagnosis":      getattr(adm, "admitting_diagnosis", "") or "",
            "doctor_id":      getattr(adm, "admitting_doctor_id", "") or "",
        })

    patient_summary = {
        "total":    len(patients),
        "admitted": sum(1 for p in patients.values() if (p.status or "").lower() in ("admitted", "active")),
        "rows":     patient_rows,
    }

    return {
        "timestamp":          now.isoformat(),
        "bed_census":         bed_census,
        "discharge_pipeline": discharge_pipeline,
        "panic_alerts":       panic_alerts,
        "revenue":            revenue,
        "emergency":          emergency,
        "patients":           patient_summary,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LIVE DATA ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/api/v1/dashboard/live")
async def get_dashboard_live(role: str = "ADMIN") -> Dict[str, Any]:
    from app.ontology.graph_service import get_ontology_graph_service
    service = get_ontology_graph_service()
    data = _build_live_data(service.builder)
    # Real data-level RBAC: strip restricted sections before returning
    if role in ("NURSE", "DOCTOR"):
        rv = data.get("revenue", {})
        rv["claim_rows"] = []
        rv["total_at_risk"] = None
        rv["tpa_labels"] = []
        rv["tpa_values"] = []
        rv["status_labels"] = []
        rv["status_values"] = []
    if role == "BILLING_STAFF":
        pa = data.get("panic_alerts", {})
        pa["rows"] = []  # individual alert details hidden
    return data


# ─────────────────────────────────────────────────────────────────────────────
# ACTION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/v1/ops/discharge/{discharge_id}/advance")
async def advance_discharge_step(discharge_id: str) -> Dict[str, Any]:
    from app.ontology.graph_service import get_ontology_graph_service
    builder = get_ontology_graph_service().builder
    dis = builder.discharges.get(discharge_id)
    if not dis:
        return {"success": False, "message": f"Discharge {discharge_id} not found"}
    STEPS = [("clearance_clinical", "Clinical"), ("clearance_pharmacy", "Pharmacy"),
             ("clearance_billing", "Billing"), ("clearance_nursing", "Nursing")]
    for field, name in STEPS:
        if not getattr(dis, field, False):
            setattr(dis, field, True)
            # If all steps done, unblock
            if all(getattr(dis, f, False) for f, _ in STEPS):
                dis.is_blocked = False
                dis.gate_pass_issued = True
                try:
                    from app.ontology.shared_state import audit as _audit
                    _audit("ACTION", discharge_id, "gate_pass_issued", "All clearances complete")
                except Exception:
                    pass
                return {"success": True, "message": f"All clearances complete — gate pass issued for {discharge_id}",
                        "timestamp": datetime.now(timezone.utc).isoformat()}
            try:
                from app.ontology.shared_state import audit as _audit
                _audit("ACTION", discharge_id, f"{name.lower()}_cleared", f"{name} clearance marked complete")
            except Exception:
                pass
            return {"success": True, "message": f"{name} clearance marked complete for {discharge_id}",
                    "next_step": STEPS[STEPS.index((field, name)) + 1][1] if STEPS.index((field, name)) + 1 < len(STEPS) else "Complete",
                    "timestamp": datetime.now(timezone.utc).isoformat()}
    dis.is_blocked = False
    try:
        from app.ontology.shared_state import audit as _audit
        _audit("ACTION", discharge_id, "discharge_cleared", "Discharge fully cleared")
    except Exception:
        pass
    return {"success": True, "message": f"Discharge {discharge_id} fully cleared",
            "timestamp": datetime.now(timezone.utc).isoformat()}


@router.post("/api/v1/ops/alert/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str) -> Dict[str, Any]:
    from app.ontology.graph_service import get_ontology_graph_service
    builder = get_ontology_graph_service().builder
    alert = builder.lab_critical_alerts.get(alert_id)
    if not alert:
        return {"success": False, "message": f"Alert {alert_id} not found"}
    alert.readback_status = "Acknowledged"
    alert.doctor_contacted = True
    alert.ack_time = datetime.now(timezone.utc).isoformat()
    try:
        from app.ontology.shared_state import audit as _audit
        _audit("ACTION", alert_id, "alert_acknowledged", "Readback confirmed")
    except Exception:
        pass
    return {"success": True, "message": f"Alert {alert_id} acknowledged — readback confirmed",
            "timestamp": datetime.now(timezone.utc).isoformat()}


@router.post("/api/v1/ops/bed/{bed_id}/mark-clean")
async def mark_bed_clean(bed_id: str) -> Dict[str, Any]:
    from app.ontology.graph_service import get_ontology_graph_service
    builder = get_ontology_graph_service().builder
    bed = builder.beds.get(bed_id)
    if not bed:
        return {"success": False, "message": f"Bed {bed_id} not found"}
    bed.status = "vacant"
    bed.current_patient_uhid = None
    try:
        from app.ontology.shared_state import audit as _audit
        _audit("ACTION", bed_id, "bed_marked_clean", "Dirty bed marked as vacant")
    except Exception:
        pass
    return {"success": True, "message": f"Bed {bed_id} marked clean and available",
            "timestamp": datetime.now(timezone.utc).isoformat()}


@router.post("/api/v1/ops/bed/{bed_id}/assign")
async def assign_patient_to_bed(bed_id: str, uhid: str = Query(...)) -> Dict[str, Any]:
    from app.ontology.graph_service import get_ontology_graph_service
    builder = get_ontology_graph_service().builder
    bed = builder.beds.get(bed_id)
    if not bed:
        return {"success": False, "message": f"Bed {bed_id} not found"}
    pat = builder.patients.get(uhid)
    if not pat:
        return {"success": False, "message": f"Patient {uhid} not found"}
    bed.status = "occupied"
    bed.current_patient_uhid = uhid
    pat.current_bed_id = bed_id
    try:
        from app.ontology.shared_state import audit as _audit
        _audit("ACTION", bed_id, "patient_assigned", f"Patient {pat.name} ({uhid}) assigned")
    except Exception:
        pass
    return {"success": True, "message": f"Patient {pat.name} ({uhid}) assigned to {bed_id}",
            "timestamp": datetime.now(timezone.utc).isoformat()}


@router.post("/api/v1/ops/claim/{claim_id}/update-status")
async def update_claim_status(claim_id: str, status: str = Query(...)) -> Dict[str, Any]:
    from app.ontology.graph_service import get_ontology_graph_service
    builder = get_ontology_graph_service().builder
    claim = builder.claims.get(claim_id)
    if not claim:
        return {"success": False, "message": f"Claim {claim_id} not found"}
    old = claim.status
    claim.status = status
    try:
        from app.ontology.shared_state import audit as _audit
        _audit("ACTION", claim_id, "claim_status_updated", f"Status: {old} to {status}")
    except Exception:
        pass
    return {"success": True, "message": f"Claim {claim_id} status updated: {old} → {status}",
            "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/api/v1/approvals/pending")
async def get_pending_approvals() -> Dict[str, Any]:
    from app.ontology.shared_state import APPROVAL_QUEUE
    return {"count": len(APPROVAL_QUEUE), "items": list(APPROVAL_QUEUE)}


@router.post("/api/v1/approvals/{approval_id}/approve")
async def approve_action(approval_id: str) -> Dict[str, Any]:
    from app.ontology.shared_state import resolve_approval
    ok = resolve_approval(approval_id, "approved", "admin")
    return {"success": ok, "message": f"Action {approval_id} approved." if ok else "Not found"}


@router.post("/api/v1/approvals/{approval_id}/deny")
async def deny_action(approval_id: str) -> Dict[str, Any]:
    from app.ontology.shared_state import resolve_approval
    ok = resolve_approval(approval_id, "denied", "admin")
    return {"success": ok, "message": f"Action {approval_id} denied." if ok else "Not found"}


@router.get("/api/v1/audit/log")
async def get_audit_log(limit: int = 100, event_type: str = "") -> Dict[str, Any]:
    from app.ontology.shared_state import AUDIT_LOG
    entries = list(AUDIT_LOG)
    if event_type:
        entries = [e for e in entries if e.get("event_type", "").upper() == event_type.upper()]
    return {"count": len(entries), "entries": entries[:limit]}


@router.get("/api/v1/ops/detail/{entity_type}/{entity_id}")
async def get_entity_detail(entity_type: str, entity_id: str) -> Dict[str, Any]:
    """Return full detail for any entity — claim, discharge, alert, bed, patient."""
    from app.ontology.graph_service import get_ontology_graph_service
    svc = get_ontology_graph_service()
    if not svc or not svc.builder:
        return {"error": "Graph not initialised"}
    b = svc.builder

    def _pat(uhid):
        p = b.patients.get(uhid)
        if not p: return {}
        return {"name": p.name, "age": p.age, "gender": p.gender, "contact": p.contact,
                "status": p.status, "bed": p.current_bed_id or "—"}

    def _adm(admission_id):
        a = b.admissions.get(admission_id) if hasattr(b, "admissions") else None
        if not a: return {}
        return {"doctor": a.admitting_doctor_id, "diagnosis": a.admitting_diagnosis,
                "date": a.admission_date, "type": a.admission_type, "dept": a.department_id}

    if entity_type == "claim":
        c = b.claims.get(entity_id)
        if not c: return {"error": f"Claim {entity_id} not found"}
        pat = _pat(c.uhid)
        adm = _adm(getattr(c, "admission_id", ""))
        return {
            "type": "claim", "id": c.claim_id,
            "claim_id": c.claim_id, "admission_id": getattr(c, "admission_id", "—"),
            "uhid": c.uhid, "patient": pat,
            "insurer": getattr(c, "insurer", "—"), "tpa": c.tpa,
            "policy_number": getattr(c, "policy_number", "—"),
            "claim_amount": c.claim_amount, "approved_amount": getattr(c, "approved_amount", 0),
            "status": c.status,
            "rejection_reason": getattr(c, "rejection_reason", None),
            "rejection_clause": getattr(c, "rejection_clause", None),
            "requires_dispute_appeal": getattr(c, "requires_dispute_appeal", False),
            "admission": adm,
        }

    if entity_type == "discharge":
        d = b.discharges.get(entity_id)
        if not d: return {"error": f"Discharge {entity_id} not found"}
        pat = _pat(d.uhid)
        return {
            "type": "discharge", "id": d.discharge_id,
            "discharge_id": d.discharge_id, "admission_id": d.admission_id,
            "uhid": d.uhid, "patient": pat, "bed_id": d.bed_id,
            "discharge_type": d.discharge_type, "final_diagnosis": d.final_diagnosis,
            "clearance_clinical": d.clearance_clinical, "clearance_pharmacy": d.clearance_pharmacy,
            "clearance_billing": d.clearance_billing, "clearance_nursing": d.clearance_nursing,
            "is_blocked": d.is_blocked, "blocker_reason": d.blocker_reason,
            "resolution_team_extension": d.resolution_team_extension,
            "gate_pass_issued": d.gate_pass_issued, "status": d.status,
        }

    if entity_type == "alert":
        a = b.lab_critical_alerts.get(entity_id)
        if not a: return {"error": f"Alert {entity_id} not found"}
        pat = _pat(a.uhid)
        return {
            "type": "alert", "id": a.alert_id,
            "alert_id": a.alert_id, "order_id": getattr(a, "order_id", "—"),
            "uhid": a.uhid, "patient": pat,
            "patient_name": a.patient_name, "parameter_name": a.parameter_name,
            "critical_value": a.critical_value, "alert_time": a.alert_time,
            "doctor_contacted": a.doctor_contacted, "doctor_phone": getattr(a, "doctor_phone", "—"),
            "readback_status": a.readback_status,
            "sla_minutes": a.sla_minutes, "elapsed_minutes": a.elapsed_minutes,
            "is_sla_breached": a.is_sla_breached,
            "ack_time": getattr(a, "ack_time", None),
        }

    if entity_type == "bed":
        bed = b.beds.get(entity_id)
        if not bed: return {"error": f"Bed {entity_id} not found"}
        pat = _pat(bed.current_patient_uhid or "") if bed.current_patient_uhid else {}
        return {
            "type": "bed", "id": bed.bed_id,
            "bed_id": bed.bed_id, "ward": bed.ward, "department_id": bed.department_id,
            "bed_type": bed.bed_type, "status": bed.status,
            "current_patient_uhid": bed.current_patient_uhid or "—",
            "patient": pat,
            "active_admission_id": bed.active_admission_id or "—",
            "last_turnaround": getattr(bed, "last_turnaround_timestamp", "—"),
        }

    if entity_type == "patient":
        p = b.patients.get(entity_id)
        if not p: return {"error": f"Patient {entity_id} not found"}
        # Linked discharges
        patient_dis = [d for d in b.discharges.values() if d.uhid == entity_id]
        patient_claims = [c for c in b.claims.values() if c.uhid == entity_id]
        patient_alerts = [a for a in b.lab_critical_alerts.values() if a.uhid == entity_id]
        adm_id = p.active_admission_id or ""
        adm = _adm(adm_id)
        return {
            "type": "patient", "id": p.uhid,
            "uhid": p.uhid, "name": p.name, "age": p.age, "gender": p.gender,
            "contact": p.contact, "registration_date": p.registration_date,
            "status": p.status, "current_bed_id": p.current_bed_id or "—",
            "admission": adm,
            "discharges": [{"id": d.discharge_id, "status": d.status, "is_blocked": d.is_blocked,
                            "blocker": d.blocker_reason} for d in patient_dis],
            "claims": [{"id": c.claim_id, "tpa": c.tpa, "amount": c.claim_amount,
                        "status": c.status, "rejection": getattr(c,"rejection_reason",None)}
                       for c in patient_claims],
            "alerts": [{"id": a.alert_id, "param": a.parameter_name, "value": a.critical_value,
                        "status": a.readback_status, "breached": a.is_sla_breached}
                       for a in patient_alerts],
        }

    return {"error": f"Unknown entity type: {entity_type}"}


# ─────────────────────────────────────────────────────────────────────────────
# NODE LIFECYCLE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/v1/ops/prune")
async def prune_expired_nodes() -> Dict[str, Any]:
    """Manually trigger the node TTL pruner. Also runs automatically after every sync."""
    from app.ontology.graph_service import get_ontology_graph_service
    svc = get_ontology_graph_service()
    if not svc or not svc.builder:
        return {"error": "Graph not initialised"}
    from app.ontology.node_lifecycle import prune_builder
    result = prune_builder(svc.builder)
    try:
        from app.ontology.shared_state import audit
        audit("ACTION", "PRUNER", "prune_expired_nodes",
              f"Removed {result['pruned_total']} expired nodes: {result['by_type']}")
    except Exception:
        pass
    return result


@router.get("/api/v1/ops/lifecycle/stats")
async def lifecycle_stats() -> Dict[str, Any]:
    """Return per-type node counts and TTL policy."""
    from app.ontology.graph_service import get_ontology_graph_service
    from app.ontology.node_lifecycle import NODE_TTL_HOURS
    svc = get_ontology_graph_service()
    if not svc or not svc.builder:
        return {"error": "Graph not initialised"}
    b = svc.builder
    collections = [
        ("patients", "PatientNode"), ("admissions", "AdmissionNode"),
        ("discharges", "DischargeNode"), ("lab_critical_alerts", "LabPanicAlertNode"),
        ("lab_results", "LabResultNode"), ("bills", "BillNode"),
        ("claims", "ClaimNode"), ("prescriptions", "PrescriptionNode"),
        ("emergency_cases", "EmergencyCaseNode"), ("beds", "BedNode"),
        ("sops", "SOPNode"), ("policies", "PolicyNode"),
        ("articles", "KnowledgeArticleNode"),
    ]
    stats = {}
    for attr, ntype in collections:
        count = len(getattr(b, attr, {}))
        ttl = NODE_TTL_HOURS.get(ntype)
        stats[ntype] = {"count": count, "ttl_hours": ttl,
                        "ttl_label": f"{ttl}h" if ttl else "permanent"}
    return {"node_stats": stats, "timestamp": datetime.now(timezone.utc).isoformat()}


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND CENTER HTML
# ─────────────────────────────────────────────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SMCH Operations Command Center</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #020817; --surface: #0d1117; --surface2: #161b22; --surface3: #1c2128;
      --border: #21262d; --border2: #30363d;
      --text: #e6edf3; --muted: #7d8590; --subtle: #484f58;
      --red: #f85149; --red-dim: #490202; --red-border: #6e1a1a;
      --amber: #d29922; --amber-dim: #2d1e00; --amber-border: #5a3e00;
      --green: #3fb950; --green-dim: #0d2a15; --green-border: #1a5429;
      --blue: #388bfd; --blue-dim: #0d1f3c; --blue-border: #1a3a6e;
      --purple: #a371f7; --purple-dim: #1e1040; --purple-border: #3d1e8e;
      --font: 'Inter', system-ui, sans-serif; --mono: 'JetBrains Mono', monospace;
    }
    html, body { height: 100%; background: var(--bg); color: var(--text); font-family: var(--font); font-size: 13px; overflow: hidden; }

    /* ── TOP BAR ── */
    .topbar {
      position: fixed; top: 0; left: 0; right: 0; height: 48px; z-index: 200;
      background: var(--surface); border-bottom: 1px solid var(--border);
      display: flex; align-items: center; justify-content: space-between; padding: 0 20px;
    }
    .topbar-left { display: flex; align-items: center; gap: 12px; }
    .brand { font-size: 14px; font-weight: 800; letter-spacing: -0.02em; }
    .brand span { color: var(--blue); }
    .brand-sep { color: var(--subtle); }
    .brand-sub { font-size: 11px; color: var(--muted); }
    .live-pill {
      display: flex; align-items: center; gap: 5px;
      background: var(--green-dim); border: 1px solid var(--green-border);
      color: var(--green); padding: 2px 9px; border-radius: 20px; font-size: 10px; font-weight: 700;
    }
    .live-dot { width: 5px; height: 5px; background: var(--green); border-radius: 50%; animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
    .topbar-right { display: flex; align-items: center; gap: 12px; }
    .sync-lbl { font-size: 10px; color: var(--subtle); font-family: var(--mono); }
    .role-badge { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: var(--purple-dim); color: var(--purple); border: 1px solid var(--purple-border); }
    .graph-btn { font-size: 11px; color: var(--muted); padding: 4px 10px; border: 1px solid var(--border); border-radius: 5px; text-decoration: none; }
    .graph-btn:hover { color: var(--text); border-color: var(--border2); }

    /* ── LAYOUT ── */
    .layout { display: flex; height: 100vh; padding-top: 48px; }

    /* ── SIDEBAR ── */
    .sidebar {
      width: 210px; flex-shrink: 0; background: #0A1628;
      border-right: 1px solid rgba(99,102,241,0.2);
      display: flex; flex-direction: column; overflow-y: auto;
      padding: 12px 8px;
    }
    .sidebar-group { margin-bottom: 16px; }
    .sidebar-group-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--subtle); padding: 0 8px; margin-bottom: 4px; }
    .sidebar-item {
      display: flex; align-items: center; gap: 9px;
      padding: 8px 10px; border-radius: 6px; cursor: pointer;
      font-size: 12px; font-weight: 500; color: var(--muted);
      transition: all 0.12s; border-left: 3px solid transparent; margin-bottom: 2px;
    }
    .sidebar-item:hover { background: rgba(99,102,241,0.12); color: var(--text); }
    .sidebar-item.active { background: rgba(99,102,241,0.2); color: var(--text); border-left-color: #6366F1; font-weight: 600; }
    .sidebar-icon { font-size: 14px; width: 18px; text-align: center; }
    .sidebar-badge { margin-left: auto; font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 10px; background: var(--red-dim); color: var(--red); border: 1px solid var(--red-border); }
    .sidebar-badge.amber { background: var(--amber-dim); color: var(--amber); border-color: var(--amber-border); }

    /* ── CONTENT ── */
    .content { flex: 1; overflow-y: auto; padding: 16px 20px 32px; }
    .section { display: none; }
    .section.active { display: block; }

    /* ── SECTION HEADER ── */
    .sec-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
    .sec-title { font-size: 16px; font-weight: 800; color: var(--text); }
    .sec-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }

    /* ── KPI STRIP ── */
    .kpi-strip { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; margin-bottom: 16px; }
    .kpi-card {
      background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
      padding: 12px 14px; display: flex; flex-direction: column; gap: 3px;
    }
    .kpi-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted); }
    .kpi-value { font-size: 24px; font-weight: 800; color: var(--text); font-variant-numeric: tabular-nums; line-height: 1; }
    .kpi-sub { font-size: 9px; color: var(--muted); }
    .kpi-card.red { border-color: var(--red-border); background: var(--red-dim); }
    .kpi-card.red .kpi-value { color: var(--red); }
    .kpi-card.amber { border-color: var(--amber-border); background: var(--amber-dim); }
    .kpi-card.amber .kpi-value { color: var(--amber); }
    .kpi-card.green .kpi-value { color: var(--green); }
    .kpi-card.blue .kpi-value { color: var(--blue); }

    /* ── CHARTS ROW ── */
    .charts-row { display: grid; grid-template-columns: 200px 1fr 200px; gap: 12px; margin-bottom: 16px; }
    .chart-panel { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
    .chart-panel-hdr { padding: 8px 12px; border-bottom: 1px solid var(--border); font-size: 11px; font-weight: 700; color: var(--text); }
    .chart-body { padding: 10px; display: flex; align-items: center; justify-content: center; min-height: 160px; }
    .chart-body canvas { max-height: 160px; }

    /* ── PANELS ── */
    .panels-row { display: grid; gap: 12px; margin-bottom: 14px; }
    .panels-2 { grid-template-columns: 1fr 1fr; }
    .panels-3 { grid-template-columns: 1fr 1fr 1fr; }
    .panel { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; }
    .panel-hdr { padding: 10px 14px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }
    .panel-title { font-size: 11px; font-weight: 700; color: var(--text); display: flex; align-items: center; gap: 8px; }
    .panel-sub { font-size: 10px; color: var(--muted); }
    .panel-body { overflow-y: auto; flex: 1; }
    .panel-body.pad { padding: 10px; }

    /* ── BADGES / PILLS ── */
    .badge { font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 10px; font-family: var(--mono); }
    .badge-red { background: var(--red-dim); color: var(--red); border: 1px solid var(--red-border); }
    .badge-green { background: var(--green-dim); color: var(--green); border: 1px solid var(--green-border); }
    .badge-amber { background: var(--amber-dim); color: var(--amber); border: 1px solid var(--amber-border); }
    .badge-blue { background: var(--blue-dim); color: var(--blue); border: 1px solid var(--blue-border); }
    .badge-muted { background: var(--surface2); color: var(--muted); border: 1px solid var(--border); }
    .badge-purple { background: var(--purple-dim); color: var(--purple); border: 1px solid var(--purple-border); }

    /* ── TABLES ── */
    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    thead tr { background: var(--surface2); }
    thead th { padding: 7px 10px; text-align: left; font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); border-bottom: 1px solid var(--border); white-space: nowrap; }
    tbody tr { border-bottom: 1px solid var(--border); transition: background 0.1s; }
    tbody tr:hover { background: var(--surface2); }
    tbody tr:last-child { border-bottom: none; }
    td { padding: 7px 10px; color: var(--text); vertical-align: middle; }
    .mono { font-family: var(--mono); font-size: 10px; color: var(--muted); }
    .dimmed { color: var(--muted); }
    .row-red { border-left: 3px solid var(--red); }
    .row-amber { border-left: 3px solid var(--amber); }
    .row-green { border-left: 3px solid var(--green); }

    /* ── DISCHARGE CARDS ── */
    .dis-cards { display: flex; flex-direction: column; gap: 8px; padding: 8px; max-height: 440px; overflow-y: auto; }
    .dis-card { background: var(--surface2); border: 1px solid var(--border2); border-radius: 7px; padding: 11px 13px; display: flex; flex-direction: column; gap: 9px; }
    .dis-card:hover { border-color: var(--red-border); }
    .dis-card-top { display: flex; justify-content: space-between; align-items: flex-start; }
    .dis-name { font-size: 12px; font-weight: 700; }
    .dis-meta { font-size: 10px; color: var(--muted); font-family: var(--mono); margin-top: 2px; }
    .dis-steps { display: flex; align-items: center; }
    .dis-step { display: flex; flex-direction: column; align-items: center; gap: 3px; flex-shrink: 0; }
    .step-circle { width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: 700; border: 1px solid var(--border2); background: var(--surface); color: var(--muted); }
    .step-lbl { font-size: 8px; color: var(--muted); text-align: center; width: 44px; }
    .dis-step.done .step-circle { background: var(--green-dim); border-color: var(--green-border); color: var(--green); }
    .dis-step.active .step-circle { background: var(--red-dim); border-color: var(--red-border); color: var(--red); font-size: 10px; }
    .step-line { flex: 1; height: 2px; background: var(--border2); min-width: 6px; margin-bottom: 13px; }
    .step-line.done { background: var(--green-border); }
    .dis-blocker { font-size: 10px; color: var(--red); background: var(--red-dim); border: 1px solid var(--red-border); border-radius: 4px; padding: 4px 8px; }
    .dis-actions { display: flex; gap: 7px; flex-wrap: wrap; }

    /* ── ALERT CARDS ── */
    .alert-cards { display: flex; flex-direction: column; gap: 8px; padding: 8px; max-height: 440px; overflow-y: auto; }
    .alert-card { background: var(--surface2); border: 1px solid var(--border2); border-radius: 7px; padding: 11px 13px; display: flex; flex-direction: column; gap: 7px; }
    .alert-card.breached { border-color: var(--red-border); }
    .alert-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
    .alert-patient { font-size: 12px; font-weight: 700; }
    .alert-uhid { font-size: 10px; color: var(--muted); font-family: var(--mono); }
    .alert-value { font-size: 13px; font-weight: 700; color: var(--red); }
    .sla-row { display: flex; align-items: center; gap: 8px; }
    .sla-track { flex: 1; height: 4px; background: var(--surface); border-radius: 2px; overflow: hidden; }
    .sla-fill { height: 100%; border-radius: 2px; background: var(--green); transition: width 0.4s; }
    .sla-fill.warn { background: var(--amber); }
    .sla-fill.crit { background: var(--red); }
    .sla-lbl { font-size: 10px; font-family: var(--mono); color: var(--muted); white-space: nowrap; }

    /* ── BED GRID ── */
    .bed-filters { display: flex; gap: 8px; padding: 10px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
    .bed-filters select, .bed-filters input { background: var(--surface2); border: 1px solid var(--border2); color: var(--text); padding: 5px 9px; border-radius: 5px; font-size: 11px; font-family: var(--font); }
    .bed-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; padding: 10px; }
    .bed-card { background: var(--surface2); border: 1px solid var(--border2); border-radius: 6px; padding: 9px 10px; display: flex; flex-direction: column; gap: 5px; }
    .bed-card.occupied { border-left: 3px solid var(--red); }
    .bed-card.vacant { border-left: 3px solid var(--green); }
    .bed-card.dirty { border-left: 3px solid var(--amber); }
    .bed-id { font-size: 10px; font-weight: 700; font-family: var(--mono); color: var(--text); display: flex; justify-content: space-between; align-items: center; }
    .bed-pat { font-size: 10px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .bed-ward-lbl { font-size: 9px; color: var(--subtle); }
    .bed-btns { display: flex; gap: 4px; margin-top: 2px; }
    .assign-form { display: none; margin-top: 5px; }
    .assign-form.open { display: flex; gap: 4px; }
    .assign-form input { flex: 1; background: var(--bg); border: 1px solid var(--border2); color: var(--text); padding: 3px 6px; border-radius: 4px; font-size: 10px; font-family: var(--mono); min-width: 0; }

    /* ── BUTTONS ── */
    .btn { display: inline-flex; align-items: center; gap: 4px; padding: 5px 10px; border-radius: 5px; font-size: 11px; font-weight: 600; cursor: pointer; border: none; transition: all 0.12s; font-family: var(--font); }
    .btn-blue { background: var(--blue-dim); color: var(--blue); border: 1px solid var(--blue-border); }
    .btn-blue:hover { background: #1a3a6e; }
    .btn-green { background: var(--green-dim); color: var(--green); border: 1px solid var(--green-border); }
    .btn-green:hover { background: #1a5429; }
    .btn-amber { background: var(--amber-dim); color: var(--amber); border: 1px solid var(--amber-border); }
    .btn-amber:hover { background: #3d2a00; }
    .btn-red { background: var(--red-dim); color: var(--red); border: 1px solid var(--red-border); }
    .btn-red:hover { background: #6e1a1a; }
    .btn-muted { background: var(--surface2); color: var(--muted); border: 1px solid var(--border2); }
    .btn-muted:hover { color: var(--text); border-color: var(--border); }
    .btn-sm { padding: 3px 7px; font-size: 10px; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    /* ── PATIENT SEARCH ── */
    .search-bar { padding: 12px 14px; border-bottom: 1px solid var(--border); }
    .search-bar input { width: 100%; background: var(--surface2); border: 1px solid var(--border2); color: var(--text); padding: 8px 12px; border-radius: 6px; font-size: 12px; font-family: var(--font); }
    .search-bar input:focus { outline: none; border-color: var(--blue-border); }
    .patient-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; padding: 10px; }
    .patient-card { background: var(--surface2); border: 1px solid var(--border2); border-radius: 7px; padding: 11px 13px; display: flex; flex-direction: column; gap: 6px; }
    .patient-card:hover { border-color: var(--blue-border); }
    .pat-name { font-size: 13px; font-weight: 700; }
    .pat-uhid { font-size: 10px; font-family: var(--mono); color: var(--muted); }
    .pat-row { display: flex; gap: 8px; flex-wrap: wrap; font-size: 10px; color: var(--muted); }
    .pat-actions { display: flex; gap: 6px; margin-top: 4px; }

    /* ── MODAL ── */
    .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 500; display: none; align-items: center; justify-content: center; }
    .modal-overlay.open { display: flex; }
    .modal { background: var(--surface); border: 1px solid var(--border2); border-radius: 10px; width: 600px; max-width: 95vw; max-height: 80vh; overflow-y: auto; padding: 20px; }
    .modal-title { font-size: 15px; font-weight: 800; margin-bottom: 14px; display: flex; justify-content: space-between; }
    .modal-close { cursor: pointer; color: var(--muted); font-size: 18px; }
    .modal-section { margin-bottom: 12px; }
    .modal-section-title { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin-bottom: 6px; border-bottom: 1px solid var(--border); padding-bottom: 4px; }
    .modal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .modal-field { display: flex; flex-direction: column; gap: 2px; }
    .modal-field label { font-size: 9px; color: var(--subtle); text-transform: uppercase; }
    .modal-field span { font-size: 12px; color: var(--text); font-family: var(--mono); }

    /* ── REPORTS ── */
    .report-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; padding: 10px; }
    .report-card { background: var(--surface2); border: 1px solid var(--border2); border-radius: 7px; padding: 14px; display: flex; flex-direction: column; gap: 8px; }
    .report-title { font-size: 12px; font-weight: 700; }
    .report-desc { font-size: 10px; color: var(--muted); }

    /* ── CLAIMS TABS ── */
    .tab-bar { display: flex; border-bottom: 1px solid var(--border); padding: 0 12px; }
    .tab { padding: 8px 12px; font-size: 11px; font-weight: 600; color: var(--muted); cursor: pointer; border-bottom: 2px solid transparent; }
    .tab.active { color: var(--blue); border-bottom-color: var(--blue); }

    /* ── ACTIVITY FEED ── */
    .activity-feed { padding: 8px; display: flex; flex-direction: column; gap: 6px; max-height: 280px; overflow-y: auto; }
    .activity-item { display: flex; gap: 8px; align-items: flex-start; padding: 6px 8px; border-radius: 5px; background: var(--surface2); }
    .activity-dot { width: 7px; height: 7px; border-radius: 50%; margin-top: 4px; flex-shrink: 0; }
    .activity-text { font-size: 10px; color: var(--muted); line-height: 1.5; }

    /* ── AGENT CHAT ── */
    .chat-layout { display: flex; flex-direction: column; height: 600px; }
    .chat-messages { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 10px; }
    .chat-msg { max-width: 80%; padding: 9px 13px; border-radius: 8px; font-size: 12px; line-height: 1.6; white-space: pre-wrap; }
    .chat-msg.user { align-self: flex-end; background: var(--blue-dim); border: 1px solid var(--blue-border); color: var(--text); }
    .chat-msg.assistant { align-self: flex-start; background: var(--surface2); border: 1px solid var(--border2); color: var(--text); }
    .chat-msg.system { align-self: center; background: transparent; border: none; color: var(--muted); font-size: 10px; font-style: italic; }
    .chat-msg.guardrail { align-self: flex-start; background: var(--red-dim); border: 1px solid var(--red-border); color: var(--red); }
    .chat-thinking { display: flex; gap: 4px; align-items: center; padding: 10px 14px !important; min-height: 36px; }
    .tdot { width: 7px; height: 7px; background: #6366F1; border-radius: 50%; animation: tdot-blink 1.2s infinite; flex-shrink: 0; }
    .tdot:nth-child(2) { animation-delay: 0.2s; }
    .tdot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes tdot-blink { 0%,80%,100% { opacity:0.2; transform:scale(0.8); } 40% { opacity:1; transform:scale(1.1); } }
    .chat-input-row { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--border); }
    .chat-input-row input { flex: 1; background: var(--surface2); border: 1px solid var(--border2); color: var(--text); padding: 8px 12px; border-radius: 6px; font-size: 12px; font-family: var(--font); }
    .chat-input-row input:focus { outline: none; border-color: var(--blue-border); }
    .chat-confidence { font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 10px; margin-bottom: 4px; display: inline-block; }
    .conf-HIGH { background: var(--green-dim); color: var(--green); border: 1px solid var(--green-border); }
    .conf-MEDIUM { background: var(--amber-dim); color: var(--amber); border: 1px solid var(--amber-border); }
    .conf-LOW, .conf-UNCERTAIN { background: var(--red-dim); color: var(--red); border: 1px solid var(--red-border); }
    .chat-citations { font-size: 9px; color: var(--subtle); margin-top: 4px; font-family: var(--mono); }
    .chat-workflow { margin-top: 6px; background: var(--green-dim); border: 1px solid var(--green-border); border-radius: 5px; padding: 7px 10px; font-size: 10px; }
    .chat-wf-title { font-weight: 700; color: var(--green); margin-bottom: 3px; }
    .chat-wf-action { color: var(--text); }
    .chat-wf-contact { color: var(--green); font-family: var(--mono); margin-top: 2px; }

    /* ── WARD BARS ── */
    .ward-rows { padding: 4px 0; }
    .ward-row { display: flex; align-items: center; gap: 8px; padding: 5px 12px; border-bottom: 1px solid var(--border); }
    .ward-row:last-child { border-bottom: none; }
    .ward-name { font-size: 10px; color: var(--text); width: 160px; flex-shrink: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .ward-track { flex: 1; height: 5px; background: var(--surface2); border-radius: 3px; overflow: hidden; }
    .ward-fill { height: 100%; border-radius: 3px; background: var(--blue); transition: width 0.4s; }
    .ward-fill.high { background: var(--amber); }
    .ward-fill.crit { background: var(--red); }
    .ward-pct { font-size: 10px; font-family: var(--mono); color: var(--muted); width: 32px; text-align: right; }
    .ward-cnt { font-size: 9px; color: var(--subtle); font-family: var(--mono); width: 60px; text-align: right; }

    /* ── SLA TABLE ── */
    .sla-breached-row { background: rgba(248,81,73,0.05); }

    /* ── LOADING / TOAST ── */
    #loadingOverlay { position: fixed; inset: 0; background: var(--bg); z-index: 999; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; }
    .spinner { width: 28px; height: 28px; border: 2px solid var(--border2); border-top-color: var(--blue); border-radius: 50%; animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .toast { position: fixed; bottom: 20px; right: 20px; z-index: 9999; padding: 9px 16px; border-radius: 7px; font-size: 11px; font-weight: 600; opacity: 0; transform: translateY(6px); transition: all 0.25s; pointer-events: none; max-width: 300px; }
    .toast.show { opacity: 1; transform: translateY(0); }
    .toast.success { background: var(--green-dim); color: var(--green); border: 1px solid var(--green-border); }
    .toast.error { background: var(--red-dim); color: var(--red); border: 1px solid var(--red-border); }
    .toast.info { background: var(--blue-dim); color: var(--blue); border: 1px solid var(--blue-border); }

    .empty { padding: 20px; text-align: center; color: var(--muted); font-size: 11px; }
    .revenue-big { font-size: 32px; font-weight: 900; color: var(--amber); font-variant-numeric: tabular-nums; }
    .sec-kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px; }
    .sec-kpi { background: var(--surface2); border: 1px solid var(--border); border-radius: 7px; padding: 10px 12px; }
    .sec-kpi-lbl { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }
    .sec-kpi-val { font-size: 20px; font-weight: 800; color: var(--text); line-height: 1.2; }
  </style>
</head>
<body>
<div id="loadingOverlay">
  <div class="spinner"></div>
  <p style="font-size:11px;color:var(--muted);">Loading operational data…</p>
</div>

<header class="topbar">
  <div class="topbar-left">
    <div class="brand">SMCH <span>OPS</span></div>
    <span class="brand-sep">/</span>
    <span class="brand-sub">Operations Command Center</span>
    <div class="live-pill"><span class="live-dot"></span>LIVE</div>
  </div>
  <div class="topbar-right">
    <span class="sync-lbl" id="syncTime">Connecting…</span>
    <select id="roleSelector" onchange="setRole(this.value)" style="background:rgba(99,102,241,0.15);border:1px solid rgba(99,102,241,0.3);color:#E2E8F0;border-radius:5px;padding:4px 10px;font-size:11px;cursor:pointer;">
      <option value="ADMIN">&#x1F451; Admin</option>
      <option value="DOCTOR">&#x1FA7A; Doctor</option>
      <option value="NURSE">&#x1F489; Nurse</option>
      <option value="BILLING_STAFF">&#x1F4B3; Billing</option>
    </select>
    <span class="role-badge" id="roleBadgeLabel">ADMIN</span>
    <a href="/" class="graph-btn">Graph View</a>
  </div>
</header>

<div class="layout">
  <nav class="sidebar">
    <div class="sidebar-group">
      <div class="sidebar-group-label">Overview</div>
      <div class="sidebar-item active" id="nav-overview" onclick="showSection('overview')"><span class="sidebar-icon">🏠</span>Overview</div>
    </div>
    <div class="sidebar-group">
      <div class="sidebar-group-label">Operations</div>
      <div class="sidebar-item" id="nav-beds" onclick="showSection('beds')"><span class="sidebar-icon">🛏️</span>Bed Operations</div>
      <div class="sidebar-item" id="nav-discharge" onclick="showSection('discharge')"><span class="sidebar-icon">🚪</span>Discharge Hub<span class="sidebar-badge" id="sb-block">0</span></div>
      <div class="sidebar-item" id="nav-alerts" onclick="showSection('alerts')"><span class="sidebar-icon">⚗️</span>Lab &amp; Alerts<span class="sidebar-badge" id="sb-alert">0</span></div>
      <div class="sidebar-item" id="nav-billing" onclick="showSection('billing')"><span class="sidebar-icon">💳</span>Billing &amp; Claims</div>
    </div>
    <div class="sidebar-group">
      <div class="sidebar-group-label">Analytics</div>
      <div class="sidebar-item" id="nav-revenue" onclick="showSection('revenue')"><span class="sidebar-icon">📈</span>Revenue Analytics<span class="sidebar-badge amber" id="sb-rev"></span></div>
      <div class="sidebar-item" id="nav-patients" onclick="showSection('patients')"><span class="sidebar-icon">👥</span>Patient Lookup</div>
    </div>
    <div class="sidebar-group">
      <div class="sidebar-group-label">Tools</div>
      <div class="sidebar-item" id="nav-reports" onclick="showSection('reports')"><span class="sidebar-icon">📋</span>Reports</div>
      <div class="sidebar-item" id="nav-approvals" onclick="showSection('approvals')"><span class="sidebar-icon">✅</span>Approvals <span id="approvalBadge" style="background:var(--red);color:white;border-radius:9999px;padding:1px 6px;font-size:9px;margin-left:4px;display:none">0</span></div>
      <div class="sidebar-item" id="nav-audit" onclick="showSection('audit')"><span class="sidebar-icon">📜</span>Audit Trail</div>
      <div class="sidebar-item" id="nav-agent" onclick="showSection('agent')"><span class="sidebar-icon">🤖</span>AI Assistant</div>
    </div>
  </nav>

  <main class="content" id="mainContent">

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- SECTION: OVERVIEW                                                      -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="section active" id="section-overview">
      <div class="sec-header">
        <div><div class="sec-title">Operations Overview</div><div class="sec-sub">Real-time hospital operational intelligence</div></div>
      </div>

      <div class="kpi-strip">
        <div class="kpi-card blue"><div class="kpi-label">Total Patients</div><div class="kpi-value" id="kpiPatients">—</div><div class="kpi-sub">Active inpatients</div></div>
        <div class="kpi-card" id="kpiOccCard"><div class="kpi-label">Bed Occupancy</div><div class="kpi-value" id="kpiOcc">—</div><div class="kpi-sub" id="kpiOccSub">—</div></div>
        <div class="kpi-card" id="kpiBlockCard"><div class="kpi-label">Blocked Discharges</div><div class="kpi-value" id="kpiBlock">—</div><div class="kpi-sub">Clearance pending</div></div>
        <div class="kpi-card" id="kpiSLACard"><div class="kpi-label">SLA Breaches</div><div class="kpi-value" id="kpiSLA">—</div><div class="kpi-sub">Lab readback overdue</div></div>
        <div class="kpi-card" id="kpiDirtyCard"><div class="kpi-label">Dirty Beds</div><div class="kpi-value" id="kpiDirty">—</div><div class="kpi-sub">Turnaround queue</div></div>
        <div class="kpi-card amber" id="kpiRevCard"><div class="kpi-label">Revenue at Risk</div><div class="kpi-value" id="kpiRev">—</div><div class="kpi-sub">Claims at risk</div></div>
      </div>

      <div class="charts-row">
        <div class="chart-panel">
          <div class="chart-panel-hdr">Bed Status</div>
          <div class="chart-body"><canvas id="bedDonut"></canvas></div>
        </div>
        <div class="chart-panel">
          <div class="chart-panel-hdr">Ward Occupancy — Top 8</div>
          <div class="chart-body" style="padding:10px 6px;"><canvas id="wardBar" style="max-height:160px;"></canvas></div>
        </div>
        <div class="chart-panel">
          <div class="chart-panel-hdr">Discharge Status</div>
          <div class="chart-body"><canvas id="dischDonut"></canvas></div>
        </div>
      </div>

      <div class="panels-row panels-2" style="margin-bottom:14px;">
        <div class="panel">
          <div class="panel-hdr">
            <div class="panel-title">Blocked Discharges <span class="badge badge-red" id="ovBlockBadge">0</span></div>
            <span class="panel-sub">4-step clearance matrix</span>
          </div>
          <div class="panel-body">
            <div class="dis-cards" id="ovBlockedCards"><div class="empty">Loading…</div></div>
          </div>
        </div>
        <div class="panel">
          <div class="panel-hdr">
            <div class="panel-title">SLA Breach Tracker <span class="badge badge-red" id="ovSLABadge">0</span></div>
            <span class="panel-sub">POL-010 · 15-min readback</span>
          </div>
          <div class="panel-body">
            <div class="alert-cards" id="ovAlertCards"><div class="empty">Loading…</div></div>
          </div>
        </div>
      </div>

      <div class="panels-row panels-2">
        <div class="panel">
          <div class="panel-hdr">
            <div class="panel-title">Ward Fleet</div>
            <span class="panel-sub" id="ovBedSub">—</span>
          </div>
          <div class="panel-body">
            <div class="ward-rows" id="ovWardRows"></div>
          </div>
        </div>
        <div class="panel">
          <div class="panel-hdr">
            <div class="panel-title">Revenue &amp; Claims <span class="badge badge-amber" id="ovRevBadge">—</span></div>
            <span class="panel-sub">TPA / Disputes</span>
          </div>
          <div class="panel-body">
            <div id="ovClaimCards" style="padding:8px;display:flex;flex-direction:column;gap:5px;max-height:280px;overflow-y:auto;"></div>
          </div>
        </div>
      </div>

      <!-- Node Lifecycle / TTL panel -->
      <div class="panel" style="margin-top:16px;">
        <div class="panel-hdr" style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div class="panel-title">Graph Node Lifecycle</div>
            <span class="panel-sub">TTL-based expiry · Context decay prevention · Storage cost control</span>
          </div>
          <button class="btn btn-amber btn-sm" onclick="runPruner()">⚡ Run Pruner</button>
        </div>
        <div class="panel-body">
          <div id="lifecycleStats" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;padding:8px;">
            <div class="empty">Loading lifecycle stats…</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- SECTION: BED OPERATIONS                                                -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="section" id="section-beds">
      <div class="sec-header">
        <div><div class="sec-title">Bed Operations</div><div class="sec-sub">Assign, clean, and track every bed in real time</div></div>
      </div>
      <div class="sec-kpi-row">
        <div class="sec-kpi"><div class="sec-kpi-lbl">Occupied</div><div class="sec-kpi-val" id="bedKpiOcc">—</div></div>
        <div class="sec-kpi"><div class="sec-kpi-lbl">Vacant</div><div class="sec-kpi-val" id="bedKpiVac" style="color:var(--green)">—</div></div>
        <div class="sec-kpi"><div class="sec-kpi-lbl">Dirty</div><div class="sec-kpi-val" id="bedKpiDirty" style="color:var(--amber)">—</div></div>
        <div class="sec-kpi"><div class="sec-kpi-lbl">Occupancy %</div><div class="sec-kpi-val" id="bedKpiPct">—</div></div>
      </div>
      <div class="panel">
        <div class="bed-filters">
          <select id="bedWardFilter" onchange="filterBeds()"><option value="">All Wards</option></select>
          <select id="bedStatusFilter" onchange="filterBeds()">
            <option value="">All Statuses</option>
            <option value="occupied">Occupied</option>
            <option value="vacant">Vacant</option>
            <option value="dirty">Dirty</option>
          </select>
          <input type="text" id="bedSearch" placeholder="Search bed ID…" oninput="filterBeds()" style="width:160px;">
        </div>
        <div class="bed-grid" id="bedGrid"><div class="empty">Loading beds…</div></div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- SECTION: DISCHARGE HUB                                                 -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="section" id="section-discharge">
      <div class="sec-header">
        <div><div class="sec-title">Discharge Hub</div><div class="sec-sub">Monitor and advance every discharge step</div></div>
      </div>
      <div class="sec-kpi-row">
        <div class="sec-kpi"><div class="sec-kpi-lbl">Total</div><div class="sec-kpi-val" id="disKpiTotal">—</div></div>
        <div class="sec-kpi"><div class="sec-kpi-lbl">Blocked</div><div class="sec-kpi-val" id="disKpiBlocked" style="color:var(--red)">—</div></div>
        <div class="sec-kpi"><div class="sec-kpi-lbl">Cleared</div><div class="sec-kpi-val" id="disKpiCleared" style="color:var(--green)">—</div></div>
        <div class="sec-kpi"><div class="sec-kpi-lbl">Gate Pass Issued</div><div class="sec-kpi-val" id="disKpiGate">—</div></div>
      </div>

      <div class="panel" style="margin-bottom:14px;">
        <div class="panel-hdr">
          <div class="panel-title">Blocked Discharges <span class="badge badge-red" id="disBlockBadge">0</span></div>
          <span class="panel-sub">Click "Advance" to mark current step complete</span>
        </div>
        <div class="panel-body">
          <div class="dis-cards" id="disBlockedCards" style="max-height:600px;"><div class="empty">Loading…</div></div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-hdr">
          <div class="panel-title">All Discharges <span class="badge badge-muted" id="disAllBadge">0</span></div>
        </div>
        <div class="panel-body">
          <table>
            <thead><tr><th>Patient</th><th>UHID</th><th>Bed</th><th>Ward</th><th>Clinical</th><th>Pharmacy</th><th>Billing</th><th>Nursing</th><th>Gate Pass</th><th>Blocked</th></tr></thead>
            <tbody id="disAllTable"><tr><td colspan="10" class="empty">Loading…</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- SECTION: LAB & ALERTS                                                  -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="section" id="section-alerts">
      <div class="sec-header">
        <div><div class="sec-title">Lab &amp; Critical Alerts</div><div class="sec-sub">POL-010 · 15-minute readback SLA</div></div>
      </div>
      <div class="sec-kpi-row">
        <div class="sec-kpi"><div class="sec-kpi-lbl">Total Alerts</div><div class="sec-kpi-val" id="altKpiTotal">—</div></div>
        <div class="sec-kpi"><div class="sec-kpi-lbl">SLA Breached</div><div class="sec-kpi-val" id="altKpiBreached" style="color:var(--red)">—</div></div>
        <div class="sec-kpi"><div class="sec-kpi-lbl">Within SLA</div><div class="sec-kpi-val" id="altKpiOK" style="color:var(--green)">—</div></div>
        <div class="sec-kpi"><div class="sec-kpi-lbl">Acknowledged</div><div class="sec-kpi-val" id="altKpiAck" style="color:var(--blue)">—</div></div>
      </div>
      <div class="panel">
        <div class="panel-hdr">
          <div class="panel-title">Active Alerts <span class="badge badge-red" id="altBadge">0</span></div>
          <span class="panel-sub">Sorted by elapsed time descending</span>
        </div>
        <div class="panel-body">
          <div class="alert-cards" id="altCards" style="max-height:700px;"><div class="empty">Loading…</div></div>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- SECTION: BILLING & CLAIMS                                               -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="section" id="section-billing">
      <div class="sec-header">
        <div><div class="sec-title">Billing &amp; Claims</div><div class="sec-sub">Update claim statuses and track TPA rejections</div></div>
      </div>
      <div class="sec-kpi-row" id="claimKPIs"></div>
      <div class="panel">
        <div class="tab-bar" id="claimTabBar">
          <div class="tab active" onclick="filterClaims('all', this)">All</div>
          <div class="tab" onclick="filterClaims('pending', this)">Pending</div>
          <div class="tab" onclick="filterClaims('rejected', this)">Rejected</div>
          <div class="tab" onclick="filterClaims('approved', this)">Approved</div>
        </div>
        <div class="panel-body">
          <table>
            <thead><tr><th>Claim ID</th><th>Patient</th><th>TPA / Insurer</th><th>Amount</th><th>Status</th><th>Rejection Reason</th><th>Actions</th></tr></thead>
            <tbody id="claimsTable"><tr><td colspan="7" class="empty">Loading…</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- SECTION: REVENUE ANALYTICS                                              -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="section" id="section-revenue">
      <div class="sec-header">
        <div><div class="sec-title">Revenue Analytics</div><div class="sec-sub">At-risk revenue, TPA breakdown, claims performance</div></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:14px;">
        <div class="panel" style="padding:16px;align-items:center;text-align:center;">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted);margin-bottom:6px;">Revenue at Risk</div>
          <div class="revenue-big" id="revBigNum">—</div>
          <div style="font-size:10px;color:var(--muted);margin-top:4px;">Rejected + Pending claims</div>
        </div>
        <div class="chart-panel">
          <div class="chart-panel-hdr">Claims by Status</div>
          <div class="chart-body"><canvas id="claimStatusChart"></canvas></div>
        </div>
        <div class="chart-panel">
          <div class="chart-panel-hdr">TPA Breakdown (₹)</div>
          <div class="chart-body"><canvas id="tpaChart"></canvas></div>
        </div>
      </div>
      <div class="panel">
        <div class="panel-hdr">
          <div class="panel-title">At-Risk Claims</div>
          <span class="panel-sub">Rejected and Pending — action required</span>
        </div>
        <div class="panel-body">
          <table>
            <thead><tr><th>Claim ID</th><th>Patient</th><th>TPA</th><th>Amount</th><th>Status</th><th>Risk Reason</th><th>Action</th></tr></thead>
            <tbody id="revRiskTable"><tr><td colspan="7" class="empty">Loading…</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- SECTION: PATIENT LOOKUP                                                 -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="section" id="section-patients">
      <div class="sec-header">
        <div><div class="sec-title">Patient Lookup</div><div class="sec-sub">Search by UHID, name, or ward</div></div>
      </div>
      <div class="panel">
        <div class="search-bar">
          <input type="text" id="patSearch" placeholder="Search by UHID, name, or ward…" oninput="filterPatients()">
        </div>
        <div class="patient-cards" id="patCards"><div class="empty">Loading patients…</div></div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- SECTION: REPORTS                                                        -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="section" id="section-reports">
      <div class="sec-header">
        <div><div class="sec-title">Reports</div><div class="sec-sub">Download operational reports as CSV</div></div>
      </div>
      <div class="report-cards">
        <div class="report-card">
          <div class="report-title">Daily Bed Occupancy</div>
          <div class="report-desc">All beds, wards, status, occupancy %</div>
          <button class="btn btn-blue" onclick="downloadReport('beds')">Download CSV</button>
        </div>
        <div class="report-card">
          <div class="report-title">Blocked Discharge Summary</div>
          <div class="report-desc">All blocked discharges with step status</div>
          <button class="btn btn-red" onclick="downloadReport('discharges')">Download CSV</button>
        </div>
        <div class="report-card">
          <div class="report-title">SLA Breach Report</div>
          <div class="report-desc">All lab critical alerts, SLA status, readback</div>
          <button class="btn btn-red" onclick="downloadReport('alerts')">Download CSV</button>
        </div>
        <div class="report-card">
          <div class="report-title">Revenue at Risk</div>
          <div class="report-desc">All at-risk claims with rejection reasons</div>
          <button class="btn btn-amber" onclick="downloadReport('revenue')">Download CSV</button>
        </div>
        <div class="report-card">
          <div class="report-title">Ward-wise Patient Census</div>
          <div class="report-desc">All patients grouped by ward</div>
          <button class="btn btn-muted" onclick="downloadReport('patients')">Download CSV</button>
        </div>
        <div class="report-card">
          <div class="report-title">Lab Critical Alerts Log</div>
          <div class="report-desc">Full history with doctor contact info</div>
          <button class="btn btn-muted" onclick="downloadReport('alertlog')">Download CSV</button>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- SECTION: APPROVALS                                                      -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="section" id="section-approvals">
      <div class="sec-header">
        <div><div class="sec-title">Human Approval Queue</div><div class="sec-sub">Actions flagged for human authorisation before execution</div></div>
        <button class="btn btn-muted btn-sm" onclick="loadApprovals()">&#8635; Refresh</button>
      </div>
      <div class="panel">
        <div class="panel-header"><span class="panel-title">Pending Approvals</span><span class="badge badge-red" id="aprCount">0</span></div>
        <div class="panel-body" style="overflow-x:auto;">
          <table class="data-table" style="width:100%">
            <thead><tr><th>ID</th><th>Query</th><th>Guardrail</th><th>Escalation Team</th><th>Reason</th><th>Time</th><th>Actions</th></tr></thead>
            <tbody id="approvalRows"><tr><td colspan="7" class="empty">No pending approvals</td></tr></tbody>
          </table>
        </div>
      </div>
      <div class="panel" style="margin-top:16px;">
        <div class="panel-header"><span class="panel-title">Recently Resolved</span></div>
        <div class="panel-body" style="overflow-x:auto;">
          <table class="data-table" style="width:100%">
            <thead><tr><th>ID</th><th>Query / Detail</th><th>Status</th><th>Resolved By</th><th>Resolved At</th></tr></thead>
            <tbody id="approvalHistoryRows"><tr><td colspan="5" class="empty">No resolved approvals yet</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- SECTION: AUDIT TRAIL                                                    -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="section" id="section-audit">
      <div class="sec-header">
        <div><div class="sec-title">Audit Trail</div><div class="sec-sub">Every agent query, guardrail trigger, operational action, and approval decision</div></div>
        <div style="display:flex;gap:8px;align-items:center;">
          <select id="auditTypeFilter" onchange="loadAuditLog()" style="background:var(--surface2);border:1px solid var(--border2);color:var(--text);border-radius:5px;padding:5px 8px;font-size:11px;">
            <option value="">All Events</option>
            <option value="QUERY">Queries</option>
            <option value="GUARDRAIL">Guardrails</option>
            <option value="ACTION">Actions</option>
            <option value="APPROVAL">Approvals</option>
            <option value="RBAC_DENY">RBAC Denials</option>
          </select>
          <button class="btn btn-muted btn-sm" onclick="loadAuditLog()">&#8635; Refresh</button>
        </div>
      </div>
      <div class="panel">
        <div class="panel-header"><span class="panel-title">Event Log</span><span id="auditCount" class="badge badge-muted">0 entries</span></div>
        <div class="panel-body" style="overflow-x:auto;">
          <table class="data-table" style="width:100%;min-width:700px;">
            <thead><tr><th>ID</th><th>Time</th><th>Type</th><th>Entity</th><th>Action</th><th>Detail</th><th>Role</th></tr></thead>
            <tbody id="auditRows"><tr><td colspan="7" class="empty">No audit entries yet — perform actions to see them here</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- SECTION: AI ASSISTANT                                                   -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <div class="section" id="section-agent">
      <div class="sec-header">
        <div><div class="sec-title">AI Operations Assistant</div><div class="sec-sub">Governed agent — grounded in live graph + institutional policies</div></div>
      </div>
      <div class="panel">
        <div class="chat-layout">
          <div class="chat-messages" id="chatMessages">
            <div class="chat-msg system">Ask any operational question. Grounded in the live knowledge graph and institutional SOPs.</div>
            <div class="chat-msg system" style="color:var(--muted);font-size:10px;">Try: "Why is Geetha Kuppuswamy's discharge blocked?" · "Which beds are vacant in Ward 3A?" · "How many SLA breaches are active?"</div>
          </div>
          <div class="chat-input-row">
            <input type="text" id="chatInput" placeholder="Ask an operational question…" onkeydown="if(event.key==='Enter')sendChat()">
            <button class="btn btn-blue" onclick="sendChat()">Send</button>
          </div>
        </div>
      </div>
    </div>

  </main>
</div>

<!-- Patient 360° Modal -->
<div class="modal-overlay" id="patModal">
  <div class="modal">
    <div class="modal-title"><span id="modalTitle">Patient 360°</span><span class="modal-close" onclick="closeModal()">&#10005;</span></div>
    <div id="modalBody"></div>
  </div>
</div>

<div class="toast" id="toastEl"></div>

<script>
// ── GLOBALS ──────────────────────────────────────────────────────────────────
const INR = v => '₹' + Number(v||0).toLocaleString('en-IN', {maximumFractionDigits:0});
const pill = (lbl, cls) => `<span class="badge badge-${cls}">${lbl}</span>`;
const chk = v => v ? '<span style="color:var(--green)">✓</span>' : '<span style="color:var(--red)">✗</span>';

let _liveData = null;
let _allBedRows = [];
let _allPatRows = [];
let _allClaimRows = [];
let _claimFilter = 'all';
let agentHistory = [];

// Charts
let bedDonut=null, wardBar=null, dischDonut=null, claimChart=null, tpaChart=null;

// ── NAVIGATION ───────────────────────────────────────────────────────────────
function showSection(name) {
  // RBAC gate — block access to sections the current role cannot see
  if (!_canSeeSection(name)) {
    const permitted = _permittedSections(_currentRole)[0] || 'overview';
    showToast('Your role does not have access to this section.', 'error');
    if (name !== permitted) showSection(permitted);
    return;
  }
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
  const sec = document.getElementById('section-' + name);
  const nav = document.getElementById('nav-' + name);
  if (sec) sec.classList.add('active');
  if (nav) nav.classList.add('active');
  if (name === 'approvals') loadApprovals();
  if (name === 'audit') loadAuditLog();
  if (name === 'overview') loadLifecycleStats();
}

// ── TOAST ─────────────────────────────────────────────────────────────────────
function showToast(msg, type='success') {
  const t = document.getElementById('toastEl');
  t.textContent = msg; t.className = 'toast ' + type + ' show';
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove('show'), 3500);
}

// ── ACTION HELPER ─────────────────────────────────────────────────────────────
async function doAction(url, method='POST') {
  try {
    const r = await fetch(url, {method});
    const d = await r.json();
    showToast(d.message || (d.success ? 'Done' : 'Failed'), d.success ? 'success' : 'error');
    if (d.success) setTimeout(fetchAndRender, 600);
    return d;
  } catch(e) {
    showToast('Network error', 'error');
    return {success: false};
  }
}

// ── CHARTS INIT ───────────────────────────────────────────────────────────────
function initCharts() {
  Chart.defaults.color = '#7d8590';
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
  Chart.defaults.font.size = 10;

  bedDonut = new Chart(document.getElementById('bedDonut'), {
    type: 'doughnut',
    data: { labels: ['Occupied','Vacant','Dirty'], datasets: [{ data: [0,0,0], backgroundColor: ['#EF4444','#10B981','#F59E0B'], borderWidth: 0, hoverOffset: 4 }] },
    options: { responsive:true, maintainAspectRatio:true, cutout:'65%', plugins: { legend: { position:'bottom', labels:{padding:6,boxWidth:8} } } }
  });

  wardBar = new Chart(document.getElementById('wardBar'), {
    type: 'bar',
    data: { labels: [], datasets: [{ label:'Occupied', data:[], backgroundColor:'#6366F1', borderRadius:3, borderSkipped:false }] },
    options: {
      indexAxis:'y', responsive:true, maintainAspectRatio:false,
      plugins: { legend:{display:false} },
      scales: { x:{grid:{color:'rgba(255,255,255,0.04)'}}, y:{grid:{display:false}} }
    }
  });

  dischDonut = new Chart(document.getElementById('dischDonut'), {
    type: 'doughnut',
    data: { labels: ['Blocked','Cleared'], datasets: [{ data:[0,0], backgroundColor:['#EF4444','#10B981'], borderWidth:0, hoverOffset:4 }] },
    options: { responsive:true, maintainAspectRatio:true, cutout:'65%', plugins: { legend:{ position:'bottom', labels:{padding:6,boxWidth:8} } } }
  });

  claimChart = new Chart(document.getElementById('claimStatusChart'), {
    type: 'doughnut',
    data: { labels:[], datasets:[{data:[], backgroundColor:['#EF4444','#10B981','#F59E0B','#388bfd'], borderWidth:0}] },
    options: { responsive:true, maintainAspectRatio:true, cutout:'60%', plugins:{legend:{position:'bottom',labels:{padding:6,boxWidth:8}}} }
  });

  tpaChart = new Chart(document.getElementById('tpaChart'), {
    type: 'bar',
    data: { labels:[], datasets:[{label:'Amount',data:[],backgroundColor:'#a371f7',borderRadius:3}] },
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins:{legend:{display:false}},
      scales:{ x:{grid:{display:false}}, y:{grid:{color:'rgba(255,255,255,0.04)'}, ticks:{callback:v=>'₹'+Number(v/1000).toFixed(0)+'K'}} }
    }
  });
}

function updateCharts(d) {
  const bc = d.bed_census, dp = d.discharge_pipeline, rv = d.revenue;
  if (bedDonut) { bedDonut.data.datasets[0].data = [bc.occupied, bc.vacant, bc.dirty]; bedDonut.update(); }
  if (wardBar) {
    const top8 = [...(bc.by_ward||[])].sort((a,b)=>b.occupied-a.occupied).slice(0,8);
    wardBar.data.labels = top8.map(w=>w.ward);
    wardBar.data.datasets[0].data = top8.map(w=>w.occupied);
    wardBar.update();
  }
  if (dischDonut) { dischDonut.data.datasets[0].data = [dp.blocked, dp.cleared]; dischDonut.update(); }
  if (claimChart && rv.status_labels) { claimChart.data.labels = rv.status_labels; claimChart.data.datasets[0].data = rv.status_values; claimChart.update(); }
  if (tpaChart && rv.tpa_labels) { tpaChart.data.labels = rv.tpa_labels; tpaChart.data.datasets[0].data = rv.tpa_values; tpaChart.update(); }
}

// ── OVERVIEW SECTION ──────────────────────────────────────────────────────────
const STEP_NAMES = ['Clinical','Pharmacy','Billing','Nursing'];
const STEP_EXTS  = ['Ext. 1012','Ext. 1023','Ext. 1028','Ext. 1031'];

function buildDisSteps(r) {
  const vals = [r.clinical, r.pharmacy, r.billing, r.nursing];
  const step = vals.indexOf(false) + 1 || 5;
  return vals.map((v, i) => {
    const s = i + 1;
    const cls = v ? 'done' : s === step ? 'active' : '';
    const icon = v ? '✓' : s;
    const line = i < 3 ? `<div class="step-line ${v ? 'done' : ''}"></div>` : '';
    return `<div class="dis-step ${cls}"><div class="step-circle">${icon}</div><div class="step-lbl">${STEP_NAMES[i]}</div></div>${line}`;
  }).join('');
}

function renderDisCard(r, showAdvance=true) {
  const vals = [r.clinical, r.pharmacy, r.billing, r.nursing];
  const step = vals.indexOf(false);
  const stepName = step >= 0 ? STEP_NAMES[step] : 'Complete';
  const stepExt  = step >= 0 ? STEP_EXTS[step]  : '—';
  const advBtn = showAdvance && r.is_blocked
    ? `<button class="btn btn-green btn-sm" onclick="event.stopPropagation();doAction('/api/v1/ops/discharge/${r.discharge_id}/advance')">✓ Mark ${stepName} Done</button>`
    : '';
  return `<div class="dis-card" style="cursor:pointer;" onclick="showDetail('discharge','${r.discharge_id}')">
    <div class="dis-card-top">
      <div><div class="dis-name">${r.patient_name}</div><div class="dis-meta">${r.discharge_id} · ${r.uhid} · ${r.ward || r.bed_id}</div></div>
      <div style="display:flex;gap:6px;flex-shrink:0;align-items:flex-start;" onclick="event.stopPropagation()">
        ${advBtn}
        <button class="btn btn-muted btn-sm" onclick="showToast('Notifying ${stepName} team — ${stepExt}','info')">📞 Notify</button>
        <button class="btn btn-muted btn-sm" onclick="showDetail('discharge','${r.discharge_id}')">🔍 Detail</button>
      </div>
    </div>
    <div class="dis-steps">${buildDisSteps(r)}</div>
    ${r.is_blocked ? `<div class="dis-blocker">${r.blocker_reason || 'Blocked at step: ' + stepName + ' — ' + stepExt}</div>` : '<div style="font-size:10px;color:var(--green)">✓ Discharge cleared</div>'}
  </div>`;
}

function renderBlockedCards(dp, containerId) {
  const el = document.getElementById(containerId);
  const blocked = (dp.rows||[]).filter(r=>r.is_blocked);
  if (!el) return;
  document.querySelectorAll('[id$="BlockBadge"],[id$="block"]').forEach(b => { if (b) b.textContent = dp.blocked; });
  if (!blocked.length) { el.innerHTML = '<div class="empty" style="color:var(--green)">✓ No blocked discharges</div>'; return; }
  el.innerHTML = blocked.map(r => renderDisCard(r, true)).join('');
}

function renderAlertCards(pa, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const rows = (pa.rows||[]).filter(r => r.readback_status !== 'Acknowledged').slice(0,30);
  if (!rows.length) { el.innerHTML = '<div class="empty" style="color:var(--green)">✓ All readbacks acknowledged</div>'; return; }
  el.innerHTML = rows.map((r, idx) => {
    const pct = r.sla_limit_min > 0 ? Math.min(100, Math.round(r.elapsed_min / r.sla_limit_min * 100)) : 100;
    const barCls = r.sla_breached ? 'crit' : pct > 70 ? 'warn' : '';
    const docBadge = r.doctor_contacted ? pill('Doctor Contacted','green') : pill('NOT CONTACTED','red');
    return `<div class="alert-card ${r.sla_breached?'breached':''}" id="ac-${containerId}-${idx}" style="cursor:pointer;" onclick="showDetail('alert','${r.alert_id}')">
      <div class="alert-top">
        <div><div class="alert-patient">${r.patient_name}</div><div class="alert-uhid">${r.alert_id}</div></div>
        <div style="display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end;">
          ${r.sla_breached ? pill('SLA BREACHED','red') : pill('Within SLA','green')}
          ${docBadge}
        </div>
      </div>
      <div class="alert-value">${r.parameter} = ${r.value}</div>
      <div class="sla-row">
        <div class="sla-track"><div class="sla-fill ${barCls}" style="width:${pct}%"></div></div>
        <div class="sla-lbl">${r.elapsed_min}m / ${r.sla_limit_min}m</div>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;" onclick="event.stopPropagation()">
        ${pill(r.readback_status || 'Pending', r.readback_status === 'Acknowledged' ? 'green' : 'amber')}
        <button class="btn btn-green btn-sm" onclick="doAction('/api/v1/ops/alert/${r.alert_id}/acknowledge')">✓ Confirm Readback</button>
      </div>
    </div>`;
  }).join('');
}

function renderWardRows(bc, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = (bc.by_ward||[]).map(w => {
    const cls = w.occupancy_pct >= 90 ? 'crit' : w.occupancy_pct >= 75 ? 'high' : '';
    return `<div class="ward-row">
      <div class="ward-name">${w.ward}</div>
      <div class="ward-track"><div class="ward-fill ${cls}" style="width:${w.occupancy_pct}%"></div></div>
      <div class="ward-pct">${w.occupancy_pct}%</div>
      <div class="ward-cnt">${w.occupied}/${w.total}</div>
    </div>`;
  }).join('');
}

function renderClaimCardsSmall(rv, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const rows = (rv.claim_rows||[]).slice(0,20);
  if (!rows.length) { el.innerHTML = '<div class="empty">No claims</div>'; return; }
  el.innerHTML = rows.map(r => {
    const sl = (r.status||'').toLowerCase();
    const cls = r.is_rejected ? 'rejected' : sl.includes('approved') ? 'approved' : 'pending';
    const pc  = r.is_rejected ? 'red' : sl.includes('approved') ? 'green' : 'amber';
    return `<div style="background:var(--surface2);border:1px solid var(--border2);border-radius:5px;padding:8px 10px;display:flex;justify-content:space-between;align-items:center;gap:8px;border-left:3px solid var(--${r.is_rejected?'red':sl.includes('approved')?'green':'amber'});">
      <div><div style="font-size:11px;font-weight:600;">${r.patient_name}</div><div class="mono">${r.claim_id} · ${r.tpa}</div></div>
      <div style="text-align:right;flex-shrink:0;"><div style="font-size:11px;font-weight:700;font-family:var(--mono);">${INR(r.amount)}</div>${pill(r.status||'—',pc)}</div>
    </div>`;
  }).join('');
}

// ── OVERVIEW RENDER ───────────────────────────────────────────────────────────
function renderOverview(d) {
  const bc = d.bed_census, dp = d.discharge_pipeline, pa = d.panic_alerts, rv = d.revenue, pt = d.patients;
  document.getElementById('kpiPatients').textContent = pt.admitted || pt.total;
  document.getElementById('kpiOcc').textContent = bc.occupancy_pct + '%';
  document.getElementById('kpiOccSub').textContent = bc.occupied + ' of ' + bc.total + ' beds';
  document.getElementById('kpiBlock').textContent = dp.blocked;
  document.getElementById('kpiSLA').textContent = pa.sla_breached;
  document.getElementById('kpiDirty').textContent = bc.dirty;
  document.getElementById('kpiRev').textContent = INR(rv.total_at_risk);
  document.getElementById('ovRevBadge').textContent = INR(rv.total_at_risk) + ' at risk';
  document.getElementById('ovBedSub').textContent = bc.occupied + '/' + bc.total + ' occupied';
  document.getElementById('sb-block').textContent = dp.blocked;
  document.getElementById('sb-alert').textContent = pa.sla_breached;
  document.getElementById('sb-rev').textContent = INR(rv.total_at_risk);

  const setCard = (id, cls) => { const el = document.getElementById(id); if (el) el.className = 'kpi-card ' + cls; };
  setCard('kpiBlockCard', dp.blocked > 0 ? 'red' : 'green');
  setCard('kpiSLACard',   pa.sla_breached > 0 ? 'red' : 'green');
  setCard('kpiDirtyCard', bc.dirty > 0 ? 'amber' : '');
  setCard('kpiOccCard',   bc.occupancy_pct >= 90 ? 'red' : bc.occupancy_pct >= 75 ? 'amber' : '');

  renderBlockedCards(dp, 'ovBlockedCards');
  document.getElementById('ovBlockBadge').textContent = dp.blocked;
  renderAlertCards(pa, 'ovAlertCards');
  document.getElementById('ovSLABadge').textContent = pa.sla_breached + ' breached';
  renderWardRows(bc, 'ovWardRows');
  renderClaimCardsSmall(rv, 'ovClaimCards');
}

// ── BED OPERATIONS ────────────────────────────────────────────────────────────
function renderBedSection(d) {
  const bc = d.bed_census;
  document.getElementById('bedKpiOcc').textContent = bc.occupied;
  document.getElementById('bedKpiVac').textContent = bc.vacant;
  document.getElementById('bedKpiDirty').textContent = bc.dirty;
  document.getElementById('bedKpiPct').textContent = bc.occupancy_pct + '%';
  _allBedRows = bc.bed_rows || [];

  // Populate ward filter
  const wards = [...new Set(_allBedRows.map(b=>b.ward))].sort();
  const sel = document.getElementById('bedWardFilter');
  const cur = sel.value;
  sel.innerHTML = '<option value="">All Wards</option>' + wards.map(w=>`<option value="${w}" ${w===cur?'selected':''}>${w}</option>`).join('');

  filterBeds();
}

function filterBeds() {
  const ward = document.getElementById('bedWardFilter').value;
  const status = document.getElementById('bedStatusFilter').value;
  const q = (document.getElementById('bedSearch').value || '').toLowerCase();
  const rows = _allBedRows.filter(b =>
    (!ward   || b.ward === ward) &&
    (!status || b.status === status) &&
    (!q      || b.bed_id.toLowerCase().includes(q))
  );
  const grid = document.getElementById('bedGrid');
  if (!rows.length) { grid.innerHTML = '<div class="empty">No beds match filters</div>'; return; }
  grid.innerHTML = rows.map(b => {
    const dot = b.status === 'vacant' ? '🟢' : b.status === 'dirty' ? '🟡' : '🔴';
    const patInfo = b.patient_name ? `<div class="bed-pat">${b.patient_name}</div><div class="bed-pat" style="font-family:var(--mono);font-size:9px;">${b.patient_uhid}</div>` : '<div class="bed-pat" style="color:var(--muted);">—</div>';
    const btns = b.status === 'vacant'
      ? `<button class="btn btn-blue btn-sm" onclick="toggleAssignForm('${b.bed_id}')">Assign</button>`
      : b.status === 'dirty'
      ? `<button class="btn btn-green btn-sm" onclick="doAction('/api/v1/ops/bed/${b.bed_id}/mark-clean')">Clean ✓</button>`
      : `<button class="btn btn-muted btn-sm" onclick="showToast('Transfer workflow — contact Bed Management','info')">Transfer</button>`;
    return `<div class="bed-card ${b.status}">
      <div class="bed-id">${b.bed_id} <span>${dot}</span></div>
      <div class="bed-ward-lbl">${b.ward}</div>
      ${patInfo}
      <div class="bed-btns">${btns}</div>
      <div class="assign-form" id="af-${b.bed_id}">
        <input type="text" placeholder="UHID" id="ai-${b.bed_id}">
        <button class="btn btn-green btn-sm" onclick="submitAssign('${b.bed_id}')">OK</button>
      </div>
    </div>`;
  }).join('');
}

function toggleAssignForm(bedId) {
  const el = document.getElementById('af-' + bedId);
  if (el) { el.classList.toggle('open'); el.querySelector('input').focus(); }
}

async function submitAssign(bedId) {
  const uhid = document.getElementById('ai-' + bedId).value.trim();
  if (!uhid) { showToast('Enter a UHID','error'); return; }
  await doAction(`/api/v1/ops/bed/${bedId}/assign?uhid=${encodeURIComponent(uhid)}`);
}

// ── DISCHARGE SECTION ─────────────────────────────────────────────────────────
function renderDischargeSection(d) {
  const dp = d.discharge_pipeline;
  document.getElementById('disKpiTotal').textContent   = dp.total;
  document.getElementById('disKpiBlocked').textContent = dp.blocked;
  document.getElementById('disKpiCleared').textContent = dp.cleared;
  document.getElementById('disKpiGate').textContent    = dp.gate_pass_issued;
  document.getElementById('disBlockBadge').textContent = dp.blocked;
  document.getElementById('disAllBadge').textContent   = dp.total;

  // Blocked cards
  renderBlockedCards(dp, 'disBlockedCards');

  // All table
  const tbody = document.getElementById('disAllTable');
  tbody.innerHTML = (dp.rows||[]).map(r => `<tr class="${r.is_blocked?'row-red':''}">
    <td style="max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${r.patient_name}</td>
    <td class="mono">${r.uhid}</td>
    <td class="mono">${r.bed_id}</td>
    <td class="dimmed">${r.ward}</td>
    <td style="text-align:center">${chk(r.clinical)}</td>
    <td style="text-align:center">${chk(r.pharmacy)}</td>
    <td style="text-align:center">${chk(r.billing)}</td>
    <td style="text-align:center">${chk(r.nursing)}</td>
    <td style="text-align:center">${r.gate_pass ? pill('ISSUED','green') : pill('PENDING','muted')}</td>
    <td style="text-align:center">${r.is_blocked ? pill('BLOCKED','red') : pill('CLEAR','green')}</td>
  </tr>`).join('');
}

// ── ALERTS SECTION ────────────────────────────────────────────────────────────
function renderAlertsSection(d) {
  const pa = d.panic_alerts;
  document.getElementById('altKpiTotal').textContent   = pa.total;
  document.getElementById('altKpiBreached').textContent= pa.sla_breached;
  document.getElementById('altKpiOK').textContent      = pa.total - pa.sla_breached;
  document.getElementById('altKpiAck').textContent     = pa.acknowledged;
  document.getElementById('altBadge').textContent      = pa.sla_breached + ' breached';
  renderAlertCards(pa, 'altCards');
}

// ── BILLING SECTION ───────────────────────────────────────────────────────────
function renderBillingSection(d) {
  const rv = d.revenue;
  _allClaimRows = rv.claim_rows || [];

  const total    = _allClaimRows.reduce((s,c) => s + (c.amount||0), 0);
  const approved = _allClaimRows.filter(c=>(c.status||'').toLowerCase().includes('approved')).reduce((s,c)=>s+(c.amount||0),0);
  const rejected = _allClaimRows.filter(c=>c.is_rejected).reduce((s,c)=>s+(c.amount||0),0);
  const rejCount = _allClaimRows.filter(c=>c.is_rejected).length;
  const rejRate  = _allClaimRows.length > 0 ? Math.round(rejCount / _allClaimRows.length * 100) : 0;

  document.getElementById('claimKPIs').innerHTML = `
    <div class="sec-kpi"><div class="sec-kpi-lbl">Total Claimed</div><div class="sec-kpi-val" style="font-size:15px;">${INR(total)}</div></div>
    <div class="sec-kpi"><div class="sec-kpi-lbl">Approved</div><div class="sec-kpi-val" style="color:var(--green);font-size:15px;">${INR(approved)}</div></div>
    <div class="sec-kpi"><div class="sec-kpi-lbl">Rejected</div><div class="sec-kpi-val" style="color:var(--red);font-size:15px;">${INR(rejected)}</div></div>
    <div class="sec-kpi"><div class="sec-kpi-lbl">Rejection Rate</div><div class="sec-kpi-val" style="color:${rejRate>20?'var(--red)':'var(--amber)'};">${rejRate}%</div></div>`;

  filterClaims(_claimFilter);
}

function filterClaims(filter, tabEl) {
  _claimFilter = filter;
  document.querySelectorAll('#claimTabBar .tab').forEach(t => t.classList.remove('active'));
  if (tabEl) tabEl.classList.add('active');
  const rows = _allClaimRows.filter(r => {
    const sl = (r.status||'').toLowerCase();
    if (filter === 'pending')  return sl === 'pending';
    if (filter === 'rejected') return r.is_rejected;
    if (filter === 'approved') return sl.includes('approved');
    return true;
  });
  const tbody = document.getElementById('claimsTable');
  if (!rows.length) { tbody.innerHTML = '<tr><td colspan="7" class="empty">No claims</td></tr>'; return; }
  tbody.innerHTML = rows.map(r => {
    const sl = (r.status||'').toLowerCase();
    const pc = r.is_rejected ? 'red' : sl.includes('approved') ? 'green' : 'amber';
    return `<tr class="${r.is_rejected?'row-red':''}" style="cursor:pointer;" onclick="showDetail('claim','${r.claim_id}')">
      <td class="mono">${r.claim_id}</td>
      <td>${r.patient_name}</td>
      <td class="dimmed">${r.tpa}</td>
      <td class="mono">${INR(r.amount)}</td>
      <td>${pill(r.status||'—',pc)}</td>
      <td class="dimmed" style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${r.rejection_reason||'—'}</td>
      <td onclick="event.stopPropagation()">
        <select class="btn btn-muted btn-sm" onchange="updateClaim('${r.claim_id}',this.value,this)" style="padding:3px 6px;">
          <option value="">Actions…</option>
          <option value="Approved">Mark Approved</option>
          <option value="In Review">Mark In Review</option>
          <option value="Rejected">Mark Rejected</option>
          <option value="Pending">Mark Pending</option>
        </select>
      </td>
    </tr>`;
  }).join('');
}

async function updateClaim(claimId, status, el) {
  if (!status) return;
  el.value = '';
  await doAction(`/api/v1/ops/claim/${encodeURIComponent(claimId)}/update-status?status=${encodeURIComponent(status)}`);
}

// ── REVENUE SECTION ───────────────────────────────────────────────────────────
function renderRevenueSection(d) {
  const rv = d.revenue;
  document.getElementById('revBigNum').textContent = INR(rv.total_at_risk);
  const atRisk = (rv.claim_rows||[]).filter(r => r.is_rejected || (r.status||'').toLowerCase() === 'pending');
  const tbody = document.getElementById('revRiskTable');
  if (!atRisk.length) { tbody.innerHTML = '<tr><td colspan="7" class="empty" style="color:var(--green)">No at-risk claims</td></tr>'; return; }
  tbody.innerHTML = atRisk.map(r => `<tr class="${r.is_rejected?'row-red':'row-amber'}" style="cursor:pointer;" onclick="showDetail('claim','${r.claim_id}')">
    <td class="mono">${r.claim_id}</td>
    <td>${r.patient_name}</td>
    <td class="dimmed">${r.tpa}</td>
    <td class="mono">${INR(r.amount)}</td>
    <td>${pill(r.status||'—', r.is_rejected?'red':'amber')}</td>
    <td class="dimmed" style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${r.rejection_reason||'Revenue exposure'}</td>
    <td onclick="event.stopPropagation()"><button class="btn btn-muted btn-sm" onclick="showToast('Escalating claim ${r.claim_id} to TPA desk','info')">Follow Up</button></td>
  </tr>`).join('');
}

// ── PATIENT SECTION ───────────────────────────────────────────────────────────
function renderPatientSection(d) {
  _allPatRows = d.patients.rows || [];
  filterPatients();
}

function filterPatients() {
  const q = (document.getElementById('patSearch').value || '').toLowerCase();
  const rows = q
    ? _allPatRows.filter(p =>
        p.uhid.toLowerCase().includes(q) ||
        (p.name||'').toLowerCase().includes(q) ||
        (p.ward||'').toLowerCase().includes(q))
    : _allPatRows.slice(0, 60);
  const el = document.getElementById('patCards');
  if (!rows.length) { el.innerHTML = '<div class="empty">No patients found</div>'; return; }
  el.innerHTML = rows.map(p => {
    const sc = (p.status||'').toLowerCase().includes('discharg') ? 'muted' : 'green';
    return `<div class="patient-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div><div class="pat-name">${p.name}</div><div class="pat-uhid">${p.uhid}</div></div>
        ${pill(p.status||'active', sc)}
      </div>
      <div class="pat-row">
        <span>🛏️ ${p.bed_id}</span>
        <span>📍 ${p.ward}</span>
        ${p.gender ? `<span>👤 ${p.gender}</span>` : ''}
        ${p.age ? `<span>Age: ${p.age}</span>` : ''}
      </div>
      ${p.diagnosis ? `<div style="font-size:10px;color:var(--muted);">Dx: ${p.diagnosis}</div>` : ''}
      <div class="pat-actions">
        <button class="btn btn-blue btn-sm" onclick="showDetail('patient','${p.uhid}')">View 360°</button>
        <button class="btn btn-muted btn-sm" onclick="showSection('discharge');showToast('Checking discharge status for ${p.uhid}','info')">Discharge</button>
        <button class="btn btn-red btn-sm" onclick="showToast('${p.name} flagged as urgent — notifying charge nurse','info')">Flag Urgent</button>
      </div>
    </div>`;
  }).join('');
}

function openPatModal(p) {
  document.getElementById('modalTitle').textContent = p.name + ' — ' + p.uhid;
  document.getElementById('modalBody').innerHTML = `
    <div class="modal-section">
      <div class="modal-section-title">Demographics</div>
      <div class="modal-grid">
        <div class="modal-field"><label>UHID</label><span>${p.uhid}</span></div>
        <div class="modal-field"><label>Name</label><span>${p.name}</span></div>
        <div class="modal-field"><label>Status</label><span>${p.status||'—'}</span></div>
        <div class="modal-field"><label>Gender</label><span>${p.gender||'—'}</span></div>
        <div class="modal-field"><label>Age</label><span>${p.age||'—'}</span></div>
        <div class="modal-field"><label>Ward / Bed</label><span>${p.ward} / ${p.bed_id}</span></div>
      </div>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">Admission</div>
      <div class="modal-grid">
        <div class="modal-field"><label>Admission Date</label><span>${p.admission_date||'—'}</span></div>
        <div class="modal-field"><label>Doctor ID</label><span>${p.doctor_id||'—'}</span></div>
        <div class="modal-field"><label>Diagnosis</label><span>${p.diagnosis||'—'}</span></div>
      </div>
    </div>`;
  document.getElementById('patModal').classList.add('open');
}

function closeModal() { document.getElementById('patModal').classList.remove('open'); }

// ── ASK AGENT ─────────────────────────────────────────────────────────────────
function askAgent(query) {
  closeModal();
  showSection('agent');
  const inp = document.getElementById('chatInput');
  inp.value = query;
  inp.focus();
  // Auto-submit after brief delay so the tab transition is visible
  setTimeout(sendChat, 200);
}

function _askBtn(query) {
  const safe = query.replace(/'/g, "\\'");
  return `<button class="btn btn-blue btn-sm" style="margin-left:auto;" onclick="askAgent('${safe}')">🤖 Ask Agent</button>`;
}

// ── UNIVERSAL DETAIL MODAL ────────────────────────────────────────────────────
async function showDetail(type, id) {
  const modal = document.getElementById('patModal');
  const title = document.getElementById('modalTitle');
  const body  = document.getElementById('modalBody');
  title.textContent = 'Loading…';
  body.innerHTML = '<div style="text-align:center;padding:30px;color:var(--muted)">Fetching details…</div>';
  modal.classList.add('open');
  try {
    const d = await fetch(`/api/v1/ops/detail/${type}/${encodeURIComponent(id)}`).then(r=>r.json());
    if (d.error) { body.innerHTML = `<div style="color:var(--red);padding:16px">${d.error}</div>`; return; }
    if (type === 'claim')     renderClaimDetail(d, title, body);
    else if (type === 'discharge') renderDischargeDetail(d, title, body);
    else if (type === 'alert')     renderAlertDetail(d, title, body);
    else if (type === 'bed')       renderBedDetail(d, title, body);
    else if (type === 'patient')   renderPatientDetail(d, title, body);
  } catch(e) {
    body.innerHTML = `<div style="color:var(--red);padding:16px">Error: ${e.message}</div>`;
  }
}

function _row(label, val, mono) {
  return `<div class="modal-field"><label>${label}</label><span class="${mono?'mono':''}">${val||'—'}</span></div>`;
}
function _clr(ok) { return ok
  ? '<span style="color:var(--green);font-weight:700">✓ Cleared</span>'
  : '<span style="color:var(--red);font-weight:700">✗ Pending</span>'; }

function renderClaimDetail(d, title, body) {
  const p = d.patient || {};
  const a = d.admission || {};
  const pc = (d.status||'').toLowerCase().includes('reject') ? 'red'
           : (d.status||'').toLowerCase().includes('approv') ? 'green' : 'amber';
  title.innerHTML = `Claim Detail &nbsp; ${pill(d.status||'—', pc)}`;
  body.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">
      ${_row('Claim ID', d.claim_id, true)}
      ${_row('Admission ID', d.admission_id, true)}
      ${_row('UHID', d.uhid, true)}
      ${_row('Patient', p.name || d.uhid)}
      ${_row('Age / Gender', p.age ? `${p.age} yrs / ${p.gender}` : '—')}
      ${_row('Contact', p.contact)}
      ${_row('Current Bed', p.bed)}
      ${_row('Status', p.status)}
    </div>
    <hr style="border-color:var(--border2);margin:12px 0">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">
      ${_row('Insurer', d.insurer)}
      ${_row('TPA', d.tpa)}
      ${_row('Policy Number', d.policy_number, true)}
      ${_row('Claim Amount', INR(d.claim_amount), true)}
      ${_row('Approved Amount', INR(d.approved_amount), true)}
      ${_row('Claim Status', d.status)}
    </div>
    ${d.rejection_reason ? `<hr style="border-color:var(--border2);margin:12px 0">
    <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.25);border-radius:6px;padding:12px;">
      <div style="font-weight:700;color:var(--red);margin-bottom:6px;">⚠ Rejection Details</div>
      ${_row('Rejection Reason', d.rejection_reason)}
      ${_row('Rejection Clause', d.rejection_clause)}
      ${_row('Dispute Appeal Required', d.requires_dispute_appeal ? 'Yes' : 'No')}
    </div>` : ''}
    ${a.doctor ? `<hr style="border-color:var(--border2);margin:12px 0">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">
      <div style="grid-column:1/-1;font-weight:700;color:var(--muted);font-size:10px;text-transform:uppercase;margin-bottom:4px;">Admission</div>
      ${_row('Doctor', a.doctor)}
      ${_row('Diagnosis', a.diagnosis)}
      ${_row('Admission Date', a.date)}
      ${_row('Department', a.dept)}
    </div>` : ''}
    <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      <button class="btn btn-green btn-sm" onclick="doAction('/api/v1/ops/claim/${encodeURIComponent(d.claim_id)}/update-status?status=Approved')">Mark Approved</button>
      <button class="btn btn-amber btn-sm" onclick="doAction('/api/v1/ops/claim/${encodeURIComponent(d.claim_id)}/update-status?status=In Review')">Mark In Review</button>
      <button class="btn btn-red btn-sm"   onclick="doAction('/api/v1/ops/claim/${encodeURIComponent(d.claim_id)}/update-status?status=Rejected')">Mark Rejected</button>
      ${_askBtn('Tell me about claim ' + d.claim_id + ' for patient ' + (d.patient && d.patient.name ? d.patient.name : d.uhid) + '. Why is it ' + d.status + '?')}
    </div>`;
}

function renderDischargeDetail(d, title, body) {
  const p = d.patient || {};
  const pc = d.is_blocked ? 'red' : 'green';
  title.innerHTML = `Discharge Detail &nbsp; ${pill(d.status||'—', pc)}`;
  body.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">
      ${_row('Discharge ID', d.discharge_id, true)}
      ${_row('Admission ID', d.admission_id, true)}
      ${_row('UHID', d.uhid, true)}
      ${_row('Patient', p.name || d.uhid)}
      ${_row('Bed', d.bed_id)}
      ${_row('Discharge Type', d.discharge_type)}
      ${_row('Final Diagnosis', d.final_diagnosis)}
      ${_row('Gate Pass Issued', d.gate_pass_issued ? 'Yes ✓' : 'No ✗')}
    </div>
    <hr style="border-color:var(--border2);margin:12px 0">
    <div style="font-weight:700;color:var(--muted);font-size:10px;text-transform:uppercase;margin-bottom:8px;">Clearance Checklist</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
      <div style="background:var(--surface2);border-radius:6px;padding:10px;">${_clr(d.clearance_clinical)}<div style="margin-top:4px;font-size:11px;">Clinical Sign-off</div></div>
      <div style="background:var(--surface2);border-radius:6px;padding:10px;">${_clr(d.clearance_pharmacy)}<div style="margin-top:4px;font-size:11px;">Pharmacy Return</div></div>
      <div style="background:var(--surface2);border-radius:6px;padding:10px;">${_clr(d.clearance_billing)}<div style="margin-top:4px;font-size:11px;">Billing Settlement</div></div>
      <div style="background:var(--surface2);border-radius:6px;padding:10px;">${_clr(d.clearance_nursing)}<div style="margin-top:4px;font-size:11px;">Nursing Clearance</div></div>
    </div>
    ${d.is_blocked ? `<div style="margin-top:12px;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.25);border-radius:6px;padding:12px;">
      <div style="font-weight:700;color:var(--red);margin-bottom:4px;">Blocker</div>
      <div>${d.blocker_reason||'—'}</div>
      <div style="margin-top:4px;font-size:11px;color:var(--muted)">Resolution team: Ext. ${d.resolution_team_extension||'—'}</div>
    </div>` : ''}
    <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap;">
      <button class="btn btn-green btn-sm" onclick="doAction('/api/v1/ops/discharge/${encodeURIComponent(d.discharge_id)}/advance')">✓ Advance to Next Step</button>
      ${_askBtn('Why is the discharge of ' + (d.patient && d.patient.name ? d.patient.name : d.uhid) + ' blocked? What needs to be done next?')}
    </div>`;
}

function renderAlertDetail(d, title, body) {
  const p = d.patient || {};
  const pct = Math.min(100, Math.round((d.elapsed_minutes / (d.sla_minutes||1)) * 100));
  const barColor = pct >= 100 ? 'var(--red)' : pct >= 80 ? 'var(--amber)' : 'var(--green)';
  title.innerHTML = `Lab Critical Alert &nbsp; ${pill(d.readback_status||'—', d.is_sla_breached?'red':'amber')}`;
  body.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">
      ${_row('Alert ID', d.alert_id, true)}
      ${_row('Order ID', d.order_id, true)}
      ${_row('UHID', d.uhid, true)}
      ${_row('Patient', d.patient_name || p.name)}
    </div>
    <div style="margin:12px 0;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);border-radius:8px;padding:14px;text-align:center;">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px;">${d.parameter_name}</div>
      <div style="font-size:28px;font-weight:900;color:var(--red);font-family:var(--mono)">${d.critical_value}</div>
      <div style="font-size:10px;color:var(--muted);margin-top:2px;">Critical Value</div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">
      ${_row('Alert Time', d.alert_time)}
      ${_row('Ack Time', d.ack_time||'Not yet acknowledged')}
      ${_row('Doctor Contacted', d.doctor_contacted||'—')}
      ${_row('Doctor Phone', d.doctor_phone)}
      ${_row('Readback Status', d.readback_status)}
    </div>
    <div style="margin:12px 0;">
      <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-bottom:4px;">
        <span>SLA Elapsed: ${Math.round(d.elapsed_minutes)} min</span>
        <span>Limit: ${Math.round(d.sla_minutes)} min</span>
      </div>
      <div style="height:8px;background:var(--surface2);border-radius:4px;overflow:hidden;">
        <div style="height:100%;width:${pct}%;background:${barColor};transition:width 0.5s;"></div>
      </div>
      <div style="text-align:right;font-size:10px;margin-top:2px;color:${barColor};">${d.is_sla_breached ? '⚠ SLA BREACHED' : pct+'% used'}</div>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <button class="btn btn-green btn-sm" onclick="doAction('/api/v1/ops/alert/${encodeURIComponent(d.alert_id)}/acknowledge')">✓ Confirm Readback</button>
      ${_askBtn('What is the SLA status for alert ' + d.alert_id + '? Patient ' + d.patient_name + ' has a critical ' + d.parameter_name + ' of ' + d.critical_value + '.')}
    </div>`;
}

function renderBedDetail(d, title, body) {
  const p = d.patient || {};
  const sc = d.status === 'Vacant' ? 'green' : d.status === 'Dirty' ? 'amber' : 'red';
  title.innerHTML = `Bed Detail &nbsp; ${pill(d.status||'—', sc)}`;
  body.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">
      ${_row('Bed ID', d.bed_id, true)}
      ${_row('Ward', d.ward)}
      ${_row('Department', d.department_id)}
      ${_row('Bed Type', d.bed_type)}
      ${_row('Status', d.status)}
      ${_row('Last Turnaround', d.last_turnaround)}
    </div>
    ${d.current_patient_uhid !== '—' ? `<hr style="border-color:var(--border2);margin:12px 0">
    <div style="font-weight:700;color:var(--muted);font-size:10px;text-transform:uppercase;margin-bottom:8px;">Current Patient</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">
      ${_row('UHID', d.current_patient_uhid, true)}
      ${_row('Name', p.name)}
      ${_row('Age / Gender', p.age ? `${p.age} yrs / ${p.gender}` : '—')}
      ${_row('Contact', p.contact)}
    </div>
    <div style="margin-top:10px;display:flex;gap:8px;">
      <button class="btn btn-muted btn-sm" onclick="closeModal();showDetail('patient','${encodeURIComponent(d.current_patient_uhid)}')">View Patient 360°</button>
    </div>` : `
    <div style="margin-top:14px;">
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px;">Assign patient to this bed:</div>
      <div style="display:flex;gap:8px;">
        <input id="assignUhid_${d.bed_id}" placeholder="UHID (SMCH-XXXXXX)" class="input" style="flex:1">
        <button class="btn btn-green btn-sm" onclick="assignBedFromModal('${d.bed_id}')">Assign</button>
      </div>
    </div>`}
    <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;">
      ${d.status==='Dirty' ? `<button class="btn btn-amber btn-sm" onclick="doAction('/api/v1/ops/bed/${encodeURIComponent(d.bed_id)}/mark-clean')">Mark as Clean</button>` : ''}
      ${_askBtn('What is the current status of bed ' + d.bed_id + ' in ' + d.ward + '?')}
    </div>`;
}

function renderPatientDetail(d, title, body) {
  const a = d.admission || {};
  title.innerHTML = `Patient 360° &mdash; ${d.name}`;
  const disHtml = d.discharges.length ? d.discharges.map(x=>
    `<div style="display:flex;gap:8px;align-items:center;padding:4px 0;border-bottom:1px solid var(--border2);">
      <span class="mono" style="flex:1">${x.id}</span>
      ${pill(x.status||'—', x.is_blocked?'red':'green')}
      <span style="font-size:10px;color:var(--muted);flex:2">${x.blocker||''}</span>
      <button class="btn btn-muted btn-sm" onclick="closeModal();showDetail('discharge','${x.id}')">View</button>
    </div>`).join('') : '<div class="dimmed" style="font-size:11px">No discharges on record</div>';
  const clHtml = d.claims.length ? d.claims.map(x=>
    `<div style="display:flex;gap:8px;align-items:center;padding:4px 0;border-bottom:1px solid var(--border2);">
      <span class="mono" style="flex:1.5">${x.id}</span>
      <span style="flex:1">${x.tpa}</span>
      <span class="mono" style="flex:0.8">${INR(x.amount)}</span>
      ${pill(x.status||'—', x.status.toLowerCase().includes('reject')?'red':x.status.toLowerCase().includes('approv')?'green':'amber')}
      <button class="btn btn-muted btn-sm" onclick="closeModal();showDetail('claim','${x.id}')">View</button>
    </div>`).join('') : '<div class="dimmed" style="font-size:11px">No claims on record</div>';
  const alHtml = d.alerts.length ? d.alerts.map(x=>
    `<div style="display:flex;gap:8px;align-items:center;padding:4px 0;border-bottom:1px solid var(--border2);">
      <span class="mono" style="flex:1">${x.id}</span>
      <span style="flex:1">${x.param}: <strong>${x.value}</strong></span>
      ${pill(x.status||'—', x.breached?'red':'amber')}
      <button class="btn btn-muted btn-sm" onclick="closeModal();showDetail('alert','${x.id}')">View</button>
    </div>`).join('') : '<div class="dimmed" style="font-size:11px">No critical alerts</div>';
  body.innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">
      ${_row('UHID', d.uhid, true)}
      ${_row('Name', d.name)}
      ${_row('Age', d.age+' yrs')}
      ${_row('Gender', d.gender)}
      ${_row('Contact', d.contact)}
      ${_row('Registration Date', d.registration_date)}
      ${_row('Status', d.status)}
      ${_row('Current Bed', d.current_bed_id)}
    </div>
    ${a.doctor ? `<hr style="border-color:var(--border2);margin:12px 0">
    <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;margin-bottom:6px;">Active Admission</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 24px;">
      ${_row('Doctor', a.doctor)} ${_row('Diagnosis', a.diagnosis)}
      ${_row('Admission Date', a.date)} ${_row('Department', a.dept)}
    </div>` : ''}
    <hr style="border-color:var(--border2);margin:12px 0">
    <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;margin-bottom:6px;">Discharge Records</div>
    ${disHtml}
    <hr style="border-color:var(--border2);margin:12px 0">
    <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;margin-bottom:6px;">Insurance Claims</div>
    ${clHtml}
    <hr style="border-color:var(--border2);margin:12px 0">
    <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;margin-bottom:6px;">Critical Lab Alerts</div>
    ${alHtml}
    <div style="margin-top:16px;">
      ${_askBtn('Give me the full operational status for patient ' + d.name + ' (UHID: ' + d.uhid + '). Include discharge status, claims, and any active alerts.')}
    </div>`;
}

function assignBedFromModal(bedId) {
  const uhid = document.getElementById('assignUhid_'+bedId).value.trim();
  if (!uhid) { showToast('Enter a UHID first', 'error'); return; }
  doAction(`/api/v1/ops/bed/${encodeURIComponent(bedId)}/assign?uhid=${encodeURIComponent(uhid)}`);
  closeModal();
}

// ── RBAC ─────────────────────────────────────────────────────────────────────
let _currentRole = 'ADMIN';

// Sections each role is permitted to see (all others are hidden)
const ROLE_SECTIONS = {
  ADMIN:         ['overview','beds','discharge','lab','billing','revenue','patients','reports','approvals','audit','agent'],
  DOCTOR:        ['overview','discharge','lab','patients','reports','agent'],
  NURSE:         ['overview','beds','discharge','patients','reports','agent'],
  BILLING_STAFF: ['overview','billing','revenue','reports','agent'],
};

function _permittedSections(role) {
  return ROLE_SECTIONS[role] || ROLE_SECTIONS['ADMIN'];
}
function _canSeeSection(name) {
  return _permittedSections(_currentRole).includes(name);
}

function _applySidebarVisibility(role) {
  const permitted = _permittedSections(role);
  // All sidebar items have id="nav-<sectionName>"
  document.querySelectorAll('.sidebar-item[id^="nav-"]').forEach(el => {
    const sec = el.id.replace('nav-', '');
    if (permitted.includes(sec)) {
      el.style.display = '';
      el.title = '';
    } else {
      el.style.display = 'none';
    }
  });
}

function setRole(role) {
  _currentRole = role;
  const labels = {ADMIN:'👑 Admin', DOCTOR:'🩺 Doctor', NURSE:'💉 Nurse', BILLING_STAFF:'💳 Billing'};
  const colors  = {ADMIN:'#6366F1', DOCTOR:'#10B981', NURSE:'#3B82F6', BILLING_STAFF:'#F59E0B'};
  const lbl = document.getElementById('roleBadgeLabel');
  if (lbl) { lbl.textContent = labels[role]||role; lbl.style.background = colors[role]||'#6366F1'; }

  // 1. Update sidebar — hide sections this role can't see
  _applySidebarVisibility(role);

  // 2. If currently viewing a restricted section, redirect to first permitted
  const activeSection = document.querySelector('.section.active');
  if (activeSection) {
    const currentName = activeSection.id.replace('section-', '');
    if (!_canSeeSection(currentName)) {
      const first = _permittedSections(role)[0] || 'overview';
      showSection(first);
    }
  }

  // 3. Re-fetch live data filtered for this role
  fetchAndRender();

  showToast('Switched to ' + (labels[role]||role) + ' — dashboard filtered for your role.', 'info');
}

// Apply sidebar visibility on first load (default ADMIN = all visible)
document.addEventListener('DOMContentLoaded', () => _applySidebarVisibility('ADMIN'));

// ── APPROVALS ────────────────────────────────────────────────────────────────
async function loadApprovals() {
  try {
    const d = await fetch('/api/v1/approvals/pending').then(r=>r.json());
    const badge = document.getElementById('approvalBadge');
    const count = d.count || 0;
    if (badge) { badge.textContent = count; badge.style.display = count > 0 ? 'inline' : 'none'; }
    const el = document.getElementById('aprCount');
    if (el) el.textContent = count;
    const tbody = document.getElementById('approvalRows');
    if (!tbody) return;
    if (!d.items || !d.items.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty" style="color:var(--green)">&#10003; No pending approvals</td></tr>';
    } else {
      tbody.innerHTML = d.items.map(a => `<tr>
        <td class="mono" style="font-size:10px;">${a.id}</td>
        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${a.query}">${a.query}</td>
        <td>${pill(a.guardrail||'—','red')}</td>
        <td class="dimmed">${a.escalation||'—'}</td>
        <td class="dimmed" style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${a.reason||'—'}</td>
        <td class="dimmed mono" style="font-size:9px;">${(a.created_at||'').substring(0,19).replace('T',' ')}</td>
        <td><div style="display:flex;gap:5px;">
          <button class="btn btn-green btn-sm" onclick="resolveApproval('${a.id}','approve')">&#10003; Approve</button>
          <button class="btn btn-red btn-sm" onclick="resolveApproval('${a.id}','deny')">&#10007; Deny</button>
        </div></td>
      </tr>`).join('');
    }
    // History — pull from audit log
    const hist = await fetch('/api/v1/audit/log?event_type=APPROVAL&limit=20').then(r=>r.json());
    const hbody = document.getElementById('approvalHistoryRows');
    if (hbody && hist.entries && hist.entries.length) {
      hbody.innerHTML = hist.entries.map(e=>`<tr>
        <td class="mono" style="font-size:10px;">${e.entity_id}</td>
        <td class="dimmed" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${e.detail||'—'}</td>
        <td>${pill(e.action||'—', e.action==='approved'?'green':'red')}</td>
        <td class="dimmed">${e.role||'admin'}</td>
        <td class="dimmed mono" style="font-size:9px;">${(e.timestamp||'').substring(0,19).replace('T',' ')}</td>
      </tr>`).join('');
    }
  } catch(e) { console.error('loadApprovals', e); }
}

async function resolveApproval(id, action) {
  await doAction(`/api/v1/approvals/${id}/${action==='approve'?'approve':'deny'}`);
  setTimeout(loadApprovals, 400);
}

// ── AUDIT LOG ────────────────────────────────────────────────────────────────
async function loadAuditLog() {
  try {
    const filterEl = document.getElementById('auditTypeFilter');
    const filter = filterEl ? filterEl.value : '';
    const url = '/api/v1/audit/log?limit=200' + (filter ? '&event_type='+encodeURIComponent(filter) : '');
    const d = await fetch(url).then(r=>r.json());
    const el = document.getElementById('auditCount');
    if (el) el.textContent = d.count + ' entries';
    const tbody = document.getElementById('auditRows');
    if (!tbody) return;
    if (!d.entries || !d.entries.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">No audit entries yet — perform actions to see them here</td></tr>';
      return;
    }
    const typeColor = {QUERY:'muted',GUARDRAIL:'red',ACTION:'green',APPROVAL:'amber',RBAC_DENY:'red'};
    tbody.innerHTML = d.entries.map(e=>`<tr>
      <td class="mono" style="font-size:9px;">${e.id}</td>
      <td class="dimmed mono" style="font-size:9px;">${(e.timestamp||'').substring(0,19).replace('T',' ')}</td>
      <td>${pill(e.event_type||'—', typeColor[e.event_type]||'muted')}</td>
      <td class="mono" style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${e.entity_id||'—'}</td>
      <td>${e.action||'—'}</td>
      <td class="dimmed" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${e.detail||'—'}</td>
      <td>${pill(e.role||'system','muted')}</td>
    </tr>`).join('');
  } catch(err) { console.error('loadAuditLog', err); }
}

// ── NODE LIFECYCLE / TTL ──────────────────────────────────────────────────────
async function loadLifecycleStats() {
  const el = document.getElementById('lifecycleStats');
  if (!el) return;
  try {
    const d = await fetch('/api/v1/ops/lifecycle/stats').then(r => r.json());
    const totals = d.totals || {};
    const byType = d.by_type || {};
    const ttlColors = { live: '#22c55e', terminal: '#f59e0b', expired: '#ef4444' };
    const cards = Object.entries(byType).map(([type, counts]) => {
      const shortName = type.replace('Node','');
      const total = counts.total || 0;
      const liveW = total ? Math.round((counts.live / total) * 100) : 0;
      const termW = total ? Math.round((counts.terminal / total) * 100) : 0;
      const expW  = total ? Math.round((counts.expired / total) * 100) : 0;
      return `<div style="background:#1a1f2e;border:1px solid #2d3452;border-radius:6px;padding:8px 10px;min-width:150px;">
        <div style="font-size:11px;font-weight:600;color:#e2e8f0;margin-bottom:4px;">${shortName}</div>
        <div style="font-size:10px;color:#94a3b8;margin-bottom:6px;">${total} total</div>
        <div style="display:flex;gap:3px;height:4px;border-radius:2px;overflow:hidden;">
          <div style="width:${liveW}%;background:${ttlColors.live};"></div>
          <div style="width:${termW}%;background:${ttlColors.terminal};"></div>
          <div style="width:${expW}%;background:${ttlColors.expired};"></div>
        </div>
        <div style="display:flex;gap:8px;margin-top:4px;font-size:9px;">
          <span style="color:${ttlColors.live};">● ${counts.live} active</span>
          <span style="color:${ttlColors.terminal};">● ${counts.terminal} terminal</span>
          ${counts.expired ? `<span style="color:${ttlColors.expired};">● ${counts.expired} expired</span>` : ''}
        </div>
      </div>`;
    }).join('');
    el.innerHTML = `
      <div style="display:flex;gap:16px;margin-bottom:10px;flex-wrap:wrap;">
        <span style="font-size:12px;color:#22c55e;">● ${totals.live||0} active</span>
        <span style="font-size:12px;color:#f59e0b;">● ${totals.terminal||0} terminal (counting down)</span>
        <span style="font-size:12px;color:#ef4444;">● ${totals.expired||0} expired (will be pruned)</span>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:8px;">${cards}</div>
      <div style="font-size:10px;color:#475569;margin-top:8px;">Last checked: ${(d.timestamp||'').substring(0,19).replace('T',' ')} UTC · Auto-pruner runs every 5 min</div>`;
  } catch(err) {
    if (el) el.innerHTML = '<div class="empty">Lifecycle stats unavailable</div>';
    console.error('loadLifecycleStats', err);
  }
}

async function runPruner() {
  showToast('Running node pruner…', 'info');
  try {
    const d = await doAction('/api/v1/ops/prune');
    const total = d.pruned_total || 0;
    showToast(total > 0
      ? `Pruner removed ${total} expired nodes`
      : 'Pruner ran — no expired nodes found', total > 0 ? 'success' : 'info');
    await loadLifecycleStats();
  } catch(err) {
    showToast('Pruner failed: ' + (err.message || err), 'error');
  }
}

// ── REPORTS ───────────────────────────────────────────────────────────────────
function downloadReport(type) {
  if (!_liveData) { showToast('No data — refresh first','error'); return; }
  let rows = [], headers = [], filename = '';
  const d = _liveData;
  if (type === 'beds') {
    headers = ['Bed ID','Ward','Status','Patient UHID','Patient Name'];
    rows = (d.bed_census.bed_rows||[]).map(b=>[b.bed_id,b.ward,b.status,b.patient_uhid,b.patient_name]);
    filename = 'smch_bed_report.csv';
  } else if (type === 'discharges') {
    headers = ['Discharge ID','UHID','Patient','Ward','Bed','Clinical','Pharmacy','Billing','Nursing','Blocked','Blocker'];
    rows = (d.discharge_pipeline.rows||[]).filter(r=>r.is_blocked).map(r=>[r.discharge_id,r.uhid,r.patient_name,r.ward,r.bed_id,r.clinical,r.pharmacy,r.billing,r.nursing,r.is_blocked,r.blocker_reason]);
    filename = 'smch_blocked_discharges.csv';
  } else if (type === 'alerts') {
    headers = ['Alert ID','UHID','Patient','Parameter','Value','Elapsed Min','SLA Min','Breached','Readback','Doctor Contacted'];
    rows = (d.panic_alerts.rows||[]).map(a=>[a.alert_id,a.uhid,a.patient_name,a.parameter,a.value,a.elapsed_min,a.sla_limit_min,a.sla_breached,a.readback_status,a.doctor_contacted]);
    filename = 'smch_sla_breaches.csv';
  } else if (type === 'revenue') {
    headers = ['Claim ID','UHID','Patient','TPA','Amount','Status','Rejection Reason'];
    rows = (d.revenue.claim_rows||[]).filter(r=>r.is_rejected||(r.status||'').toLowerCase()==='pending').map(c=>[c.claim_id,c.uhid,c.patient_name,c.tpa,c.amount,c.status,c.rejection_reason]);
    filename = 'smch_revenue_risk.csv';
  } else if (type === 'patients') {
    headers = ['UHID','Name','Status','Gender','Age','Ward','Bed','Diagnosis'];
    rows = (d.patients.rows||[]).map(p=>[p.uhid,p.name,p.status,p.gender,p.age,p.ward,p.bed_id,p.diagnosis]);
    filename = 'smch_patient_census.csv';
  } else {
    headers = ['Alert ID','UHID','Patient','Parameter','Value','Elapsed Min','SLA Min','SLA Breached','Readback','Doctor Contacted','Doctor Phone'];
    rows = (d.panic_alerts.rows||[]).map(a=>[a.alert_id,a.uhid,a.patient_name,a.parameter,a.value,a.elapsed_min,a.sla_limit_min,a.sla_breached,a.readback_status,a.doctor_contacted,a.doctor_phone]);
    filename = 'smch_alert_log.csv';
  }
  const csv = [headers, ...rows].map(r => r.map(v => '"' + String(v||'').replace(/"/g,'""') + '"').join(',')).join('\\n');
  const a = document.createElement('a');
  a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
  a.download = filename; a.click();
  showToast('Downloading ' + filename, 'success');
}

// ── AI CHAT ───────────────────────────────────────────────────────────────────
function chatAppend(role, content, extra) {
  const msgs = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = 'chat-msg ' + role;
  if (extra && extra.guardrail) {
    div.className = 'chat-msg guardrail';
    let html = `<div>${content}</div>`;
    if (extra.escalation) html += `<div style="margin-top:5px;font-size:10px;font-weight:700;">${extra.escalation}</div>`;
    if (extra.escalation_reason) html += `<div style="font-size:9px;margin-top:2px;opacity:0.7;">${extra.escalation_reason}</div>`;
    div.innerHTML = html;
  } else if (role === 'assistant') {
    let html = '';
    if (extra && extra.confidence && extra.confidence.level) {
      html += `<span class="chat-confidence conf-${extra.confidence.level}">Confidence: ${extra.confidence.level}</span><br>`;
    }
    html += `<div style="white-space:pre-wrap;">${content}</div>`;
    if (extra && extra.workflow_step && extra.workflow_step.name !== 'Complete') {
      const ws = extra.workflow_step;
      html += `<div class="chat-workflow"><div class="chat-wf-title">Next Step (${ws.step}/${ws.total_steps}): ${ws.name}</div><div class="chat-wf-action">${ws.action_required}</div><div class="chat-wf-contact">${ws.contact}</div></div>`;
    }
    if (extra && extra.source_citations && extra.source_citations.length) {
      html += `<div class="chat-citations">Sources: ${extra.source_citations.map(c=>c.id+' ['+c.type+']').join(' · ')}</div>`;
    }
    div.innerHTML = html;
  } else {
    div.textContent = content;
  }
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

async function sendChat() {
  const inp = document.getElementById('chatInput');
  const q = inp.value.trim();
  if (!q) return;
  inp.value = '';
  chatAppend('user', q);
  agentHistory.push({role:'user', content:q});
  const thinking = document.createElement('div');
  thinking.className = 'chat-msg assistant chat-thinking';
  thinking.innerHTML = '<span class="tdot"></span><span class="tdot"></span><span class="tdot"></span>';
  document.getElementById('chatMessages').appendChild(thinking);
  document.getElementById('chatMessages').scrollTop = 99999;
  try {
    const r = await fetch('/api/v1/agent/query', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({query:q, conversation_history: agentHistory.slice(-6), role: _currentRole})
    });
    const d = await r.json();
    thinking.remove();
    const answer = d.answer || JSON.stringify(d);
    chatAppend(d.guardrail_triggered ? 'guardrail' : 'assistant', answer, d);
    agentHistory.push({role:'assistant', content:answer});
    if (agentHistory.length > 20) agentHistory = agentHistory.slice(-12);
  } catch(e) {
    thinking.remove();
    chatAppend('assistant', '[Connection error — retrying…]');
  }
}

// ── MASTER RENDER ─────────────────────────────────────────────────────────────
function renderAll(d) {
  _liveData = d;
  renderOverview(d);
  renderBedSection(d);
  renderDischargeSection(d);
  renderAlertsSection(d);
  renderBillingSection(d);
  renderRevenueSection(d);
  renderPatientSection(d);
  updateCharts(d);
  loadApprovals();  // keep approval badge up to date
  const t = new Date(d.timestamp);
  document.getElementById('syncTime').textContent = 'Synced ' + t.toLocaleTimeString();
}

async function fetchAndRender() {
  try {
    const role = typeof _currentRole !== 'undefined' ? _currentRole : 'ADMIN';
    const res = await fetch('/api/v1/dashboard/live?role=' + encodeURIComponent(role));
    const data = await res.json();
    renderAll(data);
    document.getElementById('loadingOverlay').style.display = 'none';
  } catch(e) {
    document.getElementById('syncTime').textContent = 'Sync error — retrying…';
  }
}

// Close modal on overlay click
document.getElementById('patModal').addEventListener('click', function(e) { if (e.target === this) closeModal(); });

// Chat enter key
document.getElementById('chatInput').addEventListener('keydown', e => { if (e.key === 'Enter') sendChat(); });

initCharts();
fetchAndRender();
loadLifecycleStats();
setInterval(fetchAndRender, 30000);
setInterval(loadLifecycleStats, 300000);  // refresh lifecycle stats every 5 min
</script>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard() -> str:
    return DASHBOARD_HTML
