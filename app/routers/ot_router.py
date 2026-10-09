"""
Operation Theatre Complex API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/ot", tags=["Operation Theatre Complex"])

@router.get("/schedule", summary="Daily master surgical schedule and status")
def get_ot_schedule(ot_room: Optional[str] = None, status: Optional[str] = None):
    """
    Returns surgical theatre schedule across OT-01 to OT-06 (including DaVinci Xi Robotic Suite),
    tracking procedure name, primary surgeon, scheduled time, knife-to-skin time, and procedure-end time.
    """
    query = "SELECT * FROM ot_surgeries WHERE 1=1"
    params = []
    if ot_room:
        query += " AND ot_room = ?"
        params.append(ot_room)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY scheduled_time ASC"
    surgeries = execute_query(query, tuple(params))
    return {"total": len(surgeries), "surgeries": surgeries}

@router.get("/checklists", summary="WHO Surgical Safety Checklists verification logs")
def get_ot_checklists(surgery_id: Optional[str] = None):
    """
    Returns mandatory WHO surgical safety checklist verification:
    - Sign In (before induction of anesthesia)
    - Time Out (before knife-to-skin)
    - Sign Out (before patient leaves room)
    Includes allergy check, surgical site marking, sponge & needle count confirmation.
    """
    query = "SELECT * FROM ot_checklists WHERE 1=1"
    params = []
    if surgery_id:
        query += " AND surgery_id = ?"
        params.append(surgery_id)
    query += " ORDER BY timestamp DESC LIMIT 50"
    rows = execute_query(query, tuple(params))
    return {"checklists": rows}

@router.get("/implants", summary="Regulatory medical implant & prosthesis tracking")
def get_ot_implants(surgery_id: Optional[str] = None, limit: int = 50):
    """
    Returns high-risk surgical implant logs with regulatory lot numbers,
    serial numbers, and barcode tracking (stents, mesh, joints, staplers).
    """
    query = "SELECT * FROM ot_implants WHERE 1=1"
    params = []
    if surgery_id:
        query += " AND surgery_id = ?"
        params.append(surgery_id)
    query += " ORDER BY logged_at DESC LIMIT ?"
    params.append(limit)
    rows = execute_query(query, tuple(params))
    return {"implants": rows}
