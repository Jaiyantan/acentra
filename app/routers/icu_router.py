"""
ICU & Critical Care API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/icu", tags=["ICU & Critical Care"])

@router.get("/beds", summary="Critical Care beds, APACHE II & SOFA illness severity scores")
def get_icu_beds(icu_name: Optional[str] = None):
    """
    Returns active beds in MICU, SICU, CCU, and Neuro-ICU with current severity scoring
    (APACHE II and SOFA scores).
    """
    query = "SELECT * FROM icu_beds WHERE 1=1"
    params = []
    if icu_name:
        query += " AND icu_name LIKE ?"
        params.append(f"%{icu_name}%")
    beds = execute_query(query, tuple(params))
    return {"total_beds": len(beds), "icu_beds": beds}

@router.get("/telemetry/live", summary="Bedside multi-parameter patient monitor telemetry")
def get_icu_telemetry(bed_id: Optional[str] = None):
    """
    Returns live bedside monitor telemetry:
    - Heart Rate (HR)
    - Arterial Blood Pressure (Systolic / Diastolic / MAP)
    - Pulse Oximetry (SpO2)
    - Respiratory Rate (RR)
    - End-Tidal CO2 (EtCO2)
    - Central Venous Pressure (CVP)
    - Core Temperature & Cardiac Rhythm
    """
    query = "SELECT * FROM icu_telemetry WHERE 1=1"
    params = []
    if bed_id:
        query += " AND bed_id = ?"
        params.append(bed_id)
    query += " ORDER BY timestamp DESC LIMIT 30"
    telemetry = execute_query(query, tuple(params))
    return {"telemetry": telemetry}

@router.get("/ventilators", summary="Mechanical ventilator real-time parameters")
def get_icu_ventilators(bed_id: Optional[str] = None):
    """
    Returns live mechanical ventilator feeds:
    - Ventilation Mode (PRVC, SIMV+PS, PSV)
    - FiO2 percentage
    - Positive End-Expiratory Pressure (PEEP cmH2O)
    - Tidal Volume (mL) & Minute Volume (L/min)
    - Peak Airway Pressure (cmH2O)
    """
    query = "SELECT * FROM icu_ventilator_telemetry WHERE 1=1"
    params = []
    if bed_id:
        query += " AND bed_id = ?"
        params.append(bed_id)
    query += " ORDER BY timestamp DESC LIMIT 20"
    vents = execute_query(query, tuple(params))
    return {"ventilators": vents}

@router.get("/titration", summary="Vasoactive & sedative infusion pump titration logs")
def get_icu_titration_logs(bed_id: Optional[str] = None, limit: int = 50):
    """
    Returns smart syringe/infusion pump logs (Noradrenaline, Vasopressin, Propofol, Insulin).
    """
    query = "SELECT * FROM icu_infusion_titrations WHERE 1=1"
    params = []
    if bed_id:
        query += " AND bed_id = ?"
        params.append(bed_id)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    rows = execute_query(query, tuple(params))
    return {"titrations": rows}

@router.get("/abg", summary="Arterial Blood Gas (ABG) trending and acid-base interpretation")
def get_icu_abg_reports(bed_id: Optional[str] = None, limit: int = 20):
    """
    Returns serial ABG reports: pH, pCO2, pO2, HCO3, Base Excess, Lactate with clinical acid-base interpretation.
    """
    query = "SELECT * FROM icu_abg_reports WHERE 1=1"
    params = []
    if bed_id:
        query += " AND bed_id = ?"
        params.append(bed_id)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    rows = execute_query(query, tuple(params))
    return {"abg_reports": rows}
