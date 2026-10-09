"""
Inpatient Department (IPD) API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/ipd", tags=["Inpatient Department (IPD)"])

@router.get("/admissions", summary="Active inpatient admissions census")
def get_ipd_admissions(
    ward: Optional[str] = None,
    status: Optional[str] = "Active",
    limit: int = 50
):
    """
    Returns active admitted patients, admitting doctors, admitting diagnoses, and ward locations.
    """
    query = "SELECT * FROM ipd_admissions WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if ward:
        query += " AND ward_name LIKE ?"
        params.append(f"%{ward}%")
    query += " ORDER BY admission_time DESC LIMIT ?"
    params.append(limit)

    admissions = execute_query(query, tuple(params))
    return {"total": len(admissions), "admissions": admissions}

@router.get("/beds", summary="Hospital bed master and occupancy status (1,600 bed tracking)")
def get_ipd_beds(ward: Optional[str] = None, status: Optional[str] = None):
    """
    Returns bed allocation across all general wards, special rooms, and HDUs.
    Status: Occupied, Vacant, Cleaning, Maintenance.
    """
    query = "SELECT * FROM ipd_beds WHERE 1=1"
    params = []
    if ward:
        query += " AND ward_name LIKE ?"
        params.append(f"%{ward}%")
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " LIMIT 300"
    beds = execute_query(query, tuple(params))

    # Calculate overall occupancy summary
    summary_stats = execute_query("SELECT status, COUNT(*) as count FROM ipd_beds GROUP BY status;")
    return {
        "summary": {r["status"]: r["count"] for r in summary_stats},
        "beds_returned": len(beds),
        "beds": beds
    }

@router.get("/progress-notes", summary="Daily ward round SOAP progress notes")
def get_ipd_progress_notes(admission_id: Optional[str] = None, uhid: Optional[str] = None, limit: int = 50):
    """
    Returns Subjective, Objective, Assessment, Plan (SOAP) progress notes recorded during consultant ward rounds.
    """
    query = "SELECT * FROM ipd_progress_notes WHERE 1=1"
    params = []
    if admission_id:
        query += " AND admission_id = ?"
        params.append(admission_id)
    if uhid:
        query += " AND uhid = ?"
        params.append(uhid)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    notes = execute_query(query, tuple(params))
    return {"total": len(notes), "progress_notes": notes}

@router.get("/nursing-charts", summary="Nursing charts: Vitals, I/O Fluid Balance, and MAR")
def get_ipd_nursing_charts(admission_id: Optional[str] = None, limit: int = 50):
    """
    Returns nursing vital signs (q4h / q8h), urine output, fluid intake, and medication administration records.
    """
    query = "SELECT * FROM ipd_nursing_charts WHERE 1=1"
    params = []
    if admission_id:
        query += " AND admission_id = ?"
        params.append(admission_id)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    charts = execute_query(query, tuple(params))
    return {"total": len(charts), "nursing_charts": charts}
