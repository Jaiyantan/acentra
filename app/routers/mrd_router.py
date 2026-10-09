"""
Medical Records Department (MRD) API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/mrd", tags=["Medical Records Department (MRD)"])

@router.get("/mpi", summary="Master Patient Index (MPI) search by UHID or name")
def get_mrd_mpi(query_str: Optional[str] = Query(None, description="Search by UHID, name, or phone"), limit: int = 50):
    """
    Returns Master Patient Index records across the hospital's history.
    """
    if query_str:
        q = f"%{query_str}%"
        rows = execute_query(
            "SELECT * FROM patients WHERE uhid LIKE ? OR name LIKE ? OR phone LIKE ? LIMIT ?",
            (q, q, q, limit)
        )
    else:
        rows = execute_query("SELECT * FROM patients ORDER BY registered_at DESC LIMIT ?", (limit,))
    return {"total": len(rows), "patients": rows}

@router.get("/physical-files", summary="Physical case file archive rack location & borrowing logs")
def get_physical_files(limit: int = 50):
    """
    Returns physical paper case file warehouse tracking: rack IDs, box numbers,
    borrowing departments, and checkout dates.
    """
    files = execute_query("SELECT * FROM mrd_physical_files ORDER BY file_id DESC LIMIT ?", (limit,))
    return {"total": len(files), "physical_files": files}

@router.get("/mlc", summary="Medico-Legal Case (MLC) register and police intimation logs")
def get_mlc_records(limit: int = 50):
    """
    Returns Medico-Legal Cases (RTAs, industrial injuries, assaults) with police station intimations.
    """
    mlc = execute_query("SELECT * FROM mrd_mlc_records ORDER BY police_intimation_time DESC LIMIT ?", (limit,))
    return {"mlc_records": mlc}
