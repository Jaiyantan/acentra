"""
Hemodialysis & Nephrology Unit API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/dialysis", tags=["Hemodialysis & Nephrology"])

@router.get("/sessions", summary="Live hemodialysis stations & telemetry parameters")
def get_dialysis_sessions(status: Optional[str] = "Active"):
    """
    Returns live hemodialysis sessions across 16 stations:
    - Dialyzer model (e.g. FX80 Cordiax)
    - Vascular access (AV Fistula / Permcath)
    - Blood Flow Rate Qb (mL/min)
    - Dialysate Flow Rate Qd (mL/min)
    - Venous Pressure (mmHg)
    - Transmembrane Pressure TMP (mmHg)
    - Total Ultrafiltration (UF) removed (mL)
    - Conductivity (mS/cm)
    """
    query = "SELECT * FROM dialysis_sessions WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY station_no ASC"
    sessions = execute_query(query, tuple(params))
    return {"active_stations_count": len(sessions), "sessions": sessions}
