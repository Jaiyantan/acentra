"""
Outpatient Department (OPD) API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/opd", tags=["Outpatient Department (OPD)"])

@router.get("/registrations", summary="Patient registrations and UHID master log")
def get_opd_registrations(limit: int = 50):
    """
    Returns registered outpatients with demographics, UHID, and payment/scheme category.
    """
    patients = execute_query(
        "SELECT * FROM patients ORDER BY registered_at DESC LIMIT ?",
        (limit,)
    )
    return {"department": "OPD Registrations", "total": len(patients), "registrations": patients}

@router.get("/tokens", summary="Active consultation room queue and token status")
def get_opd_tokens(specialty: Optional[str] = None):
    """
    Returns current consultation queue token allocation across clinical specialties.
    """
    query = "SELECT consultation_id, token_no, uhid, patient_name, specialty, doctor_name, queue_time, status FROM opd_consultations WHERE 1=1"
    params = []
    if specialty:
        query += " AND specialty = ?"
        params.append(specialty)
    query += " ORDER BY queue_time DESC LIMIT 100"
    tokens = execute_query(query, tuple(params))
    return {"total_in_queue": len(tokens), "tokens": tokens}

@router.get("/consultations", summary="Doctor consultation notes and ICD-10 diagnoses")
def get_opd_consultations(limit: int = 50, icd10: Optional[str] = None):
    """
    Returns specialist consultation records including examination findings,
    provisional diagnosis, and ICD-10 coding.
    """
    query = "SELECT * FROM opd_consultations WHERE 1=1"
    params = []
    if icd10:
        query += " AND icd10_code LIKE ?"
        params.append(f"%{icd10}%")
    query += " ORDER BY consultation_time DESC LIMIT ?"
    params.append(limit)
    rows = execute_query(query, tuple(params))
    return {"total": len(rows), "consultations": rows}

@router.get("/prescriptions", summary="Outpatient prescription orders")
def get_opd_prescriptions(limit: int = 50, uhid: Optional[str] = None):
    """
    Returns digital prescriptions issued by outpatient consultants.
    """
    query = "SELECT * FROM opd_prescriptions WHERE 1=1"
    params = []
    if uhid:
        query += " AND uhid = ?"
        params.append(uhid)
    query += " ORDER BY prescribed_at DESC LIMIT ?"
    params.append(limit)
    rx = execute_query(query, tuple(params))
    return {"total": len(rx), "prescriptions": rx}
