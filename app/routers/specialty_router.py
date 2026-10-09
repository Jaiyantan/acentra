"""
Specialty & Super-Specialty Clinics API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/specialty", tags=["Specialty & Super-Specialty Clinics"])

@router.get("/records", summary="Specialist consultation records and procedure notes")
def get_specialty_records(specialty: Optional[str] = None, limit: int = 50):
    """
    Returns procedure reports across Cardiology (Cath Lab Angiography/PTCA, Echo),
    Gastroenterology (Endoscopy/Colonoscopy), Neurology (EEG/EMG), and Nephrology.
    """
    query = "SELECT * FROM specialty_records WHERE 1=1"
    params = []
    if specialty:
        query += " AND specialty LIKE ?"
        params.append(f"%{specialty}%")
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    rows = execute_query(query, tuple(params))
    return {"total": len(rows), "records": rows}

@router.get("/oncology/chemotherapy", summary="Daycare chemotherapy infusion sessions")
def get_chemo_sessions(limit: int = 50):
    """
    Returns chemotherapy administration logs: Regimen, cycle count, drugs infused,
    and CTCAE adverse reaction grading.
    """
    rows = execute_query(
        "SELECT * FROM oncology_chemo_sessions ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    return {"chemo_sessions": rows}

@router.get("/oncology/tumor-boards", summary="Multidisciplinary Tumor Board meeting records")
def get_tumor_board_records(limit: int = 20):
    """
    Returns tumor board multidisciplinary discussions and consensus treatment decisions.
    """
    rows = execute_query(
        "SELECT * FROM tumor_board_records ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    return {"tumor_boards": rows}
