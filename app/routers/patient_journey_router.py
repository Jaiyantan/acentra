"""
10-State Patient Journey Lifecycle API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
Implements the 10 Patient Journey States defined on Page 3 of Hack to Care Build Plan:
REGISTERED -> TRIAGED -> ADMITTED -> UNDER_TREATMENT -> INVESTIGATION ->
SURGERY -> RECOVERY -> DISCHARGE_PENDING -> DISCHARGED -> FOLLOW_UP
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.engine.workflow_engine import workflow_engine

router = APIRouter(prefix="/api/patient-journey", tags=["Patient Journey Lifecycle (10 States)"])

JOURNEY_STATES = [
    "REGISTERED", "TRIAGED", "ADMITTED", "UNDER_TREATMENT", "INVESTIGATION",
    "SURGERY", "RECOVERY", "DISCHARGE_PENDING", "DISCHARGED", "FOLLOW_UP"
]

@router.get("/states", summary="List the 10 defined Patient Journey States")
def get_journey_states():
    """
    Returns the 10 standardized patient lifecycle states.
    """
    return {
        "lifecycle_states": JOURNEY_STATES,
        "state_sequence": "REGISTERED → TRIAGED → ADMITTED → UNDER_TREATMENT → INVESTIGATION → SURGERY → RECOVERY → DISCHARGE_PENDING → DISCHARGED → FOLLOW_UP"
    }

@router.get("/census", summary="Hospital-wide census breakdown across the 10 journey states")
def get_journey_census():
    """
    Returns count and active patient breakdown for each of the 10 journey states.
    """
    rows = execute_query(
        "SELECT current_state, COUNT(*) as count FROM patient_journeys GROUP BY current_state;"
    )
    counts = {r["current_state"]: r["count"] for r in rows}
    full_breakdown = {state: counts.get(state, 0) for state in JOURNEY_STATES}
    return {
        "total_tracked_patients": sum(full_breakdown.values()),
        "breakdown": full_breakdown,
        "census": full_breakdown
    }

@router.get("/active", summary="List active patients currently tracked in journey pipeline")
def get_active_journeys(limit: int = 50):
    """
    Returns active patient journeys currently in any of the 10 states.
    """
    rows = execute_query(
        "SELECT * FROM patient_journeys ORDER BY last_state_change DESC LIMIT ?",
        (limit,)
    )
    return {
        "total": len(rows),
        "active_journeys": rows
    }

@router.get("/{uhid}", summary="Get patient's current journey state and transition history")
def get_patient_journey(uhid: str):
    """
    Returns a patient's current location in the 10-state lifecycle and past milestones.
    """
    rows = execute_query("SELECT * FROM patient_journeys WHERE uhid = ?", (uhid,))
    if not rows:
        raise HTTPException(status_code=404, detail="Patient journey record not found.")
    return rows[0]

@router.post("/transition", summary="Advance patient state with workflow validation")
def transition_patient_state(
    uhid: str = Body(..., embed=True),
    target_state: str = Body(..., embed=True),
    authorized_by: str = Body("Doctor", embed=True),
    notes: Optional[str] = Body(None, embed=True)
):
    """
    Transitions a patient to the next state in the 10-state sequence.
    """
    if target_state not in JOURNEY_STATES:
        raise HTTPException(status_code=400, detail=f"Invalid state. Must be one of: {JOURNEY_STATES}")

    result = workflow_engine.transition_patient_journey(uhid, target_state)
    return {"status": "SUCCESS", "transition": result, "authorized_by": authorized_by}
