"""
Biomedical Engineering & Administration API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/biomedical", tags=["Biomedical Engineering & Staff"])

@router.get("/equipment", summary="Medical equipment asset register, uptime %, and calibration")
def get_equipment_register():
    """
    Returns asset records for high-value equipment: DaVinci Xi Robot, 3T MRI, 128-Slice CT,
    ECMO, Cath Lab, Dialysis machines with maintenance dates and uptime %.
    """
    assets = execute_query("SELECT * FROM biomedical_equipment ORDER BY uptime_pct DESC;")
    return {"total_assets": len(assets), "equipment": assets}

@router.get("/breakdowns", summary="Equipment breakdown tickets and repair status")
def get_breakdown_tickets(status: Optional[str] = None):
    """
    Returns real-time equipment breakdown tickets, assigned biomedical engineers, and clinical impact.
    """
    query = "SELECT * FROM biomedical_breakdowns WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY reported_at DESC"
    tickets = execute_query(query, tuple(params))
    return {"breakdowns": tickets}

@router.get("/staff", summary="Hospital clinical staff directory and medical council licenses")
def get_staff_directory(department: Optional[str] = None):
    """
    Returns healthcare worker master records (doctors, nurses, engineers) with registration numbers
    and NABH credentialing statuses.
    """
    query = "SELECT * FROM staff_master WHERE 1=1"
    params = []
    if department:
        query += " AND department LIKE ?"
        params.append(f"%{department}%")
    staff = execute_query(query, tuple(params))
    return {"total_staff": len(staff), "staff": staff}
