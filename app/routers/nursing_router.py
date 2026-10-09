"""
Nursing Administration & Shift Quality API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/nursing", tags=["Nursing Administration"])

@router.get("/rosters", summary="Shift duty rosters and nurse-to-patient ratios")
def get_nursing_rosters(ward: Optional[str] = None):
    """
    Returns nurse staffing assignments and real-time nurse-to-patient ratios per ward.
    """
    query = "SELECT * FROM nursing_rosters WHERE 1=1"
    params = []
    if ward:
        query += " AND ward_name LIKE ?"
        params.append(f"%{ward}%")
    rosters = execute_query(query, tuple(params))
    return {"rosters": rosters}

@router.get("/handovers", summary="Shift-to-shift SBAR verbal and written handovers")
def get_nursing_handovers(limit: int = 50):
    """
    Returns nursing shift handovers, oral handover notes, and high-risk patient flags.
    """
    handovers = execute_query(
        "SELECT * FROM nursing_shift_handovers ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    return {"handovers": handovers}

@router.get("/incidents", summary="NABH incident reports (Falls, Medication errors, Pressure sores)")
def get_nursing_incidents(severity: Optional[str] = None, limit: int = 50):
    """
    Returns incident reports and sentinel event audits.
    """
    query = "SELECT * FROM nursing_incidents WHERE 1=1"
    params = []
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    rows = execute_query(query, tuple(params))
    return {"total": len(rows), "incidents": rows}
