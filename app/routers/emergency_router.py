"""
Emergency & Trauma Care API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/emergency", tags=["Emergency & Trauma Care"])

@router.get("/triage", summary="Get active emergency triage queue")
def get_emergency_triage(
    status: Optional[str] = Query("Active", description="Filter by status (Active, Discharged, Admitted)"),
    triage_level: Optional[str] = Query(None, description="Filter by P1, P2, or P3"),
    limit: int = Query(50, ge=1, le=200)
):
    """
    Returns live Emergency Department triage records:
    - P1: Resuscitation (immediate life threat)
    - P2: Emergent / Urgent
    - P3: Non-urgent
    Includes time-to-doctor timestamps, triage nurse notes, and vital signs.
    """
    query = "SELECT * FROM emergency_cases WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if triage_level:
        query += " AND triage_level = ?"
        params.append(triage_level)
    query += " ORDER BY CASE triage_level WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END, arrival_time DESC LIMIT ?"
    params.append(limit)

    cases = execute_query(query, tuple(params))
    return {
        "department": "Emergency & Trauma Care",
        "total_count": len(cases),
        "data": cases
    }

@router.post("/triage", summary="Register emergency walk-in or ambulance arrival")
async def register_emergency_case(payload: Dict[str, Any] = Body(...)):
    """
    Manually register or intake an emergency patient.
    """
    case_id = f"ED-MAN-{datetime.now().strftime('%m%d%H%M%S')}"
    uhid = payload.get("uhid", f"SMCH-{datetime.now().strftime('%y%m%d%S')}")
    name = payload.get("patient_name", "Unknown Patient")
    age = payload.get("age", 45)
    gender = payload.get("gender", "Unknown")
    arrival_mode = payload.get("arrival_mode", "Walk-in")
    triage_level = payload.get("triage_level", "P2")
    chief_complaint = payload.get("chief_complaint", "Acute distress")
    hr = payload.get("hr", 90)
    bp_sys = payload.get("bp_sys", 120)
    bp_dia = payload.get("bp_dia", 80)
    spo2 = payload.get("spo2", 98)
    doctor = payload.get("assigned_doctor", "Dr. K. Venkatraman")

    execute_insert(
        """INSERT INTO emergency_cases 
           (case_id, uhid, patient_name, age, gender, arrival_mode, ambulance_id, paramedic_notes, 
            triage_level, chief_complaint, hr, bp_sys, bp_dia, spo2, rr, temp, gcs, arrival_time, 
            doctor_seen_time, time_to_doctor_min, assigned_doctor, disposition, status, clinical_reasoning)
           VALUES (?, ?, ?, ?, ?, ?, NULL, 'Intake at emergency desk', ?, ?, ?, ?, ?, ?, 18, 98.4, 15, ?, NULL, NULL, ?, 'In-Evaluation', 'Active', 'Initial emergency assessment initiated.');""",
        (case_id, uhid, name, age, gender, arrival_mode, triage_level, chief_complaint, hr, bp_sys, bp_dia, spo2, datetime.now().isoformat(), doctor)
    )

    await event_bus.publish_event(
        department="Emergency Department",
        event_type="Manual Triage Intake",
        severity="WARNING" if triage_level == "P2" else ("CRITICAL" if triage_level == "P1" else "INFO"),
        summary=f"[{triage_level}] Registered {name} ({age}y/{gender}) via {arrival_mode}: {chief_complaint}",
        uhid=uhid,
        patient_name=name,
        details={"case_id": case_id, "triage_level": triage_level, "doctor": doctor}
    )

    return {"status": "success", "case_id": case_id, "uhid": uhid}

@router.get("/ambulances", summary="Inbound and arrived ambulance transport logs")
def get_ambulance_logs(limit: int = 25):
    """
    Returns pre-hospital ambulance arrival logs, vehicle IDs, paramedic handover notes,
    and transit vital signs.
    """
    cases = execute_query(
        "SELECT case_id, uhid, patient_name, arrival_mode, ambulance_id, paramedic_notes, arrival_time, triage_level FROM emergency_cases WHERE ambulance_id IS NOT NULL ORDER BY arrival_time DESC LIMIT ?",
        (limit,)
    )
    return {"total_count": len(cases), "ambulances": cases}

@router.get("/dispositions", summary="Emergency disposition and outcome breakdown")
def get_emergency_dispositions(limit: int = 50):
    """
    Returns patient disposition outcomes (Admitted to ICU, Admitted to Ward, Discharged, DAMA, Transferred).
    """
    rows = execute_query(
        "SELECT case_id, uhid, patient_name, chief_complaint, disposition, arrival_time, doctor_seen_time, time_to_doctor_min, assigned_doctor FROM emergency_cases WHERE disposition IS NOT NULL ORDER BY arrival_time DESC LIMIT ?",
        (limit,)
    )
    return {"total_count": len(rows), "dispositions": rows}

@router.get("/stats", summary="Emergency Department operational KPIs")
def get_emergency_stats():
    """
    Calculates live occupancy, P1/P2/P3 ratio, and average door-to-doctor time.
    """
    p_counts = execute_query("SELECT triage_level, COUNT(*) as count FROM emergency_cases WHERE status = 'Active' GROUP BY triage_level;")
    avg_door = execute_query("SELECT AVG(time_to_doctor_min) as avg_min FROM emergency_cases WHERE time_to_doctor_min IS NOT NULL;")
    return {
        "active_cases": sum(r["count"] for r in p_counts),
        "triage_breakdown": {r["triage_level"]: r["count"] for r in p_counts},
        "average_door_to_doctor_minutes": round(avg_door[0]["avg_min"] or 6.5, 1)
    }
