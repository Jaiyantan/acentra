"""
Blood Centre & Transfusion Medicine (BBIS) API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/blood-bank", tags=["Blood Centre (BBIS)"])

@router.get("/inventory", summary="Blood component inventory by ABO/Rh group")
def get_blood_bank_inventory(blood_group: Optional[str] = None):
    """
    Returns available units across PRBC, Fresh Frozen Plasma (FFP), Platelet Concentrates,
    and Cryoprecipitate with storage locations and expiry dates.
    """
    query = "SELECT * FROM blood_bank_units WHERE 1=1"
    params = []
    if blood_group:
        query += " AND blood_group = ?"
        params.append(blood_group)
    query += " ORDER BY expiry_date ASC"
    units = execute_query(query, tuple(params))
    
    # Summary by component and blood group
    summary = execute_query(
        "SELECT component, blood_group, COUNT(*) as count FROM blood_bank_units WHERE status = 'Available' GROUP BY component, blood_group;"
    )
    return {
        "available_units_count": len(units),
        "summary": summary,
        "units": units
    }

@router.get("/crossmatch", summary="Crossmatch requests and compatibility clearance")
def get_crossmatch_requests(limit: int = 50):
    """
    Returns crossmatch compatibility testing records for OT, ICU, and Emergency requisitions.
    """
    rows = execute_query(
        "SELECT * FROM blood_bank_crossmatch ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    return {"crossmatch_records": rows}

@router.get("/issues", summary="Blood unit issue logs to clinical departments")
def get_blood_issues(limit: int = 50):
    """
    Returns blood unit issue logs with issuing technician, receiving nurse,
    destination ward, and bedside verification confirmation.
    """
    rows = execute_query(
        "SELECT * FROM blood_bank_issues ORDER BY issue_time DESC LIMIT ?",
        (limit,)
    )
    return {"blood_issues": rows}

@router.get("/temperature-logs", summary="Blood bank cold room and deep freezer telemetry")
def get_blood_bank_temps():
    """
    Returns temperature logs for RBC cold rooms (2°C to 6°C) and FFP deep freezers (-18°C or colder).
    """
    logs = execute_query("SELECT * FROM blood_bank_temp_logs ORDER BY timestamp DESC LIMIT 20;")
    return {"temperature_telemetry": logs}
